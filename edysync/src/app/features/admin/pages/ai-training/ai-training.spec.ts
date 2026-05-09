import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AiTraining } from './ai-training';

describe('AiTraining', () => {
  let component: AiTraining;
  let fixture: ComponentFixture<AiTraining>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [AiTraining]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AiTraining);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
