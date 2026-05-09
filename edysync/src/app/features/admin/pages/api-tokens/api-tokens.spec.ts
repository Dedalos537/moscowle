import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ApiTokens } from './api-tokens';

describe('ApiTokens', () => {
  let component: ApiTokens;
  let fixture: ComponentFixture<ApiTokens>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ApiTokens]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ApiTokens);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
