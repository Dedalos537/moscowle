import { ComponentFixture, TestBed } from '@angular/core/testing';

import { YapeImport } from './yape-import';

describe('YapeImport', () => {
  let component: YapeImport;
  let fixture: ComponentFixture<YapeImport>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [YapeImport]
    })
    .compileComponents();

    fixture = TestBed.createComponent(YapeImport);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
