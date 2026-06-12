import { Injectable, computed, inject } from '@angular/core';
import { ContextDetectorService } from './context-detector.service';
import { HELP_CONTENT } from '../config/help-content.config';
import { HelpContent } from '../models/help-content.model';

@Injectable({ providedIn: 'root' })
export class HelpContentService {
  private contextDetector = inject(ContextDetectorService);

  currentHelp = computed<HelpContent | null>(() => {
    const ctx = this.contextDetector.context();
    if (!ctx.role || !ctx.route) return null;

    const roleHelp = HELP_CONTENT.find(r => r.role === ctx.role);
    if (!roleHelp) return null;

    const pageHelp = roleHelp.pages.find(p => ctx.route.startsWith(p.route));
    if (!pageHelp) return null;

    if (ctx.tab && pageHelp.tabs) {
      const tabHelp = pageHelp.tabs.find(t => t.tab === ctx.tab);
      if (tabHelp) return tabHelp.content;
    }

    return pageHelp.content;
  });
}
