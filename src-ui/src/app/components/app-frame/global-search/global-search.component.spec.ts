import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  tick,
} from '@angular/core/testing'
import { GlobalSearchComponent } from './global-search.component'
import { Subject, of } from 'rxjs'
import { SearchService } from 'src/app/services/rest/search.service'
import { Router } from '@angular/router'
import {
  NgbDropdownModule,
  NgbModal,
  NgbModalModule,
} from '@ng-bootstrap/ng-bootstrap'
import { CorrespondentEditDialogComponent } from '../../common/edit-dialog/correspondent-edit-dialog/correspondent-edit-dialog.component'
import { UserEditDialogComponent } from '../../common/edit-dialog/user-edit-dialog/user-edit-dialog.component'
import { DocumentListViewService } from 'src/app/services/document-list-view.service'
import { HttpClient } from '@angular/common/http'
import { HttpClientTestingModule } from '@angular/common/http/testing'
import { FormsModule, ReactiveFormsModule } from '@angular/forms'
import { FILTER_HAS_CORRESPONDENT_ANY } from 'src/app/data/filter-rule-type'

describe('GlobalSearchComponent', () => {
  let component: GlobalSearchComponent
  let fixture: ComponentFixture<GlobalSearchComponent>
  let searchService: SearchService
  let router: Router
  let modalService: NgbModal
  let documentListViewService: DocumentListViewService

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [GlobalSearchComponent],
      imports: [
        HttpClientTestingModule,
        NgbModalModule,
        NgbDropdownModule,
        FormsModule,
        ReactiveFormsModule,
      ],
    }).compileComponents()

    searchService = TestBed.inject(SearchService)
    router = TestBed.inject(Router)
    modalService = TestBed.inject(NgbModal)
    documentListViewService = TestBed.inject(DocumentListViewService)

    fixture = TestBed.createComponent(GlobalSearchComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('should initialize properties', () => {
    expect(component.query).toBeUndefined()
    expect(component.queryDebounce).toBeInstanceOf(Subject)
    expect(component.searchResults).toBeUndefined()
    expect(component['currentItemIndex']).toBeUndefined()
  })

  // it('should handle keyboard events', () => {
  //   const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
  //   const focusSpy = jest.spyOn(component.searchInput.nativeElement, 'focus');
  //   component.handleKeyboardEvent(event);
  //   expect(focusSpy).toHaveBeenCalled();

  //   component.searchResults = {} as any;
  //   jest.spyOn(component.resultsDropdown, 'isOpen').mockReturnValue(true);

  //   component['currentItemIndex'] = 0;
  //   jest.spyOn(component.resultItems.get(0).nativeElement, 'click');
  //   component.handleKeyboardEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
  //   expect(component['currentItemIndex']).toBe(1);
  //   expect(component.resultItems.get(1).nativeElement.focus).toHaveBeenCalled();

  //   component['currentItemIndex'] = 1;
  //   component.handleKeyboardEvent(new KeyboardEvent('keydown', { key: 'ArrowUp' }));
  //   expect(component['currentItemIndex']).toBe(0);
  //   expect(component.resultItems.get(0).nativeElement.focus).toHaveBeenCalled();

  //   component.handleKeyboardEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
  //   expect(component.resultItems.get(0).nativeElement.click).toHaveBeenCalled();
  // });

  it('should search', fakeAsync(() => {
    const query = 'test'
    const searchSpy = jest.spyOn(searchService, 'globalSearch')
    searchSpy.mockReturnValue(of({} as any))
    const dropdownOpenSpy = jest.spyOn(component.resultsDropdown, 'open')
    component.queryDebounce.next(query)
    tick(401)
    expect(searchSpy).toHaveBeenCalledWith(query)
    expect(dropdownOpenSpy).toHaveBeenCalled()
  }))

  it('should perform primary action', () => {
    const object = { id: 1 }
    const routerSpy = jest.spyOn(router, 'navigate')
    const qfSpy = jest.spyOn(documentListViewService, 'quickFilter')
    const modalSpy = jest.spyOn(modalService, 'open')

    component.primaryAction('document', object)
    expect(routerSpy).toHaveBeenCalledWith(['/documents', object.id])

    component.primaryAction('correspondent', object)
    expect(qfSpy).toHaveBeenCalledWith([
      { rule_type: FILTER_HAS_CORRESPONDENT_ANY, value: object.id.toString() },
    ])

    component.primaryAction('user', object)
    expect(modalSpy).toHaveBeenCalledWith(UserEditDialogComponent, {
      size: 'lg',
    })
  })

  // it('should perform secondary action', () => {
  //   const object = { id: 1 };
  //   jest.spyOn(component.router, 'navigate');
  //   jest.spyOn(component.modalService, 'open').and.returnValue({
  //     componentInstance: {
  //       dialogMode: '',
  //       object: {}
  //     }
  //   });

  //   component.secondaryAction('document', object);
  //   expect(component.router.navigate).toHaveBeenCalledWith([component.documentService.getDownloadUrl(object.id)], { skipLocationChange: true });

  //   component.secondaryAction('correspondent', object);
  //   expect(component.modalService.open).toHaveBeenCalledWith(CorrespondentEditDialogComponent, { size: 'lg' });
  //   expect(component.modalService.open().componentInstance.dialogMode).toBe('EDIT');
  //   expect(component.modalService.open().componentInstance.object).toBe(object);
  // });

  // it('should reset', () => {
  //   jest.spyOn(component.queryDebounce, 'next');
  //   jest.spyOn(component.resultsDropdown, 'close');
  //   component.reset();
  //   expect(component.queryDebounce.next).toHaveBeenCalledWith('');
  //   expect(component.searchResults).toBeNull();
  //   expect(component['currentItemIndex']).toBeUndefined();
  //   expect(component.resultsDropdown.close).toHaveBeenCalled();
  // });

  // it('should set current item', () => {
  //   jest.spyOn(component.resultItems.get(0).nativeElement, 'focus');
  //   component.currentItemIndex = 0;
  //   component.setCurrentItem();
  //   expect(component.resultItems.get(0).nativeElement.focus).toHaveBeenCalled();
  // });

  // it('should handle search input keydown', () => {
  //   jest.spyOn(component.resultItems.first.nativeElement, 'click');
  //   component.searchResults = { total: 1 };
  //   component.resultsDropdown = { isOpen: () => true };
  //   component.searchInputKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
  //   expect(component.currentItemIndex).toBe(0);
  //   expect(component.resultItems.first.nativeElement.focus).toHaveBeenCalled();

  //   component.searchInputKeyDown(new KeyboardEvent('keydown', { key: 'Enter' }));
  //   expect(component.resultItems.first.nativeElement.click).toHaveBeenCalled();
  // });

  // it('should handle dropdown open change', () => {
  //   jest.spyOn(component, 'reset');
  //   component.onDropdownOpenChange(false);
  //   expect(component.reset).toHaveBeenCalled();
  // });
})
