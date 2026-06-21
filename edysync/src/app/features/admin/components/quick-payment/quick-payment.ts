import { Component, output, ChangeDetectionStrategy, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { AdminService } from '../../../../core/services/admin.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Subscription, Subject, debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { SelectOption } from '../../../../shared/components/select/select';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Select } from '../../../../shared/components/select/select';

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
  guardian_name: string;
  guardian_dni: string;
  receipt: File | null;
}

@Component({
  selector: 'app-quick-payment',
  standalone: true,
  templateUrl: './quick-payment.html',
  styleUrl: './quick-payment.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Button, Spinner, Select],
})
export class QuickPayment implements OnDestroy {
  paymentCompleted = output<void>();

  searchQuery = '';
  searchResults: PatientHit[] = [];
  selectedIndex = -1;
  showDropdown = false;
  searching = false;
  showPaymentForm = false;
  selectedPatient: PatientHit | null = null;
  analyzingReceipt = false;
  lastPaymentReceiptUrl = '';
  analyzeResult: any = null;
  registerStatus = '';

  paymentMethodOptions: SelectOption[] = [
    {value: 'transfer', label: 'Transferencia'},
    {value: 'yape', label: 'Yape'},
    {value: 'plin', label: 'Plin'},
    {value: 'cash', label: 'Efectivo'},
    {value: 'card', label: 'Tarjeta'},
  ];

  registerForm: RegisterForm = {
    patient_id: null,
    amount: 0,
    method: 'transfer',
    reference: '',
    next_due_date: '',
    payment_date: new Date().toISOString().substring(0, 10),
    discount: 0,
    guardian_name: '',
    guardian_dni: '',
    receipt: null,
  };

  private searchSubject = new Subject<string>();
  private subscriptions = new Subscription();

  constructor(
    private adminService: AdminService,
    private toastService: ToastService,
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
      guardian_name: '',
      guardian_dni: '',
      receipt: null,
    };
    this.lastPaymentReceiptUrl = '';
    this.analyzeResult = null;
    this.analyzingReceipt = false;
    this.registerStatus = '';
    this.showPaymentForm = true;
    if (this.selectedPatient?.id) this.onPatientSelected(this.selectedPatient.id);
    this.cdr.markForCheck();
  }

  closePaymentForm() {
    this.showPaymentForm = false;
  }

  onPatientSelected(patientId: number) {
    this.subscriptions.add(
      this.adminService.getPaymentInfo(patientId).subscribe({
        next: (res: any) => {
          if (res.guardian_name) this.registerForm.guardian_name = res.guardian_name;
          if (res.guardian_dni) this.registerForm.guardian_dni = res.guardian_dni;
          if (res.current_amount && !this.registerForm.amount) this.registerForm.amount = parseFloat(res.current_amount);
          if (res.suggested_date && !this.registerForm.next_due_date) this.registerForm.next_due_date = res.suggested_date;
          this.cdr.markForCheck();
        },
      }),
    );
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
    if (this.registerForm.guardian_name) formData.append('guardian_name', this.registerForm.guardian_name);
    if (this.registerForm.guardian_dni) formData.append('guardian_dni', this.registerForm.guardian_dni);
    if (this.registerForm.receipt) formData.append('receipt', this.registerForm.receipt);

    this.subscriptions.add(
      this.adminService.registerPayment(formData).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.registerStatus = 'Pago registrado exitosamente';
            this.lastPaymentReceiptUrl = res.receipt_url || '';
            if (this.lastPaymentReceiptUrl) {
              const a = document.createElement('a');
              a.href = this.lastPaymentReceiptUrl;
              a.target = '_blank';
              a.rel = 'noopener';
              a.click();
            }
            this.toastService.show('Pago registrado correctamente', 'success');
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
    return !this.registerForm.patient_id || !this.registerForm.guardian_name || !this.registerForm.guardian_dni;
  }
}
