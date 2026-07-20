import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { routeAnimations } from '../../animations';
import { ConfirmService } from '../../services/confirm.service';
import { WakeLockService } from '../../services/wake-lock.service';
import { Sidebar } from '../../components/sidebar/sidebar';
import { Header } from '../../components/header/header';
import { Spinner } from '../../../shared/components/spinner/spinner';
import { ConfirmDialog } from '../../../shared/components/confirm-dialog/confirm-dialog';
import { AiChat } from '../../../shared/components/ai-chat/ai-chat';
import { HelpButton } from '../../../shared/contextual-help/components/help-button/help-button';
import { HelpPanel } from '../../../shared/contextual-help/components/help-panel/help-panel';
import { BeaconOverlay } from 'ng-beacon';
import { ChartsToggle } from '../../../shared/components/charts-toggle/charts-toggle';

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [RouterModule, CommonModule, Sidebar, Header, Spinner, ConfirmDialog, AiChat, HelpButton, HelpPanel, BeaconOverlay, ChartsToggle],
  templateUrl: './admin-layout.html',
  styleUrl: './admin-layout.scss',
  animations: [routeAnimations],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminLayout implements OnInit, OnDestroy {
  routeLoading = false;
  loadStartTime = 0;
  loadElapsed = '';
  loading = false;
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private router: Router,
    public confirmService: ConfirmService,
    private wakeLockService: WakeLockService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.wakeLockService.request();
    this.subs.add(this.router.events.subscribe(e => {
      if (e instanceof NavigationStart) {
        this.routeLoading = true;
        this.loadStartTime = Date.now();
        this.loadElapsed = '';
        this.cdr.markForCheck();
      }
      if (e instanceof NavigationEnd || e instanceof NavigationCancel || e instanceof NavigationError) {
        const elapsed = Date.now() - this.loadStartTime;
        this.loadElapsed = `${(elapsed / 1000).toFixed(1)}s`;
        setTimeout(() => { this.routeLoading = false; this.cdr.markForCheck(); }, 350);
      }
    }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.wakeLockService.release();
  }

  prepareRoute() {
    return;
  }

}
