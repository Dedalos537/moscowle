import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import DOMPurify from 'dompurify';
import { AssistantBlock, KpiItem, TableColumn, ValueFormat } from '../../../../../../core/services/assistant';
import { PersonLabelPipe } from '../../../../../../shared/pipes/person-label.pipe';
import { BlockChart } from '../block-chart/block-chart';
import { formatValue } from './format';

type TableBlock = Extract<AssistantBlock, { type: 'table' }>;

/** Dibuja los bloques de una respuesta: texto, indicadores, gráficas, tablas y personas. */
@Component({
  selector: 'app-message-blocks',
  standalone: true,
  imports: [RouterLink, FontAwesomeModule, PersonLabelPipe, BlockChart],
  templateUrl: './message-blocks.html',
  styleUrl: './message-blocks.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MessageBlocks {
  readonly blocks = input.required<AssistantBlock[]>();
  /** Orden elegido por tabla (índice del bloque → columna y sentido). */
  readonly sort = signal<Record<number, { key: string; dir: 1 | -1 }>>({});

  md(text: string): string {
    const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const lines = esc(text).split('\n');
    let html = '';
    let inList = false;
    for (const raw of lines) {
      const line = raw.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      if (/^\s*[-·]\s+/.test(line)) {
        if (!inList) { html += '<ul>'; inList = true; }
        html += `<li>${line.replace(/^\s*[-·]\s+/, '')}</li>`;
      } else {
        if (inList) { html += '</ul>'; inList = false; }
        if (line.trim()) html += `<p>${line}</p>`;
      }
    }
    if (inList) html += '</ul>';
    return DOMPurify.sanitize(html);
  }

  value(v: unknown, format?: ValueFormat): string {
    return formatValue(v, format);
  }

  /** Verde si el cambio va en la dirección buena del indicador (p. ej. bajar la deuda es bueno). */
  deltaTone(k: KpiItem): 'up' | 'down' | 'flat' {
    if (k.delta === null || Math.abs(k.delta) < 0.005) return 'flat';
    const better = k.good_when === 'up' ? k.delta > 0 : k.delta < 0;
    return better ? 'up' : 'down';
  }

  deltaLabel(k: KpiItem): string {
    if (k.delta === null) return 'sin periodo anterior';
    const pct = Math.round(Math.abs(k.delta) * 100);
    return `${k.delta >= 0 ? '▲' : '▼'} ${pct} % vs. anterior`;
  }

  rows(i: number, b: TableBlock): Record<string, unknown>[] {
    const s = this.sort()[i];
    if (!s) return b.rows;
    return [...b.rows].sort((a, c) => {
      const x = a[s.key], y = c[s.key];
      if (x === y) return 0;
      if (x === null || x === undefined) return 1;
      if (y === null || y === undefined) return -1;
      return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'es')) * s.dir;
    });
  }

  sortBy(i: number, key: string): void {
    const cur = this.sort()[i];
    const dir: 1 | -1 = cur?.key === key && cur.dir === -1 ? 1 : -1;
    this.sort.update((m) => ({ ...m, [i]: { key, dir } }));
  }

  sortState(i: number, key: string): 'ascending' | 'descending' | 'none' {
    const s = this.sort()[i];
    return s?.key === key ? (s.dir === 1 ? 'ascending' : 'descending') : 'none';
  }

  total(b: TableBlock, col: TableColumn): string {
    if (!col.format || col.format === 'date' || col.format === 'pct') return '';
    const nums = b.rows.map((r) => r[col.key]).filter((v): v is number => typeof v === 'number');
    return nums.length ? formatValue(nums.reduce((a, n) => a + n, 0), col.format) : '';
  }

  /** Exporta la tabla a CSV (abre en Excel; con BOM para las tildes). */
  exportCsv(b: TableBlock): void {
    const cell = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const head = b.columns.map((c) => cell(c.label)).join(';');
    const body = b.rows.map((r) => b.columns.map((c) => cell(r[c.key])).join(';')).join('\n');
    const blob = new Blob(['﻿' + head + '\n' + body], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${b.title || 'tabla'}.csv`.replace(/[\\/:*?"<>|]+/g, '-');
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  link(row: Record<string, unknown>, col: TableColumn): string | null {
    return col.link ? (row[col.link] as string) || null : null;
  }

  code(row: Record<string, unknown>, col: TableColumn): string | null {
    return col.person_code ? (row[col.person_code] as string) || null : null;
  }
}
