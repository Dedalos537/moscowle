import { Component, Directive, input, contentChildren, TemplateRef, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { RevealOnScroll } from '../../directives/reveal-on-scroll';

export interface TableColumn {
  key: string;
  label: string;
  align?: 'left' | 'center' | 'right';
  class?: string;
  width?: string;
}

@Directive({
  selector: 'ng-template[tableCell]',
  standalone: true,
})
export class TableCell {
  @Input('tableCell') columnKey!: string;

  constructor(public templateRef: TemplateRef<{ $implicit: any }>) {}
}

@Component({
  selector: 'app-table',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule, RevealOnScroll],
  templateUrl: './table.html',
  styleUrl: './table.scss',
})
export class Table<T> {
  columns = input<TableColumn[]>([]);
  data = input<T[]>([]);
  emptyMessage = input('No se encontraron registros');
  emptyIcon = input<IconProp>(['fas', 'inbox']);
  trackBy = input<((index: number, item: T) => any) | undefined>();
  rowClass = input<((item: T, index: number) => string) | undefined>();

  cellDefs = contentChildren(TableCell);

  private get cellMap(): Map<string, TemplateRef<any>> {
    const map = new Map<string, TemplateRef<any>>();
    (this.cellDefs() || []).forEach(def => map.set(def.columnKey, def.templateRef));
    return map;
  }

  getTemplate(key: string): TemplateRef<any> | undefined {
    return this.cellMap.get(key);
  }

  computeRowClass(item: T, index: number): string {
    return this.rowClass()?.(item, index) ?? '';
  }

  defaultTrackBy(index: number, item: any): any {
    return item?.id ?? index;
  }

  getValue(row: any, key: string): any {
    return row?.[key];
  }
}
