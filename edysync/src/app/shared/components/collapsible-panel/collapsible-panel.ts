import { Component, input, output, ChangeDetectionStrategy } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { collapse } from '../../../core/animations';

@Component({
  selector: 'app-collapsible-panel',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './collapsible-panel.html',
  styleUrl: './collapsible-panel.scss',
  animations: [collapse],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollapsiblePanel {
  title = input<string>('');
  icon = input<IconProp>();
  expanded = input(false);
  variant = input<'default' | 'card' | 'drawer'>('default');

  expandedChange = output<boolean>();

  toggle() {
    this.expandedChange.emit(!this.expanded());
  }

  close() {
    if (this.expanded()) {
      this.expandedChange.emit(false);
    }
  }
}
