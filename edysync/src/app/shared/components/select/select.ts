import { Component, input, output, forwardRef, ChangeDetectionStrategy, ChangeDetectorRef, HostListener, ElementRef, ViewChild } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

export interface SelectOption {
  value: any;
  label: string;
  description?: string;
  icon?: IconProp;
  disabled?: boolean;
}

@Component({
  selector: 'app-select',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule],
  templateUrl: './select.html',
  styleUrl: './select.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [{
    provide: NG_VALUE_ACCESSOR,
    useExisting: forwardRef(() => Select),
    multi: true
  }]
})
export class Select implements ControlValueAccessor {
  options = input<SelectOption[]>([]);
  placeholder = input<string>('Seleccionar...');
  label = input<string>('');
  disabled = input(false);
  multiple = input(false);
  searchable = input(false);
  clearable = input(false);

  valueChange = output<any>();

  @ViewChild('dropdownPanel') dropdownPanel?: ElementRef;
  @ViewChild('searchInput') searchInput?: ElementRef;

  isOpen = false;
  selectedValue: any = null;
  selectedValues: any[] = [];
  searchQuery = '';
  highlightedIndex = -1;

  private onChange: any = () => {};
  private onTouched: any = () => {};

  constructor(private cdr: ChangeDetectorRef, private elementRef: ElementRef) {}

  get filteredOptions(): SelectOption[] {
    if (!Array.isArray(this.options())) return [];
    if (!this.searchQuery) return this.options();
    const q = this.searchQuery.toLowerCase();
    return this.options().filter(o => o.label.toLowerCase().includes(q) || (o.description && o.description.toLowerCase().includes(q)));
  }

  private findOption(value: any): SelectOption | undefined {
    if (!Array.isArray(this.options())) return undefined;
    return this.options().find(o => o.value === value);
  }

  get selectedLabel(): string {
    if (this.multiple()) {
      if (!Array.isArray(this.selectedValues) || this.selectedValues.length === 0) return '';
      if (this.selectedValues.length === 1) {
        const opt = this.findOption(this.selectedValues[0]);
        return opt?.label || '';
      }
      return `${this.selectedValues.length} seleccionados`;
    }
    if (this.selectedValue == null) return '';
    const opt = this.findOption(this.selectedValue);
    return opt?.label || '';
  }

  get selectedOption(): SelectOption | undefined {
    return this.findOption(this.selectedValue);
  }

  writeValue(value: any): void {
    if (this.multiple()) {
      this.selectedValues = Array.isArray(value) ? value : [];
    } else {
      this.selectedValue = value;
    }
    this.cdr.markForCheck();
  }

  registerOnChange(fn: any): void { this.onChange = fn; }
  registerOnTouched(fn: any): void { this.onTouched = fn; }
  setDisabledState(isDisabled: boolean): void {
    this.cdr.markForCheck();
  }

  toggle() {
    if (this.disabled()) return;
    this.isOpen = !this.isOpen;
    this.highlightedIndex = -1;
    this.searchQuery = '';
    if (this.isOpen && this.searchable()) {
      setTimeout(() => this.searchInput?.nativeElement?.focus());
    }
  }

  open() {
    if (this.disabled() || this.isOpen) return;
    this.isOpen = true;
    this.highlightedIndex = -1;
    this.searchQuery = '';
    if (this.searchable()) {
      setTimeout(() => this.searchInput?.nativeElement?.focus());
    }
  }

  close() {
    this.isOpen = false;
    this.searchQuery = '';
    this.onTouched();
  }

  select(option: SelectOption) {
    if (option.disabled) return;
    if (this.multiple()) {
      const idx = this.selectedValues.indexOf(option.value);
      if (idx === -1) {
        this.selectedValues = [...this.selectedValues, option.value];
      } else {
        this.selectedValues = this.selectedValues.filter(v => v !== option.value);
      }
      this.onChange(this.selectedValues);
      this.valueChange.emit(this.selectedValues);
    } else {
      this.selectedValue = option.value;
      this.onChange(option.value);
      this.valueChange.emit(option.value);
      this.close();
    }
    this.cdr.markForCheck();
  }

  isSelected(value: any): boolean {
    return this.multiple() ? this.selectedValues.includes(value) : this.selectedValue === value;
  }

  clear(event?: Event) {
    event?.stopPropagation();
    if (this.multiple()) {
      this.selectedValues = [];
      this.onChange([]);
      this.valueChange.emit([]);
    } else {
      this.selectedValue = null;
      this.onChange(null);
      this.valueChange.emit(null);
    }
    this.cdr.markForCheck();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event) {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.close();
      this.cdr.markForCheck();
    }
  }

  @HostListener('keydown', ['$event'])
  onKeydown(event: KeyboardEvent) {
    if (!this.isOpen) {
      if (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown') {
        event.preventDefault();
        this.open();
      }
      return;
    }

    const items = this.filteredOptions;
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        this.highlightedIndex = Math.min(this.highlightedIndex + 1, items.length - 1);
        this.scrollToHighlighted();
        break;
      case 'ArrowUp':
        event.preventDefault();
        this.highlightedIndex = Math.max(this.highlightedIndex - 1, 0);
        this.scrollToHighlighted();
        break;
      case 'Enter':
        event.preventDefault();
        if (this.highlightedIndex >= 0 && items[this.highlightedIndex]) {
          this.select(items[this.highlightedIndex]);
        }
        break;
      case 'Escape':
        event.preventDefault();
        this.close();
        break;
      case 'Tab':
        this.close();
        break;
    }
    this.cdr.markForCheck();
  }

  private scrollToHighlighted() {
    setTimeout(() => {
      const el = this.dropdownPanel?.nativeElement?.children[this.highlightedIndex];
      el?.scrollIntoView?.({ block: 'nearest' });
    });
  }
}
