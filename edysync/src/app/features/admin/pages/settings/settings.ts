import { Component, OnInit, OnDestroy, inject, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import type { IconProp } from '@fortawesome/fontawesome-svg-core';
import { forkJoin, Subscription } from 'rxjs';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ThemeService, type ThemeSchedule } from '../../../../core/services/theme.service';
import { GlobalSettingsService, COLOR_PRESETS, type FontSize } from '../../../../core/services/global-settings.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
import type { NotificationPreferences } from '../../../../core/models/notification';
import { AvatarUploader } from '../../../../shared/components/avatar-uploader/avatar-uploader';
import { FingerprintCard } from '../../../../shared/components/fingerprint-card/fingerprint-card';
import { VisorFuncionamiento, type TabId } from '../visor-funcionamiento/visor-funcionamiento';
import { NotificationPrefs } from '../../../../shared/components/notification-prefs/notification-prefs';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [FontAwesomeModule, FormsModule, RouterLink, AvatarUploader, FingerprintCard, VisorFuncionamiento, NotificationPrefs],
  templateUrl: './settings.html',
  styleUrls: ['./settings.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Settings implements OnInit, OnDestroy {
  private theme = inject(ThemeService);
  private settings = inject(GlobalSettingsService);
  private notifService = inject(NotificationService);
  private admin = inject(AdminService);
  private headerService = inject(HeaderService);
  private authService = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private subs = new Subscription();

  /** Secciones de «Mi cuenta» (preferencias personales) y de «Sistema» (lo que antes era el Centro de Operaciones). */
  readonly groups: { label: string; items: { id: string; label: string; icon: IconProp }[] }[] = [
    {
      label: 'Mi cuenta',
      items: [
        { id: 'apariencia', label: 'Apariencia', icon: ['fas', 'palette'] },
        { id: 'notificaciones', label: 'Mis notificaciones', icon: ['fas', 'bell'] },
        { id: 'cuenta', label: 'Foto y huella', icon: ['fas', 'circle-user'] },
      ],
    },
    {
      label: 'Sistema',
      items: [
        { id: 'backend', label: 'Estado del servidor', icon: ['fas', 'server'] },
        { id: 'logs', label: 'Registros', icon: ['fas', 'terminal'] },
        { id: 'incidents', label: 'Incidencias', icon: ['fas', 'triangle-exclamation'] },
        { id: 'csp', label: 'Seguridad web (CSP)', icon: ['fas', 'bug'] },
        { id: 'tokens', label: 'Tokens de API', icon: ['fas', 'key'] },
        { id: 'llm', label: 'IA y modelos', icon: ['fas', 'robot'] },
        { id: 'bot', label: 'Bot de mensajería', icon: ['fas', 'comments'] },
        { id: 'notifications', label: 'Canales de aviso', icon: ['fas', 'paper-plane'] },
      ],
    },
    { label: 'Herramientas', items: [{ id: 'herramientas', label: 'Importar y entrenar', icon: ['fas', 'wrench'] }] },
  ];

  readonly tools: { path: string; label: string; desc: string; icon: IconProp }[] = [
    { path: '/admin/yape-import', label: 'Importar pagos de Yape', desc: 'Carga las capturas o el archivo de movimientos', icon: ['fas', 'mobile-screen-button'] },
    { path: '/admin/ai', label: 'Entrenamiento de IA', desc: 'Entrena y revisa los modelos del asistente', icon: ['fas', 'brain'] },
  ];

  private readonly systemTabs = new Set<string>(['backend', 'logs', 'csp', 'tokens', 'incidents', 'llm', 'bot', 'notifications']);
  section = 'apariencia';

  get isSystemSection(): boolean {
    return this.systemTabs.has(this.section);
  }

  get systemTab(): TabId {
    return this.section as TabId;
  }

  goTo(id: string) {
    this.router.navigate([], { relativeTo: this.route, queryParams: { section: id }, queryParamsHandling: 'merge' });
  }

  hours = Array.from({ length: 24 }, (_, i) => i);
  colorPresets = COLOR_PRESETS;

  saving = false;
  saved = false;

  currentSchedule: ThemeSchedule = { enabled: false, from: 22, to: 7 };
  isDark = false;

  get schedule() { return this.currentSchedule; }
  get fontSize() { return this.settings.fontSize; }
  get primaryColor() { return this.settings.primaryColor; }
  get hideCharts() { return this.settings.hideCharts; }
  get sidebarDisplay() { return this.settings.sidebarDisplay; }
  get notifPrefs() { return this.notifService.preferences() ?? this.notifService.defaultPrefs; }


  ngOnInit() {
    this.headerService.setConfig({
      title: 'Configuración',
      subtitle: 'Tu cuenta, el sistema y las herramientas del administrador',
      icon: ['fas', 'gear'],
    });
    // La sección vive en la URL (?section=): se puede enlazar, recargar y volver con «Atrás».
    this.subs.add(this.route.queryParamMap.subscribe((q) => {
      const requested = q.get('section');
      const known = this.groups.some((g) => g.items.some((i) => i.id === requested));
      this.section = requested && known ? requested : 'apariencia';
      this.cdr.markForCheck();
    }));
    // Re-fetch schedule from API now that user is authenticated
    this.theme.refreshScheduleFromAPI();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.headerService.reset();
  }

  constructor() {
    this.isDark = (this.theme.theme$ as any).value === 'dark';
    this.subs.add(this.theme.theme$.subscribe(t => {
      this.isDark = t === 'dark';
      this.cdr.markForCheck();
    }));
    this.subs.add(this.theme.schedule$.subscribe(s => {
      this.currentSchedule = { ...s };
      this.cdr.markForCheck();
    }));
  }

  toggleDark(): void {
    this.theme.toggle();
    // Disable schedule when manually toggling — otherwise the watcher reverts it
    if (this.currentSchedule.enabled) {
      this.currentSchedule = { ...this.currentSchedule, enabled: false };
      this.theme.setSchedule({ ...this.currentSchedule });
    }
    this.cdr.markForCheck();
  }

  toggleSchedule(): void {
    this.currentSchedule = { ...this.currentSchedule, enabled: !this.currentSchedule.enabled };
    this.theme.setSchedule({ ...this.currentSchedule });
    this.cdr.markForCheck();
  }

  setScheduleFrom(hour: number): void {
    this.currentSchedule = { ...this.currentSchedule, from: hour };
    this.theme.setSchedule({ ...this.currentSchedule });
    this.cdr.markForCheck();
  }

  setScheduleTo(hour: number): void {
    this.currentSchedule = { ...this.currentSchedule, to: hour };
    this.theme.setSchedule({ ...this.currentSchedule });
    this.cdr.markForCheck();
  }

  setFontSize(size: FontSize): void {
    this.settings.setFontSize(size);
    this.cdr.markForCheck();
  }

  setPrimaryColor(name: string): void {
    this.settings.setPrimaryColor(name);
    this.cdr.markForCheck();
  }


  setSidebarDisplay(mode: 'icons' | 'labels'): void {
    this.settings.setSidebarDisplay(mode);
    this.cdr.markForCheck();
  }

}
