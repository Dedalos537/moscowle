import { Component, input, output, ContentChild, ElementRef, ChangeDetectionStrategy } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import type { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-drawer',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './drawer.html',
  styleUrl: './drawer.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Drawer {
  isOpen = input(false);
  title = input<string>('');
  icon = input<IconProp | undefined>(undefined);
  iconColor = input<string>('text-primary');
  size = input<string>('md');

  @ContentChild('drawerHdr', { read: ElementRef })
  private headerElement?: ElementRef;

  close = output<void>();

  get hasCustomHeader(): boolean {
    const el = this.headerElement?.nativeElement;
    return !!el && el.childNodes.length > 0;
  }

  get sizeClass(): string {
    const sizes: Record<string, string> = {
      sm: 'drawer-sm',
      md: 'drawer-md',
      lg: 'drawer-lg',
    };
    return sizes[this.size()] ?? '';
  }

  get customWidth(): string | null {
    const predefined = ['sm', 'md', 'lg'];
    if (predefined.includes(this.size())) return null;
    return this.size() || null;
  }

  closeDrawer() {
    this.close.emit();
  }
}
