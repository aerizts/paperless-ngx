#!/usr/bin/env python3
import logging
import os
from argparse import ArgumentParser
from typing import Final
from typing import List
from urllib.parse import quote

import requests
from common import get_log_level

logger = logging.getLogger("cleanup-tags")


class GithubContainerRegistry:
    def __init__(
        self,
        session: requests.Session,
        token: str,
        owner_or_org: str,
    ):
        self._session: requests.Session = session
        self._token = token
        self._owner_or_org = owner_or_org
        # https://docs.github.com/en/rest/branches/branches
        self._BRANCHES_ENDPOINT = "https://api.github.com/repos/{OWNER}/{REPO}/branches"
        if self._owner_or_org == "paperless-ngx":
            # https://docs.github.com/en/rest/packages#get-all-package-versions-for-a-package-owned-by-an-organization
            self._PACKAGES_VERSIONS_ENDPOINT = "https://api.github.com/orgs/{ORG}/packages/{PACKAGE_TYPE}/{PACKAGE_NAME}/versions"
            # https://docs.github.com/en/rest/packages#delete-package-version-for-an-organization
            self._PACKAGE_VERSION_DELETE_ENDPOINT = "https://api.github.com/orgs/{ORG}/packages/{PACKAGE_TYPE}/{PACKAGE_NAME}/versions/{PACKAGE_VERSION_ID}"
        else:
            # https://docs.github.com/en/rest/packages#get-all-package-versions-for-a-package-owned-by-the-authenticated-user
            self._PACKAGES_VERSIONS_ENDPOINT = "https://api.github.com/user/packages/{PACKAGE_TYPE}/{PACKAGE_NAME}/versions"
            # https://docs.github.com/en/rest/packages#delete-a-package-version-for-the-authenticated-user
            self._PACKAGE_VERSION_DELETE_ENDPOINT = "https://api.github.com/user/packages/{PACKAGE_TYPE}/{PACKAGE_NAME}/versions/{PACKAGE_VERSION_ID}"

    def __enter__(self):
        """
        Sets up the required headers for auth and response
        type from the API
        """
        self._session.headers.update(
            {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {self._token}",
            },
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ensures the authorization token is cleaned up no matter
        the reason for the exit
        """
        if "Accept" in self._session.headers:
            del self._session.headers["Accept"]
        if "Authorization" in self._session.headers:
            del self._session.headers["Authorization"]

    def _read_all_pages(self, endpoint):
        """
        Internal function to read all pages of an endpoint, utilizing the
        next.url until exhausted
        """
        internal_data = []

        while True:
            resp = self._session.get(endpoint)
            if resp.status_code == 200:
                internal_data += resp.json()
                if "next" in resp.links:
                    endpoint = resp.links["next"]["url"]
                else:
                    logger.debug("Exiting pagination loop")
                    break
            else:
                logger.warning(f"Request to {endpoint} return HTTP {resp.status_code}")
                break

        return internal_data

    def get_branches(self, repo: str):
        """
        Returns all current branches of the given repository
        """
        endpoint = self._BRANCHES_ENDPOINT.format(OWNER=self._owner_or_org, REPO=repo)
        internal_data = self._read_all_pages(endpoint)
        return internal_data

    def filter_branches_by_name_pattern(self, branch_data, pattern: str):
        """
        Filters the given list of branches to those which start with the given
        pattern.  Future enhancement could use regex patterns instead.
        """
        matches = {}

        for branch in branch_data:
            if branch["name"].startswith(pattern):
                matches[branch["name"]] = branch

        return matches

    def get_package_versions(
        self,
        package_name: str,
        package_type: str = "container",
    ) -> List:
        """
        Returns all the versions of a given package (container images) from
        the API
        """
        package_name = quote(package_name, safe="")
        endpoint = self._PACKAGES_VERSIONS_ENDPOINT.format(
            ORG=self._owner_or_org,
            PACKAGE_TYPE=package_type,
            PACKAGE_NAME=package_name,
        )

        internal_data = self._read_all_pages(endpoint)

        return internal_data

    def filter_packages_by_tag_pattern(self, package_data, pattern: str):
        """
        Filters the given package version info to those where the tags of the image
        containers at least 1 tag which starts with the given pattern.
        """
        matches = {}

        for package in package_data:
            if "metadata" in package and "container" in package["metadata"]:
                container_metadata = package["metadata"]["container"]
                if "tags" in container_metadata:
                    container_tags = container_metadata["tags"]
                    for tag in container_tags:
                        if tag.startswith(pattern):
                            matches[tag] = package
                            break

        return matches

    def filter_packages_untagged(self, package_data):
        """
        Filters the given package data to those which have no tags at all
        """
        matches = {}

        for package in package_data:
            if "metadata" in package and "container" in package["metadata"]:
                container_metadata = package["metadata"]["container"]
                if "tags" in container_metadata:
                    container_tags = container_metadata["tags"]
                    if not len(container_tags):
                        matches[package["name"]] = package

        return matches

    def delete_package_version(self, package_name, package_data):
        """
        Deletes the given package version from the GHCR
        """
        endpoint = package_data["url"]
        resp = self._session.delete(endpoint)
        if resp.status_code != 204:
            logger.warning(
                f"Request to delete {endpoint} returned HTTP {resp.status_code}",
            )


def _main():
    parser = ArgumentParser(
        description="Using the GitHub API locate and optionally delete container"
        " tags which no longer have an associated feature branch",
    )

    # Requires an affirmative command to actually do a delete
    parser.add_argument(
        "--delete",
        action="store_true",
        default=False,
        help="If provided, actually delete the container tags",
    )

    # When a tagged image is updated, the previous version remains, but it no longer tagged
    # Add this option to remove them as well
    parser.add_argument(
        "--untagged",
        action="store_true",
        default=False,
        help="If provided, delete untagged containers as well",
    )

    # Allows configuration of log level for debugging
    parser.add_argument(
        "--loglevel",
        default="info",
        help="Configures the logging level",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=get_log_level(args),
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname)-8s %(message)s",
    )

    # Must be provided in the environment
    repo_owner: Final[str] = os.environ["GITHUB_REPOSITORY_OWNER"]
    repo: Final[str] = os.environ["GITHUB_REPOSITORY"]
    gh_token: Final[str] = os.environ["TOKEN"]

    with requests.session() as sess:
        with GithubContainerRegistry(sess, gh_token, repo_owner) as gh_api:
            # Step 1 - Locate all branches of the repo
            all_branches = gh_api.get_branches("paperless-ngx")
            logger.info(f"Located {len(all_branches)} branches of {repo_owner}/{repo} ")

            # Step 2 - Filter branches to those starting with "feature-"
            feature_branches = gh_api.filter_branches_by_name_pattern(
                all_branches,
                "feature-",
            )
            logger.info(f"Located {len(feature_branches)} feature branches")

            # Step 3 - Deal with package information
            for package_name in ["paperless-ngx", "paperless-ngx/builder/cache/app"]:

                # Step 3.1 - Location all versions of the given package
                all_package_versions = gh_api.get_package_versions(package_name)
                logger.info(
                    f"Located {len(all_package_versions)} versions of package {package_name}",
                )

                # Step 3.2 - Location package versions which have a tag of "feature-"
                packages_tagged_feature = gh_api.filter_packages_by_tag_pattern(
                    all_package_versions,
                    "feature-",
                )
                logger.info(
                    f'Located {len(packages_tagged_feature)} versions of package {package_name} tagged "feature-"',
                )

                # Step 3.3 - Location package versions with no tags at all
                # TODO: What exactly are these?  Leftovers?
                untagged_packages = gh_api.filter_packages_untagged(
                    all_package_versions,
                )
                logger.info(
                    f"Located {len(untagged_packages)} untagged versions of package {package_name}",
                )

                # Step 3.4 - Determine which package versions have no matching branch
                to_delete = list(
                    set(packages_tagged_feature.keys()) - set(feature_branches.keys()),
                )
                logger.info(
                    f"Located {len(to_delete)} versions of package {package_name} to delete",
                )

                # Step 3.5 - Delete certain package versions
                for tag_to_delete in to_delete:
                    package_version_info = packages_tagged_feature[tag_to_delete]

                    if args.delete:
                        logger.info(
                            f"Deleting {tag_to_delete} (id {package_version_info['id']})",
                        )
                        gh_api.delete_package_version(
                            package_name,
                            package_version_info,
                        )

                    else:
                        logger.info(
                            f"Would delete {tag_to_delete} (id {package_version_info['id']})",
                        )

                # Step 3.6 - Delete untagged package versions
                if args.untagged:
                    logger.info(f"Deleting untagged packages of {package_name}")
                    for to_delete_name in untagged_packages:
                        to_delete_version = untagged_packages[to_delete_name]

                        if args.delete:
                            logger.info(f"Deleting id {to_delete_version['id']}")
                            gh_api.delete_package_version(
                                package_name,
                                to_delete_version,
                            )
                        else:
                            logger.info(
                                f"Would delete {to_delete_name} (id {to_delete_version['id']})",
                            )
                else:
                    logger.info("Leaving untagged images untouched")


if __name__ == "__main__":
    _main()
