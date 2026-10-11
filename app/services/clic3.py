"""Compatibilidad con Clic 3.0: convierte paquetes (.pcc, o .pac con sus actividades) en un proyecto JClic.

Clic 3.0 (Windows, 1992-2000) guarda cada actividad en un archivo de texto con su propio formato (.puz, .ass, .sop,
.crw, .txa) y las secuencias en .pac; un .pcc empaqueta todo en un solo archivo. JClic.js ya no los lee, así que se
traducen al formato .jclic (XML) que sí reproduce el lanzador de la plataforma.

La lectura es un port de edu.xtec.jclic.clic3 (JClic, GPL, Francesc Busquets): mismas reglas, mismos valores por
defecto y la misma correspondencia de tipos que usaba JClic para importar Clic 3.0.
"""

import io
import os
import re
import struct
import zipfile
from dataclasses import dataclass, field
from xml.sax.saxutils import escape, quoteattr

CLICVER = 120
ENDDESC = '‡'
CHBLOCK = '\u008e'
CHINC = '\u008f'

# Bytes 0x80-0x9F como los interpreta JClic (cp1252, pero 0x8E/0x8F/0x90 quedan como marcadores de Clic).
ANSI = '€\u0081‚ƒ„…†‡ˆ‰Š‹Œ\u008d\u008e\u008f\u0090‘’“”•–—˜™š›œ\u009d\u009eŸ'

ACTIVITY_EXT = ('.puz', '.ass', '.sop', '.crw', '.txa')
IMAGE_EXT = ('.gif', '.bmp', '.jpg', '.jpeg', '.png')
MEDIA_EXT = ('.wav', '.mp3', '.ogg', '.mid', '.midi', '.avi', '.mpg', '.mp4')

# Modos
PUZZLE, SOPA, ASSOCIA, CREUATS, TEXTACT = 1, 2, 3, 4, 5
INTERC, FORAT, DOBLE, MEMORY = 0, 1, 2, 3
NORMAL, ESPECIAL, EXPLORA, INFO, IDENTIFICA, ESCRIU = 0, 1, 2, 3, 4, 5
FORATS, COMPTEXT, IDLLETRES, IDPARAULES, BPARAULES, BPARAGRAFS = 0, 1, 2, 3, 4, 5
LAYOUT = {0: 'AB', 1: 'BA', 2: 'AUB', 3: 'BUA'}
MAXC = 20


class Clic3Error(ValueError):
    pass


def decode(data):
    return ''.join(ANSI[b - 0x80] if 0x80 <= b < 0xA0 else chr(b) for b in data)


def lines(data):
    """Como Clic3.dataToArray: corta en CR, LF o CRLF; un salto final no crea una línea vacía."""
    text = decode(data) if isinstance(data, (bytes, bytearray)) else data
    parts = re.split(r'\r\n|\r|\n', text)
    if parts and parts[-1] == '' and text and text[-1] in '\r\n':
        parts.pop()
    return parts


def fname(name):
    """Nombre de archivo normalizado (Clic era de Windows: sin mayúsculas, sin rutas)."""
    name = (name or '').strip().replace('\\', '/')
    return name.split('/')[-1].lower()


def to_int(s, default=0):
    try:
        return int(str(s).strip())
    except (TypeError, ValueError):
        return default


def color(s):
    """Color de Clic (BGR de Windows en hexadecimal) a 0xRRGGBB."""
    s = (s or '').strip()
    if len(s) > 6:
        s = s[-6:]
    try:
        v = int(s, 16)
    except ValueError:
        return '0x000000'
    rgb = ((v & 0xFF) << 16) | (v & 0xFF00) | ((v & 0xFF0000) >> 16)
    return f'0x{rgb:06X}'


@dataclass
class Font:
    family: str = 'Arial'
    size: int = 13
    bold: bool = False
    italic: bool = False


def font(s):
    parts = (s or '').split(',')
    if len(parts) < 14:
        return Font()
    height = abs(to_int(parts[0]))
    weight = to_int(parts[4])
    italic = to_int(parts[5]) != 0
    face = parts[13].strip() or 'Arial'
    size = max(8, (height * 10) // 12)
    f = Font(face, size, weight >= 700, italic)
    if face.lower() == 'system':
        f = Font('Arial', 13, True, italic)
    return f


@dataclass
class Triple:
    back: str = '0xFFFFFF'
    text: str = '0x000000'
    shadow: str = '0x808080'
    has_shadow: bool = False


def triple(s):
    p = (s or '').split(',')
    if len(p) < 4:
        return Triple()
    return Triple(color(p[0]), color(p[1]), color(p[2]), p[3].strip() == '1')


@dataclass
class Activity:
    name: str
    ext: str
    mode: int = 0
    puz_mode: int = 0
    desc: str = ''
    fonts: list = field(default_factory=lambda: [Font() for _ in range(4)])
    colors: list = field(default_factory=lambda: [Triple() for _ in range(4)])
    counters: list = field(default_factory=lambda: [True, True, True])  # tiempo, puntos, acciones
    frame: bool = True
    bg: list = field(default_factory=lambda: ['0xC0C0C0', '0xC0C0C0'])
    bg_image: str = ''
    tile_bg: bool = True
    init_mess: str = ''
    end_mess: str = ''
    delim: list = field(default_factory=lambda: [True, True])
    cw: int = 140
    ch: int = 100
    cw2: int = 140
    ch2: int = 100
    show_help: bool = True
    gra_pos: int = 0
    inv_ass: bool = False
    no_report: bool = False
    content: list = field(default_factory=lambda: ['', '', ''])
    ncw: int = 0
    nch: int = 0
    nctxw: int = 0
    nctxh: int = 0
    bar: list = field(default_factory=lambda: [True, True])
    sol: bool = False
    m_ass: bool = False
    ass: list = field(default_factory=list)
    tags: list = field(default_factory=lambda: [[], []])
    grid_text: list = field(default_factory=list)
    # Actividades de texto
    color_user: list = field(default_factory=lambda: ['0x0000FF', '0xC0C0C0'])
    color_error: list = field(default_factory=lambda: ['0xFFFFFF', '0xFF0000'])
    ok_to_next: bool = False
    check_button: bool = True
    av_cont: bool = True
    av_maj: bool = True
    av_acc: bool = True
    br_par: bool = False
    av_dbl: bool = False
    av_punt: bool = True
    av_lletra: bool = True
    av_no_salta: bool = True
    av_scope: int = 3
    av_max_scope: int = 6
    prev_help: int = 0
    prev_time: int = 30
    tab: int = 16
    check_text: str = ''
    base_text: str = ''
    prev_text: str = ''
    prev_mess: str = ''


def read_activity(name, data):
    """Port de Clic3Activity.load(): devuelve la actividad o lanza Clic3Error."""
    name = fname(name)
    ext = os.path.splitext(name)[1]
    if ext not in ACTIVITY_EXT:
        raise Clic3Error(f'{name}: no es una actividad de Clic 3.0')
    txt = lines(data)
    n = len(txt)
    a = Activity(name=name, ext=ext)
    if n <= 2:
        raise Clic3Error(f'{name}: archivo vacío')
    i = 0
    ver = to_int(txt[i])
    i += 1
    if ver > 1000:
        ver -= 1000
    if not 100 <= ver <= CLICVER:
        raise Clic3Error(f'{name}: versión de Clic no reconocida ({ver})')

    def nxt():
        nonlocal i
        v = txt[i] if i < n else ''
        i += 1
        return v

    if ver > 107:
        desc = []
        while i < n:
            if txt[i][:1] == ENDDESC:
                i += 1
                break
            desc.append(nxt())
        a.desc = '\n'.join(desc).strip()
    if ver > 100:
        for k in range(1 if ver < 118 else 3):
            a.fonts[k] = font(nxt())
            if ver >= 118:
                a.colors[k] = triple(nxt())
        if ver < 118:
            a.fonts[1] = a.fonts[2] = a.fonts[3] = a.fonts[0]
    if ver > 118:
        p = nxt().split(',')
        a.counters = [to_int(p[2]) != 0, to_int(p[0]) != 0, to_int(p[1]) != 0] if len(p) > 2 else a.counters
        if len(p) > 5:
            a.frame = to_int(p[3]) != 0
            a.bg = [color(p[4]), color(p[5])]
    elif ver == 118:
        p = nxt().split(',')
        if len(p) > 5:
            a.counters = [to_int(p[0]) != 0, to_int(p[1]) != 0, to_int(p[2]) != 0]
            a.frame = to_int(p[3]) != 0
            a.bg = [color(p[4]), color(p[5])]
    if ver >= 119:
        bmp = nxt()
        if bmp:
            a.bg_image = fname(bmp)
    a.init_mess = nxt()
    a.end_mess = nxt()
    bools = 0
    if ver > 102:
        bools = to_int(nxt())
        a.delim = [(bools & 1) != 0, (bools & 2) != 0]
    if ver > 105:
        w = nxt().split(';')
        a.cw = to_int(w[0], 140) or 140
        a.cw2 = to_int(w[1], a.cw) if len(w) > 1 else a.cw
        h = nxt().split(';')
        a.ch = to_int(h[0], 100) or 100
        a.ch2 = to_int(h[1], a.ch) if len(h) > 1 else a.ch
    if ver < 118 and ext in ('.sop', '.crw'):
        a.cw = a.ch = 20
    a.show_help = (bools & 0x0004) == 0
    a.gra_pos = (bools & 0x0018) >> 3
    if ver >= 119:
        a.inv_ass = (bools & 0x400) != 0
        a.tile_bg = (bools & 0x800) != 0
        a.no_report = (bools & 0x4000) != 0
    if ver > 108:
        nxt()  # ayuda propia (archivo .hlp de Windows): no aplica en la web
        nxt()
        nxt()
    if ver > 114:
        nxt()  # DLL de Windows: no aplica
        nxt()
        nxt()

    if ext == '.puz':
        a.mode = PUZZLE
        a.content[0] = fname(nxt())
        a.ncw, a.nch = to_int(nxt()), to_int(nxt())
        a.puz_mode = to_int(nxt())
        if (
            a.ncw < 1
            or a.nch < 1
            or a.ncw > MAXC
            or a.nch > MAXC
            or (a.ncw == 1 and a.nch == 1)
            or not 0 <= a.puz_mode <= 3
        ):
            raise Clic3Error(f'{name}: puzzle con medidas no válidas')
        a.bar = [True, True]
        if ver < 120 and a.puz_mode == MEMORY:
            a.gra_pos = 2
    elif ext == '.ass':
        a.mode = ASSOCIA
        if ver > 109:
            a.puz_mode = to_int(nxt())
        a.ncw, a.nch = to_int(nxt()), to_int(nxt())
        if a.ncw < 1 or a.nch < 1 or a.ncw > MAXC or a.nch > MAXC:
            raise Clic3Error(f'{name}: asociación con medidas no válidas')
        a.content[0] = fname(nxt())
        a.content[1] = fname(nxt())
        a.bar = [to_int(nxt()) == 1, to_int(nxt()) == 1]
        if a.puz_mode in (IDENTIFICA, ESCRIU):
            a.bar[1] = False
        elif a.puz_mode in (EXPLORA, INFO):
            a.bar = [False, False]
        if ver > 106:
            a.sol = to_int(nxt()) != 0
            if a.sol:
                a.content[2] = fname(nxt())
        if ver > 101:
            a.m_ass = to_int(nxt()) == 1
            if a.m_ass:
                if a.puz_mode == NORMAL:
                    a.puz_mode = ESPECIAL
                a.nctxw, a.nctxh = to_int(nxt()), to_int(nxt())
                a.ass = [to_int(nxt(), -1) for _ in range(a.ncw * a.nch)]
        if a.puz_mode in (INFO, EXPLORA):
            a.no_report = True
    elif ext == '.sop':
        a.mode = SOPA
        first = nxt()
        if first.startswith('*'):
            a.bar[0] = False
        else:
            a.content[0] = fname(first)
            a.bar[0] = bool(first)
        a.ncw, a.nch = to_int(nxt()), to_int(nxt())
        a.nctxw, a.nctxh = to_int(nxt()), to_int(nxt())
        ntags = to_int(nxt())
        if a.nctxw < 1 or a.nctxh < 1 or ntags < 1:
            raise Clic3Error(f'{name}: sopa de letras sin datos')
        a.grid_text = [nxt().upper() for _ in range(a.nctxh)]
        a.tags[0] = [nxt().upper() for _ in range(ntags)]
    elif ext == '.crw':
        a.mode = CREUATS
        a.nctxw, a.nctxh = to_int(nxt()), to_int(nxt())
        if a.nctxw < 1 or a.nctxh < 1:
            raise Clic3Error(f'{name}: crucigrama sin datos')
        a.grid_text = [nxt().upper() for _ in range(a.nctxh)]
        a.tags[0] = [nxt() for _ in range(a.nctxh)]
        a.tags[1] = [nxt() for _ in range(a.nctxw)]
        a.bar = [False, False]
    elif ext == '.txa':
        a.mode = TEXTACT
        a.fonts[3] = font(nxt())
        a.colors[3] = triple(nxt())
        p = nxt().split(',')
        if len(p) >= 4:
            a.color_user = [color(p[0]), color(p[1])]
            a.color_error = [color(p[2]), color(p[3])]
        p = [to_int(x) for x in nxt().split(',')] + [0] * 7
        a.puz_mode, bp, a.av_scope, a.av_max_scope, a.prev_help, a.prev_time, a.tab = p[:7]
        a.ok_to_next = (bp & 0x0001) != 0
        a.check_button = (bp & 0x0002) != 0
        a.av_cont = (bp & 0x0004) != 0
        a.av_maj = (bp & 0x0008) != 0
        a.av_acc = (bp & 0x0010) != 0
        a.br_par = (bp & 0x0020) != 0
        a.av_dbl = (bp & 0x0040) != 0
        a.av_punt = (bp & 0x0080) != 0
        a.av_lletra = (bp & 0x0100) != 0
        a.av_no_salta = (bp & 0x0200) != 0
        a.check_text = nxt()
        blocks = []
        for _ in range(3):
            buf = []
            while i < n:
                if txt[i][:1] == ENDDESC:
                    i += 1
                    break
                buf.append(nxt())
            blocks.append('\n'.join(buf))
        a.base_text, a.prev_text, a.prev_mess = blocks
        if not a.check_button and (a.puz_mode != FORATS or not a.av_cont):
            a.no_report = True
    return a


@dataclass
class Pac:
    name: str
    desc: str = ''
    acts: list = field(default_factory=list)
    next_pac: str = ''
    no_buttons: bool = False


def read_pac(name, data):
    """Port de Clic3Pac.load()."""
    txt = lines(data)
    n = len(txt)
    p = Pac(name=fname(name))
    if not n:
        raise Clic3Error(f'{name}: paquete vacío')
    i = 0
    ver = to_int(txt[i])
    i += 1
    if ver > 1000:
        ver -= 1000
    if 107 < ver <= CLICVER:
        desc = []
        while i < n:
            if txt[i][:1] == ENDDESC:
                i += 1
                break
            desc.append(txt[i])
            i += 1
        p.desc = '\n'.join(desc).strip()
        if ver >= 113 and i + 10 < n:
            p.no_buttons = (to_int(txt[i]) & 0x0002) != 0
            flags = to_int(txt[i + 2])
            ch_def = fname(txt[i + 3])
            if flags & 1 and ch_def.endswith('.pac'):
                p.next_pac = ch_def
            i += 11
    p.acts = [fname(x) for x in txt[i:] if x.strip()]
    if not p.acts:
        raise Clic3Error(f'{name}: el paquete no tiene actividades')
    return p


def read_pcc(data):
    """Contenedor .pcc: cabecera PCC00, índice de archivos (nombre, posición, tamaño) y los datos tal cual."""
    buf = io.BytesIO(data)

    def line():
        out = bytearray()
        while True:
            b = buf.read(1)
            if not b:
                raise Clic3Error('El archivo .pcc está incompleto')
            if b == b'\r':
                buf.read(1)
                return out.decode('latin-1')
            out += b

    def sz():
        out = bytearray()
        while True:
            b = buf.read(1)
            if not b or b == b'\x00':
                return out.decode('latin-1')
            out += b

    if line() != 'PCC00':
        raise Clic3Error('No es un paquete .pcc de Clic 3.0')
    line()  # descripción
    count = struct.unpack('<H', buf.read(2))[0]
    buf.read(4)  # desplazamiento base (no se usa: las posiciones son absolutas)
    files = {}
    for _ in range(count):
        name = fname(sz())
        offset, size = struct.unpack('<II', buf.read(8))
        if not name:
            break
        if offset + size > len(data):
            raise Clic3Error(f'El .pcc está dañado: {name} queda fuera del archivo')
        files[name] = data[offset : offset + size]
    return files


# ───────────────────────────── escritura en formato JClic ─────────────────────────────


def q(v):
    return quoteattr(str(v))


def style_xml(f, c, with_shadow=True):
    shadow = ' shadow="true"' if (with_shadow and c.has_shadow) else ''
    out = [f'<style{shadow}>']
    out.append(
        f'<font family={q(f.family)} size="{f.size}"'
        + (' bold="true"' if f.bold else '')
        + (' italic="true"' if f.italic else '')
        + ' />'
    )
    out.append(
        f'<color foreground="{c.text}" background="{c.back}" shadow="{c.shadow}" inactive="{c.shadow}" alternative="{c.shadow}" />'
    )
    out.append('</style>')
    return ''.join(out)


MEDIA_TYPES = (
    (('.wav', '.mp3', '.ogg', '.au'), 'PLAY_AUDIO'),
    (('.mid', '.midi'), 'PLAY_MIDI'),
    (('.avi', '.mpg', '.mp4', '.swf'), 'PLAY_VIDEO'),
    (('.ass', '.puz', '.sop', '.crw', '.txa'), 'RUN_CLIC_ACTIVITY'),
    (('.pac', '.pcc'), 'RUN_CLIC_PACKAGE'),
)


class Writer:
    """Arma el proyecto: actividades, secuencia y la lista de archivos de medios usados."""

    def __init__(self, files):
        self.files = files
        self.media = set()
        self.warnings = []

    def text_lines(self, name):
        data = self.files.get(name)
        if data is None:
            self.warnings.append(f'Falta el archivo {name}')
            return []
        return lines(data)

    def use(self, name):
        if name:
            if name not in self.files:
                self.warnings.append(f'Falta el archivo {name}')
            self.media.add(name)
        return name

    def content(self, raw):
        """Texto de una casilla con {imagen.gif}, {sonido.wav}, {otra.ass}…: (atributos, hijos)."""
        image = None
        media = []
        text = raw or ''
        for m in re.findall(r'\{([^}]*)\}', text):
            token = m.strip()
            low = token.lower()
            if low.endswith(IMAGE_EXT):
                image = self.use(fname(token))
                continue
            for word in low.split():
                for exts, kind in MEDIA_TYPES:
                    if word.endswith(exts):
                        if kind.startswith('RUN_'):
                            media.append(f'<media type="{kind}" level="1" file={q(fname(word))} />')
                        elif kind != 'PLAY_MIDI':
                            media.append(f'<media type="{kind}" level="1" file={q(self.use(fname(word)))} />')
        text = re.sub(r'\{[^}]*\}', '', text).strip()
        attrs = f' image={q(image)}' if image else ''
        body = ''.join(media) + (f'<p>{escape(text)}</p>' if text else '')
        return attrs, body

    def cell(self, raw, extra=''):
        attrs, body = self.content(raw)
        return f'<cell{extra}{attrs}>{body}</cell>' if body else f'<cell{extra}{attrs} />'

    def grid(self, a, num, gid, ids=None, ncw=None, nch=None):
        """Port de createActiveBagContent: casillas desde una imagen troceada o desde un .txt (una por línea)."""
        if num in (0, 2):
            cw, ch, w, h, border = a.ncw, a.nch, a.cw, a.ch, a.delim[0]
        else:
            cw, ch, w, h, border = a.nctxw, a.nctxh, a.cw2, a.ch2, a.delim[1]
        cw, ch = ncw or cw, nch or ch
        src = a.content[num]
        bb = min(num, 1)
        head = f'<cells rows="{ch}" cols="{cw}" cellWidth="{float(w)}" cellHeight="{float(h)}" border="{str(border).lower()}" id="{gid}"'
        shaper = f'<shaper class="@Rectangular" cols="{cw}" rows="{ch}" />'
        style = style_xml(a.fonts[bb], a.colors[bb])
        total = cw * ch
        if src.endswith('.txt'):
            texts = self.text_lines(src)
            cells = []
            for k in range(total):
                extra = f' id="{max(ids[k], 0)}"' if ids and k < len(ids) else ''
                cells.append(self.cell(texts[k] if k < len(texts) else '', extra))
            return f'{head}>{style}{shaper}{"".join(cells)}</cells>'
        if src:
            self.use(src)
            cells = ''.join(f'<cell id="{max(ids[k], 0)}" />' for k in range(min(total, len(ids)))) if ids else ''
            return f'{head} image={q(src)}>{style}{shaper}{cells}</cells>'
        return f'{head}>{style}{shaper}</cells>'

    def common(self, a, cls, extra_attrs=''):
        bb2 = style_xml(a.fonts[2], a.colors[2])
        ini_a, ini_b = self.content(a.init_mess)
        end_a, end_b = self.content(a.end_mess)
        desc = ''.join(f'<p>{escape(x)}</p>' for x in a.desc.split('\n') if x.strip())
        counters = f'<counters time="{str(a.counters[0]).lower()}" actions="{str(a.counters[2]).lower()}" score="{str(a.counters[1]).lower()}" />'
        bg_img = f'<image name={q(self.use(a.bg_image))} tiled="{str(a.tile_bg).lower()}" />' if a.bg_image else ''
        help_ = '<helpWindow showSolution="true" />' if a.show_help else ''
        return (
            f'<activity class="{cls}" name={q(a.name)}{extra_attrs}>'
            + (f'<description>{desc}</description>' if desc else '')
            + f'<messages><cell type="initial"{ini_a}>{bb2}{ini_b}</cell><cell type="final"{end_a}>{bb2}{end_b}</cell></messages>'
            + f'<settings margin="8" report="{str(not a.no_report).lower()}" reportActions="false">{help_}'
            + f'<container bgColor="{a.bg[0]}">{bg_img}{counters}</container>'
            + f'<window bgColor="{a.bg[1]}" border="{str(a.frame).lower()}" /></settings>'
        )

    def activity(self, a):
        """Una actividad de Clic 3.0 en XML de JClic, con la misma clase que elegía el importador de JClic."""
        layout = f'<layout position="{LAYOUT.get(a.gra_pos, "AB")}" />'
        if a.mode == PUZZLE:
            cls = {
                INTERC: '@puzzles.ExchangePuzzle',
                FORAT: '@puzzles.HolePuzzle',
                DOBLE: '@puzzles.DoublePuzzle',
                MEMORY: '@memory.MemoryGame',
            }[a.puz_mode]
            body = self.grid(a, 0, 'primary') + '<scramble times="31" />' + ('' if a.puz_mode == INTERC else layout)
            return self.common(a, cls) + body + '</activity>'

        if a.mode == ASSOCIA:
            if a.puz_mode == INFO:
                return self.common(a, '@panels.InformationScreen') + self.grid(a, 0, 'primary') + '</activity>'
            if a.puz_mode == IDENTIFICA:
                body = self.grid(a, 0, 'primary', ids=a.ass or None)
                if a.sol:
                    body += self.grid(a, 2, 'solved')
                return (
                    self.common(a, '@panels.Identify')
                    + body
                    + f'<scramble times="31" primary="{str(a.bar[0]).lower()}" /></activity>'
                )
            if a.puz_mode == EXPLORA:
                body = self.grid(a, 0, 'primary', ids=a.ass or None) + self.grid(a, 1, 'secondary')
                return self.common(a, '@panels.Explore') + body + layout + '</activity>'
            if a.puz_mode == ESCRIU:
                body = self.grid(a, 0, 'primary') + self.grid(a, 1, 'answers', ncw=a.ncw, nch=a.nch)
                if a.sol:
                    body += self.grid(a, 2, 'solved')
                return (
                    self.common(a, '@text.WrittenAnswer')
                    + body
                    + f'<scramble times="31" primary="{str(a.bar[0]).lower()}" />'
                    + layout
                    + '</activity>'
                )
            complex_ = a.puz_mode == ESPECIAL
            cls = '@associations.ComplexAssociation' if complex_ else '@associations.SimpleAssociation'
            body = self.grid(a, 0, 'primary', ids=a.ass if complex_ else None)
            body += self.grid(a, 1, 'secondary') if complex_ else self.grid(a, 1, 'secondary', ncw=a.ncw, nch=a.nch)
            if a.sol:
                body += self.grid(a, 2, 'solved')
            scramble = f'<scramble times="31" primary="{str(a.bar[0]).lower()}" secondary="{str(a.bar[1]).lower()}" />'
            inverse = ' inverse="true"' if complex_ and a.inv_ass else ''
            return self.common(a, cls, inverse) + body + scramble + layout + '</activity>'

        if a.mode == SOPA:
            # En el XML de JClic «rows» lleva las columnas y «columns» las filas (así lo lee JClic.js).
            grid = (
                f'<textGrid rows="{a.nctxw}" columns="{a.nctxh}" cellWidth="{float(a.cw)}" cellHeight="{float(a.ch)}" border="{str(a.delim[1]).lower()}">'
                + style_xml(a.fonts[0], a.colors[0], False)
                + '<text>'
                + ''.join(f'<row>{escape(r.ljust(a.nctxw, "*")[: a.nctxw])}</row>' for r in a.grid_text)
                + '</text></textGrid>'
            )
            clues = (
                '<clues>' + ''.join(f'<clue id="{k}">{escape(c)}</clue>' for k, c in enumerate(a.tags[0])) + '</clues>'
            )
            extra = ''
            if a.bar[0] and a.content[0]:
                b = Activity(**{**a.__dict__})
                b.cw, b.ch = a.cw2, a.ch2
                extra = self.grid(b, 0, 'secondary')
            return self.common(a, '@textGrid.WordSearch') + grid + clues + extra + layout + '</activity>'

        if a.mode == CREUATS:
            grid = (
                f'<textGrid rows="{a.nctxw}" columns="{a.nctxh}" cellWidth="{float(a.cw)}" cellHeight="{float(a.ch)}" border="true">'
                + style_xml(a.fonts[0], a.colors[0], False)
                + '<text>'
                + ''.join(f'<row>{escape(r.ljust(a.nctxw, "*")[: a.nctxw])}</row>' for r in a.grid_text)
                + '</text></textGrid>'
            )
            out = []
            for k, gid in ((0, 'acrossClues'), (1, 'downClues')):
                cells = []
                for row, tag in enumerate(a.tags[k]):
                    for item, clue in enumerate(x for x in tag.split(';') if x != ''):
                        cells.append(self.cell(clue, f' id="{row}" item="{item}"'))
                out.append(
                    f'<cells rows="{len(a.tags[k])}" cols="1" cellWidth="200.0" cellHeight="75.0" border="false" id="{gid}">'
                    + style_xml(a.fonts[1], a.colors[1])
                    + ''.join(cells)
                    + '</cells>'
                )
            return self.common(a, '@textGrid.CrossWord') + grid + ''.join(out) + layout + '</activity>'

        if a.mode == TEXTACT:
            return self.text_activity(a)
        raise Clic3Error(f'{a.name}: tipo de actividad desconocido')

    def text_activity(self, a):
        """Port de TextActivityDocument.readClic3Data: texto, casillas incrustadas y objetivos."""
        cls, attrs, evaluator = {
            FORATS: (
                '@text.FillInBlanks',
                f' autoJump="{str(not a.av_no_salta).lower()}" forceOkToAdvance="{str(a.ok_to_next).lower()}"',
                'complex',
            ),
            COMPTEXT: ('@text.Complete', '', 'complex'),
            IDLLETRES: ('@text.Identify', ' type="identifyChars"', None),
            IDPARAULES: ('@text.Identify', ' type="identifyWords"', None),
            BPARAULES: ('@text.Order', f' type="orderWords" amongParagraphs="{str(a.br_par).lower()}"', 'basic'),
            BPARAGRAFS: ('@text.Order', f' type="orderParagraphs" amongParagraphs="{str(a.br_par).lower()}"', 'basic'),
        }.get(a.puz_mode, ('@text.FillInBlanks', '', 'complex'))
        multi = a.puz_mode == FORATS
        has_check = (not a.av_cont) if multi else (True if a.puz_mode == COMPTEXT else a.check_button)

        paragraphs = [[]]

        def add_text(s, target=False):
            parts = s.split('\n')
            for k, part in enumerate(parts):
                if k:
                    paragraphs.append([])
                if part:
                    paragraphs[-1].append(('target' if target else 'text', part))

        tokens = re.split(f'([{CHBLOCK}{CHINC}])', a.base_text)
        into_block = into_target = False
        count = 0
        tgt = None
        for t in tokens + ([CHINC] if multi else []):
            if t == '':
                continue
            if t == CHBLOCK:
                into_block = not into_block
            elif t == CHINC:
                if multi:
                    count += 1
                    if count == 1:
                        tgt = {'answers': [], 'options': [], 'show': '', 'popup': None, 'text': '', 'params': None}
                    if count > 6:
                        count = 0
                        into_target = False
                        if tgt is not None:
                            paragraphs[-1].append(('fill', tgt))
                            tgt = None
                    else:
                        into_target = True
                else:
                    into_target = not into_target
            elif into_block:
                p = t.split(',', 4)
                if len(p) == 5:
                    w, h, border, left, raw = to_int(p[0]), to_int(p[1]), to_int(p[2]) != 0, to_int(p[3]) != 0, p[4]
                    align = ' hAlign="left"' if left else ''
                    c_attrs, c_body = self.content(raw)
                    paragraphs[-1].append(
                        (
                            'cell',
                            f'<cell width="{w}" height="{h}" border="{str(border).lower()}"{align}{c_attrs}>{style_xml(a.fonts[1], a.colors[1])}{c_body}</cell>',
                        )
                    )
            elif into_target:
                if not multi:
                    add_text(t, target=True)
                elif count == 1:
                    tgt['params'] = t.split(',')
                elif count == 2:
                    tgt['answers'] = [x for x in t.split('|') if x]
                elif count == 3:
                    tgt['options'] = [x for x in re.split(r'[\r\n]+', t) if x]
                elif count == 4:
                    tgt['show'] = t
                elif count == 5:
                    tgt['popup'] = t
                elif count == 6:
                    tgt['text'] += t
            else:
                add_text(t)

        def target_xml(tg):
            p = (tg['params'] or []) + ['0'] * 9
            fill = p[0][:1] or '_'
            is_list = p[1].strip() == '1'
            ini_len, max_len, mode = to_int(p[2]), to_int(p[3]), to_int(p[4])
            v = to_int(p[5])
            delay, max_time = v & 0xFF, (v & 0xFF00) >> 8
            w, h, flags = to_int(p[6]), to_int(p[7]), to_int(p[8])
            out = ['<target>']
            out += [f'<answer>{escape(x)}</answer>' for x in tg['answers']]
            if is_list:
                out.append(
                    '<optionList>' + ''.join(f'<option>{escape(o)}</option>' for o in tg['options']) + '</optionList>'
                )
            else:
                show = f' show={q(tg["show"])}' if tg['show'] else ''
                out.append(f'<response fill={q(fill)} length="{ini_len}" maxLength="{max_len}"{show} />')
            if tg['popup'] and mode != 0:
                attrs_ = ''
                if mode != 1:
                    attrs_ += f' mode="{["no_info", "always", "onError", "onDemand"][min(mode, 3)]}"'
                if delay > 0:
                    attrs_ += f' delay="{delay}"'
                if max_time > 0:
                    attrs_ += f' maxTime="{max_time}"'
                c_attrs, c_body = self.content(tg['popup'])
                only_play = (flags & 2) == 2 and '<media' in c_body and '<p>' not in c_body
                if only_play:
                    out.append(f'<info{attrs_}>{c_body}</info>')
                else:
                    align = ' hAlign="left"' if flags & 1 else ''
                    out.append(
                        f'<info{attrs_}><cell width="{w}" height="{h}"{align}{c_attrs}>{style_xml(a.fonts[3], a.colors[3])}{c_body}</cell></info>'
                    )
            out.append(f'<text>{escape(tg["text"])}</text></target>')
            return ''.join(out)

        body = []
        for para in paragraphs:
            items = []
            for kind, val in para:
                if kind == 'text':
                    items.append(f'<text>{escape(val)}</text>')
                elif kind == 'target':
                    items.append(f'<target>{escape(val)}</target>')
                elif kind == 'fill':
                    items.append(target_xml(val))
                else:
                    items.append(val)
            body.append(f'<p>{"".join(items)}</p>' if items else '<p />')

        f0, c0 = a.fonts[0], a.colors[0]
        doc = (
            '<document>'
            + f'<style name="default" family={q(f0.family)} size="{f0.size}" bold="{str(f0.bold).lower()}" italic="{str(f0.italic).lower()}"'
            + f' foreground="{c0.text}" background="{c0.back}" tabWidth="{a.tab or 16}" />'
            + f'<style name="target" base="default" foreground="{a.color_user[0]}" background="{a.color_user[1]}" target="true" />'
            + f'<style name="targetError" base="target" foreground="{a.color_error[0]}" background="{a.color_error[1]}" />'
            + '<section>'
            + ''.join(body)
            + '</section></document>'
        )
        check = f'<checkButton>{escape(a.check_text or "Corregir")}</checkButton>' if has_check else ''
        prev = ''
        if a.prev_help > 0:
            _, prev_body = self.content(a.prev_mess)
            prev = (
                f'<prevScreen maxTime="{a.prev_time}">'
                + (''.join(f'<p>{escape(x)}</p>' for x in a.prev_text.split('\n')) if a.prev_help == 2 else '')
                + '</prevScreen>'
            )
        ev = ''
        if evaluator == 'complex':
            ev = (
                f'<evaluator class="@ComplexEvaluator" checkCase="{str(a.av_maj).lower()}" checkAccents="{str(a.av_acc).lower()}"'
                f' checkPunctuation="{str(a.av_punt).lower()}" checkDoubleSpaces="{str(a.av_dbl).lower()}" detail="{str(a.av_lletra).lower()}"'
                f' checkSteps="{a.av_scope}" checkScope="{a.av_max_scope}" />'
            )
        elif evaluator == 'basic':
            ev = (
                f'<evaluator class="@BasicEvaluator" checkCase="{str(a.av_maj).lower()}" checkAccents="{str(a.av_acc).lower()}"'
                f' checkPunctuation="{str(a.av_punt).lower()}" checkDoubleSpaces="{str(a.av_dbl).lower()}" />'
            )
        settings = self.common(a, cls, attrs)
        # Tamaño de la ventana de texto (txtCW/txtCH en Clic): va dentro de <window>.
        settings = settings.replace(
            f'<window bgColor="{a.bg[1]}" border="{str(a.frame).lower()}" />',
            f'<window bgColor="{a.bg[1]}" border="{str(a.frame).lower()}"><size width="{a.cw}" height="{a.ch}" /></window>',
        )
        return settings + check + prev + doc + ev + '</activity>'


@dataclass
class Project:
    xml: str
    media: dict
    activities: int
    warnings: list


def build_project(files, title):
    """files: {nombre: bytes}. Devuelve el proyecto JClic (XML + archivos de medios a copiar)."""
    files = {fname(k): v for k, v in files.items()}
    w = Writer(files)
    pacs = [read_pac(n, d) for n, d in sorted(files.items()) if n.endswith('.pac')]
    order = []
    for p in pacs:
        for act in p.acts:
            if act not in order:
                order.append(act)
    for n in sorted(files):
        if n.endswith(ACTIVITY_EXT) and n not in order:
            order.append(n)
    if not order:
        raise Clic3Error('No encontré actividades de Clic 3.0 (.puz, .ass, .sop, .crw o .txa).')

    acts_xml = []
    converted = set()
    for n in order:
        if n not in files:
            w.warnings.append(f'El paquete nombra {n}, pero no está en el archivo')
            continue
        try:
            acts_xml.append(w.activity(read_activity(n, files[n])))
            converted.add(n)
        except Clic3Error as e:
            w.warnings.append(str(e))
    if not converted:
        raise Clic3Error('Ninguna actividad se pudo convertir.' + (' ' + w.warnings[0] if w.warnings else ''))

    seq = []
    for p in pacs:
        acts = [a for a in p.acts if a in converted]
        for k, act in enumerate(acts):
            tag = f' id={q(p.name)}' if k == 0 else ''
            jumps = ''
            if k == len(acts) - 1:
                jumps = (
                    f'<jump tag={q(p.next_pac)} id="forward" />'
                    if p.next_pac
                    else '<jump action="RETURN" id="forward" />'
                )
            seq.append(f'<item{tag} name={q(act)}>{jumps}</item>' if jumps else f'<item{tag} name={q(act)} />')
    if not pacs:
        seq = [f'<item name={q(n)} />' for n in order if n in converted]

    media = {}
    media_xml = []
    for m in sorted(w.media):
        data = files.get(m)
        if data is None:
            continue
        out_name = m
        if m.endswith('.bmp'):
            data, out_name = bmp_to_png(data, m)
        media[out_name] = data
        media_xml.append(f'<media name={q(m)} file={q(out_name)} />')

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        + f'<JClicProject name={q(title)} version="0.1.3">'
        + f'<settings><title>{escape(title)}</title><language>es</language></settings>'
        + '<sequence>'
        + ''.join(seq)
        + '</sequence>'
        + '<activities>'
        + ''.join(acts_xml)
        + '</activities>'
        + '<mediaBag>'
        + ''.join(media_xml)
        + '</mediaBag>'
        + '</JClicProject>'
    )
    return Project(xml=xml, media=media, activities=len(converted), warnings=sorted(set(w.warnings)))


def bmp_to_png(data, name):
    """Los BMP de Windows 3.x se pasan a PNG: más livianos y seguros en cualquier navegador."""
    try:
        from PIL import Image

        out = io.BytesIO()
        Image.open(io.BytesIO(data)).save(out, format='PNG', optimize=True)
        return out.getvalue(), name[:-4] + '.png'
    except Exception:  # noqa: BLE001 - si no se puede convertir, se sirve el BMP tal cual
        return data, name


MAX_FILES = 3000
MAX_TOTAL = 80 * 1024 * 1024


def files_from_upload(filename, data):
    """Saca los archivos de Clic de un .pcc, de un .zip o de un .pac suelto."""
    low = filename.lower()
    if low.endswith('.pcc'):
        return read_pcc(data)
    if low.endswith('.zip'):
        out = {}
        total = 0
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            if len(infos) > MAX_FILES:
                raise Clic3Error('El .zip tiene demasiados archivos.')
            for info in infos:
                total += info.file_size
                if total > MAX_TOTAL:
                    raise Clic3Error('El .zip es demasiado grande una vez descomprimido.')
                name = fname(info.filename)
                if name.endswith('.pcc'):
                    out.update(read_pcc(zf.read(info)))
                elif name:
                    out[name] = zf.read(info)
        return out
    if low.endswith(ACTIVITY_EXT + ('.pac',)):
        return {fname(filename): data}
    raise Clic3Error('Formato no reconocido para Clic 3.0.')


def looks_like_clic3(filename, data):
    low = filename.lower()
    if low.endswith(('.pcc', '.pac') + ACTIVITY_EXT):
        return True
    if low.endswith('.zip') and not low.endswith('.jclic.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                return any(n.lower().endswith(('.pac', '.pcc') + ACTIVITY_EXT) for n in zf.namelist())
        except zipfile.BadZipFile:
            return False
    return False
