import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CspReports } from './csp-reports';

describe('CspReports', () => {
  let component: CspReports;
  let fixture: ComponentFixture<CspReports>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [CspReports]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CspReports);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
