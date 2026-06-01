import { Component, Output, EventEmitter, ChangeDetectionStrategy, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { AlertService } from '../../../../core/services/alert.service';
import { Subscription, Subject, debounceTime, distinctUntilChanged, switchMap } from 'rxjs';

interface PatientHit {
  id: number;
  username: string;
  email: string;
  phone: string;
}

interface RegisterForm {
  patient_id: number | null;
  amount: number;
  method: string;
  reference: string;
  next_due_date: string;
  payment_date: string;
  discount: number;
  document_number: string;
  guardian_name: string;
  receipt: File | null;
}

@Component({
  selector: 'app-quick-payment',
  standalone: false,
  templateUrl: './quick-payment.html',
  styleUrl: './quick-payment.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QuickPayment implements OnDestroy {
  @Output() paymentCompleted = new EventEmitter<void>();

  searchQuery = '';
  searchResults: PatientHit[] = [];
  selectedIndex = -1;
  showDropdown = false;
  searching = false;
  showPaymentForm = false;
  selectedPatient: PatientHit | null = null;
  analyzingReceipt = false;
  analyzeResult: any = null;
  registerStatus = '';

  registerForm: RegisterForm = {
    patient_id: null,
    amount: 0,
    method: 'transfer',
    reference: '',
    next_due_date: '',
    payment_date: new Date().toISOString().substring(0, 10),
    discount: 0,
    document_number: '',
    guardian_name: '',
    receipt: null,
  };

  private searchSubject = new Subject<string>();
  private subscriptions = new Subscription();

  constructor(
    private adminService: AdminService,
    private alertService: AlertService,
    private cdr: ChangeDetectorRef,
  ) {
    this.subscriptions.add(
      this.searchSubject.pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap(q => {
          if (q.length < 2) {
            this.searchResults = [];
            this.showDropdown = false;
            this.searching = false;
            return [];
          }
          this.searching = true;
          return this.adminService.searchPatients(q);
        }),
      ).subscribe({
        next: (res: any) => {
          this.searchResults = res.patients || [];
          this.showDropdown = this.searchResults.length > 0;
          this.selectedIndex = -1;
          this.searching = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.searchResults = [];
          this.showDropdown = false;
          this.searching = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  onSearchInput(value: string) {
    this.searchQuery = value;
    this.searchSubject.next(value);
    if (value.length < 2) {
      this.showDropdown = false;
      this.searchResults = [];
    }
  }

  selectPatient(patient: PatientHit) {
    this.selectedPatient = patient;
    this.searchQuery = patient.username;
    this.showDropdown = false;
    this.openPaymentForm();
  }

  openPaymentForm() {
    if (!this.selectedPatient) return;
    this.registerForm = {
      patient_id: this.selectedPatient.id,
      amount: 0,
      method: 'transfer',
      reference: '',
      next_due_date: '',
      payment_date: new Date().toISOString().substring(0, 10),
      discount: 0,
      document_number: '',
      guardian_name: '',
      receipt: null,
    };
    this.analyzeResult = null;
    this.analyzingReceipt = false;
    this.registerStatus = '';
    this.showPaymentForm = true;
  }

  closePaymentForm() {
    this.showPaymentForm = false;
  }

  clearSearch() {
    this.searchQuery = '';
    this.searchResults = [];
    this.showDropdown = false;
    this.selectedPatient = null;
    this.selectedIndex = -1;
  }

  onBlur() {
    setTimeout(() => {
      this.showDropdown = false;
    }, 200);
  }

  onFocus() {
    if (this.searchResults.length > 0 && this.searchQuery.length >= 2) {
      this.showDropdown = true;
    }
  }

  onKeydown(event: KeyboardEvent) {
    if (!this.showDropdown || this.searchResults.length === 0) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.selectedIndex = Math.min(this.selectedIndex + 1, this.searchResults.length - 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
    } else if (event.key === 'Enter' && this.selectedIndex >= 0) {
      event.preventDefault();
      this.selectPatient(this.searchResults[this.selectedIndex]);
    } else if (event.key === 'Escape') {
      this.showDropdown = false;
    }
  }

  onFileSelected(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0] || null;
    this.registerForm.receipt = file;
    if (file) {
      this.analyzingReceipt = true;
      this.subscriptions.add(
        this.adminService.analyzeReceipt(file, this.registerForm.patient_id ?? undefined).subscribe({
          next: (res: any) => {
            this.analyzeResult = res;
            this.analyzingReceipt = false;
            if (res.amount) this.registerForm.amount = parseFloat(res.amount);
            if (res.reference) this.registerForm.reference = res.reference;
            if (res.method) this.registerForm.method = res.method;
            if (res.next_due_date) this.registerForm.next_due_date = res.next_due_date;
            this.cdr.markForCheck();
          },
          error: () => {
            this.analyzingReceipt = false;
            this.cdr.markForCheck();
          },
        }),
      );
    }
  }

  submitPayment() {
    this.registerStatus = 'Registrando...';
    const formData = new FormData();
    if (this.registerForm.patient_id) formData.append('patient_id', String(this.registerForm.patient_id));
    formData.append('amount', String(this.registerForm.amount));
    formData.append('method', this.registerForm.method);
    if (this.registerForm.reference) formData.append('reference', this.registerForm.reference);
    if (this.registerForm.next_due_date) formData.append('next_due_date', this.registerForm.next_due_date);
    if (this.registerForm.payment_date) formData.append('payment_date', this.registerForm.payment_date);
    formData.append('discount', String(this.registerForm.discount));
    if (this.registerForm.document_number) formData.append('document_number', this.registerForm.document_number);
    if (this.registerForm.guardian_name) formData.append('guardian_name', this.registerForm.guardian_name);
    if (this.registerForm.receipt) formData.append('receipt', this.registerForm.receipt);

    this.subscriptions.add(
      this.adminService.registerPayment(formData).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.registerStatus = 'Pago registrado exitosamente';
            this.alertService.show('Pago registrado correctamente', 'success');
            setTimeout(() => {
              this.closePaymentForm();
              this.clearSearch();
              this.paymentCompleted.emit();
            }, 1000);
          } else {
            this.registerStatus = 'Error: ' + (res.message || res.error || 'Desconocido');
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.registerStatus = 'Error de conexion al servidor';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  get needsRecalculation(): boolean {
    return this.registerForm.amount > 0 && this.registerForm.discount > 0;
  }

  get hasMissingData(): boolean {
    return !this.registerForm.document_number || !this.registerForm.guardian_name;
  }
}
