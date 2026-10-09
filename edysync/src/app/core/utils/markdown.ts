import DOMPurify from 'dompurify';

/**
 * Markdown sencillo y SEGURO para textos generados por IA: títulos, listas, tablas, negritas, cursivas, código y
 * separadores. Todo el texto se escapa antes de dar formato y el resultado pasa por DOMPurify con etiquetas permitidas.
 */
export interface MdSection {
  title: string;
  html: string;
}

const ALLOWED = ['h2', 'h3', 'h4', 'p', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'br'];

function escape(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function inline(text: string) {
  return escape(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*(?!\s)(.+?)\*(?!\*)/g, '$1<em>$2</em>')
    .replace(/(^|\s)_(?!\s)(.+?)_(?=\s|$|[.,;:])/g, '$1<em>$2</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function cells(row: string) {
  return row.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
}

export function markdownToHtml(md: string): string {
  const lines = (md || '').replace(/\r\n/g, '\n').split('\n');
  const out: string[] = [];
  let list: 'ul' | 'ol' | null = null;
  const closeList = () => {
    if (list) out.push(`</${list}>`);
    list = null;
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) {
      closeList();
      continue;
    }
    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    if (heading) {
      closeList();
      const level = Math.min(4, Math.max(2, heading[1].length + 1)); // # → h2: el título del modal ya es el h1
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      continue;
    }
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(line)) {
      closeList();
      out.push('<hr>');
      continue;
    }
    if (line.startsWith('|') && i + 1 < lines.length && /^\|?\s*:?-{2,}/.test(lines[i + 1].trim())) {
      closeList();
      const head = cells(line);
      i += 1;
      const rows: string[][] = [];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith('|')) rows.push(cells(lines[++i]));
      out.push(
        '<table><thead><tr>' + head.map((h) => `<th>${inline(h)}</th>`).join('') + '</tr></thead><tbody>' +
          rows.map((r) => '<tr>' + r.map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>').join('') +
          '</tbody></table>',
      );
      continue;
    }
    const bullet = /^[-*•]\s+(.*)$/.exec(line);
    const numbered = /^\d+[.)]\s+(.*)$/.exec(line);
    if (bullet || numbered) {
      const kind = bullet ? 'ul' : 'ol';
      if (list !== kind) {
        closeList();
        out.push(`<${kind}>`);
        list = kind;
      }
      out.push(`<li>${inline((bullet || numbered)![1])}</li>`);
      continue;
    }
    closeList();
    out.push(`<p>${inline(line)}</p>`);
  }
  closeList();
  return DOMPurify.sanitize(out.join(''), { ALLOWED_TAGS: ALLOWED, ALLOWED_ATTR: [] });
}

/** Divide el Markdown por títulos de nivel 2 («## Recomendaciones») para mostrar solo las secciones que interesan. */
export function markdownSections(md: string): MdSection[] {
  const parts = (md || '').split(/\n(?=##\s)/);
  return parts
    .map((part) => {
      const m = /^##\s+(.+)$/m.exec(part);
      const title = m ? m[1].trim() : '';
      const body = m ? part.replace(m[0], '') : part.replace(/^#\s+.*$/m, '');
      return { title, html: markdownToHtml(body.replace(/^\s*-{3,}\s*$/gm, '')) };
    })
    .filter((s) => s.html.replace(/<[^>]+>/g, '').trim());
}
