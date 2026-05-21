// DCE — Diego Centeno Estuvo Acá
import { Injectable, TemplateRef } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface HeaderConfig {
  title?: string;
  subtitle?: string;
  icon?: any;
  actionTemplate?: TemplateRef<any> | null;
}

@Injectable({
  providedIn: 'root'
})
export class HeaderService {
  private titleSub = new BehaviorSubject<string>('Panel de Administración');
  private subtitleSub = new BehaviorSubject<string>('Control integral de terapeutas y pacientes');
  private iconSub = new BehaviorSubject<any>(null);
  private actionTemplateSub = new BehaviorSubject<TemplateRef<any> | null>(null);

  title$ = this.titleSub.asObservable();
  subtitle$ = this.subtitleSub.asObservable();
  icon$ = this.iconSub.asObservable();
  actionTemplate$ = this.actionTemplateSub.asObservable();

  setConfig(config: HeaderConfig) {
    if (config.title !== undefined) this.titleSub.next(config.title);
    if (config.subtitle !== undefined) this.subtitleSub.next(config.subtitle);
    if (config.icon !== undefined) this.iconSub.next(config.icon || null);
    if (config.actionTemplate !== undefined) this.actionTemplateSub.next(config.actionTemplate);
  }

  reset() {
    this.titleSub.next('Panel de Administración');
    this.subtitleSub.next('Control integral de terapeutas y pacientes');
    this.iconSub.next(null);
    this.actionTemplateSub.next(null);
  }
}
