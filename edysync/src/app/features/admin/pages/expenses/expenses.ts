import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { Expense, TherapistFinancial } from '../../../../core/models/expense';
import { User } from '../../../../core/models/user';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-expenses',
  standalone: false,
  templateUrl: './expenses.html',
  styleUrl: './expenses.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class Expenses implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  therapistFinancials: TherapistFinancial[] = [];
  recentExpenses: Expense[] = [];
  therapists: User[] = [];
  loading = true;
  submitting = false;
  private subscriptions: Subscription = new Subscription();

  showModal = false;
  modalMode: 'therapist_payment' | 'operational' = 'operational';
  form = {
    category: 'operational' as string,
    therapist_id: null as number | null,
    therapist_name: '',
    amount: 0,
    method: 'transfer' as string,
    date: '',
    description: '',
    receipt: null as File | null,
  };

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Gestión de Gastos y Terapeutas',
      subtitle: 'Pagos a personal, control de horas y gastos operativos',
      icon: ['fas', 'wallet'],
      actionTemplate: this.headerActions,
    });
    this.form.date = new Date().toISOString().split('T')[0];
    this.loadData();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
    this.headerService.reset();
  }

  private loadData() {
    this.loading = true;
    this.subscriptions.add(
      this.adminService.getTherapistFinancials().subscribe({
        next: (res) => { this.therapistFinancials = res.data; this.cdr.markForCheck(); },
        error: () => { this.cdr.markForCheck(); },
      })
    );
    this.subscriptions.add(
      this.adminService.getUsers('terapista').subscribe({
        next: (res) => { this.therapists = res.users.map((u) => ({ ...u, is_active: true } as User)); this.cdr.markForCheck(); },
        error: () => { this.cdr.markForCheck(); },
      })
    );
    this.subscriptions.add(
      this.adminService.getExpenses().subscribe({
        next: (res) => {
          this.recentExpenses = res.data;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: () => { this.loading = false; this.cdr.markForCheck(); },
      })
    );
  }

  openPaymentModal(therapist: TherapistFinancial) {
    this.modalMode = 'therapist_payment';
    this.form = {
      category: 'therapist_payment',
      therapist_id: therapist.therapist.id,
      therapist_name: therapist.therapist.username,
      amount: therapist.balance > 0 ? therapist.balance : 0,
      method: 'transfer',
      date: new Date().toISOString().split('T')[0],
      description: `Pago a ${therapist.therapist.username}`,
      receipt: null,
    };
    this.showModal = true;
  }

  openOperationalModal() {
    this.modalMode = 'operational';
    this.form = {
      category: 'operational',
      therapist_id: null,
      therapist_name: '',
      amount: 0,
      method: 'transfer',
      date: new Date().toISOString().split('T')[0],
      description: '',
      receipt: null,
    };
    this.showModal = true;
  }

  closeModal() {
    this.showModal = false;
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) this.form.receipt = file;
  }

  submitForm() {
    this.submitting = true;
    const fd = new FormData();
    fd.append('category', this.form.category);
    fd.append('amount', String(this.form.amount));
    fd.append('date', this.form.date);
    fd.append('description', this.form.description);
    fd.append('method', this.form.method);
    if (this.form.therapist_id) fd.append('therapist_id', String(this.form.therapist_id));
    if (this.form.receipt) fd.append('receipt', this.form.receipt);

    this.subscriptions.add(
      this.adminService.createExpense(fd).subscribe({
        next: () => {
          this.submitting = false;
          this.closeModal();
          this.loadData();
          this.cdr.markForCheck();
        },
        error: () => { this.submitting = false; this.cdr.markForCheck(); },
      })
    );
  }
}
