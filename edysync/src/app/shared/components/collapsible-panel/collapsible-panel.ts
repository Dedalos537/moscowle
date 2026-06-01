import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { collapse } from '../../../core/animations';

@Component({
  selector: 'app-collapsible-panel',
  standalone: false,
  templateUrl: './collapsible-panel.html',
  styleUrl: './collapsible-panel.scss',
  animations: [collapse],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollapsiblePanel {
  @Input() title: string = '';
  @Input() icon?: IconProp;
  @Input() expanded: boolean = false;
  @Input() variant: 'default' | 'card' | 'drawer' = 'default';

  @Output() expandedChange = new EventEmitter<boolean>();

  toggle() {
    this.expanded = !this.expanded;
    this.expandedChange.emit(this.expanded);
  }

  close() {
    if (this.expanded) {
      this.expanded = false;
      this.expandedChange.emit(false);
    }
  }
}
