"""Cliente IPP mínimo para hablar con un CUPS remoto sin instalar nada en la VM.

El backend corre en VM-APP y la impresora está en el CUPS del host. En vez de depender de `cups-client`,
mandamos las peticiones IPP (RFC 8010/8011 + extensiones de CUPS) por HTTP al puerto 631 del host.
Solo implementa lo que usa el drive: listar impresoras, la predeterminada, imprimir y cancelar.
"""

import struct
import urllib.request
from urllib.parse import quote

# operaciones
PRINT_JOB = 0x0002
CANCEL_JOB = 0x0008
CUPS_GET_DEFAULT = 0x4001
CUPS_GET_PRINTERS = 0x4002

# etiquetas de grupo y de valor
_OPERATION, _JOB, _END, _PRINTER = 0x01, 0x02, 0x03, 0x04
_INTEGER, _BOOLEAN, _ENUM = 0x21, 0x22, 0x23
_RANGE, _TEXT, _NAME, _KEYWORD, _URI, _CHARSET, _LANG, _MIME = 0x33, 0x41, 0x42, 0x44, 0x45, 0x47, 0x48, 0x49

STATES = {3: 'idle', 4: 'printing', 5: 'disabled'}


class IppError(Exception):
    pass


def _attr(tag, name, *values):
    out = b''
    for i, value in enumerate(values):
        if tag in (_INTEGER, _ENUM):
            raw = struct.pack('>i', value)
        elif tag == _BOOLEAN:
            raw = b'\x01' if value else b'\x00'
        elif tag == _RANGE:
            raw = struct.pack('>ii', *value)
        else:
            raw = str(value).encode('utf-8')
        key = name.encode() if i == 0 else b''
        out += bytes([tag]) + struct.pack('>H', len(key)) + key + struct.pack('>H', len(raw)) + raw
    return out


def _request(op, request_id, operation_attrs, job_attrs=b''):
    body = struct.pack('>BBHI', 2, 0, op, request_id)
    body += bytes([_OPERATION]) + _attr(_CHARSET, 'attributes-charset', 'utf-8')
    body += _attr(_LANG, 'attributes-natural-language', 'es') + operation_attrs
    if job_attrs:
        body += bytes([_JOB]) + job_attrs
    return body + bytes([_END])


def parse(data: bytes) -> tuple[int, list[dict]]:
    """(status-code, grupos). Cada grupo es {'tag': int, 'attrs': {nombre: [valores]}}."""
    if len(data) < 9:
        raise IppError('Respuesta IPP incompleta')
    status = struct.unpack('>H', data[2:4])[0]
    groups, pos, name = [], 8, None
    while pos < len(data):
        tag = data[pos]
        pos += 1
        if tag == _END:
            break
        if tag < 0x10:
            groups.append({'tag': tag, 'attrs': {}})
            continue
        nlen = struct.unpack('>H', data[pos : pos + 2])[0]
        pos += 2
        if nlen:
            name = data[pos : pos + nlen].decode('utf-8', 'replace')
        pos += nlen
        vlen = struct.unpack('>H', data[pos : pos + 2])[0]
        pos += 2
        raw = data[pos : pos + vlen]
        pos += vlen
        if tag in (_INTEGER, _ENUM) and vlen == 4:
            value = struct.unpack('>i', raw)[0]
        elif tag == _BOOLEAN:
            value = raw == b'\x01'
        else:
            value = raw.decode('utf-8', 'replace')
        if groups and name:
            groups[-1]['attrs'].setdefault(name, []).append(value)
    return status, groups


class Client:
    def __init__(self, server: str, timeout: float = 5, user: str = 'moscowle'):
        self.server = server if ':' in server else f'{server}:631'
        self.timeout = timeout
        self.user = user
        self._rid = 0

    def _post(self, path, body, timeout=None):
        req = urllib.request.Request(  # noqa: S310 - servidor CUPS configurado por el admin
            f'http://{self.server}{path}', data=body, headers={'Content-Type': 'application/ipp'}, method='POST'
        )
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:  # noqa: S310
            status, groups = parse(resp.read())
        if status > 0x00FF:
            msg = next((g['attrs']['status-message'][0] for g in groups if 'status-message' in g['attrs']), None)
            raise IppError(msg or f'CUPS rechazó la petición (0x{status:04x})')
        return groups

    def _op(self, op, path, attrs, job_attrs=b'', data=b'', timeout=None):
        self._rid += 1
        return self._post(path, _request(op, self._rid, attrs, job_attrs) + data, timeout)

    def printer_uri(self, name):
        return f'ipp://{self.server}/printers/{quote(name)}'

    def printers(self) -> list[dict]:
        attrs = _attr(_NAME, 'requesting-user-name', self.user)
        attrs += _attr(_KEYWORD, 'requested-attributes', 'printer-name', 'printer-state', 'printer-state-message')
        out = []
        for g in self._op(CUPS_GET_PRINTERS, '/', attrs):
            a = g['attrs']
            if g['tag'] == _PRINTER and a.get('printer-name'):
                out.append(
                    {
                        'name': a['printer-name'][0],
                        'state': STATES.get((a.get('printer-state') or [0])[0], 'unknown'),
                        'detail': (a.get('printer-state-message') or [''])[0],
                    }
                )
        return out

    def default(self) -> str | None:
        attrs = _attr(_NAME, 'requesting-user-name', self.user)
        attrs += _attr(_KEYWORD, 'requested-attributes', 'printer-name')
        try:
            groups = self._op(CUPS_GET_DEFAULT, '/', attrs)
        except IppError:
            return None  # sin impresora predeterminada
        return next((g['attrs']['printer-name'][0] for g in groups if 'printer-name' in g['attrs']), None)

    def print_file(self, printer, data: bytes, title, copies=1, duplex=False, color=True, page_ranges=None) -> int:
        attrs = _attr(_URI, 'printer-uri', self.printer_uri(printer))
        attrs += _attr(_NAME, 'requesting-user-name', self.user) + _attr(_NAME, 'job-name', title)
        attrs += _attr(_MIME, 'document-format', 'application/octet-stream')
        job = _attr(_INTEGER, 'copies', copies)
        job += _attr(_KEYWORD, 'sides', 'two-sided-long-edge' if duplex else 'one-sided')
        if not color:
            job += _attr(_KEYWORD, 'print-color-mode', 'monochrome')
        if page_ranges:
            job += _attr(_RANGE, 'page-ranges', *page_ranges)
        groups = self._op(PRINT_JOB, f'/printers/{quote(printer)}', attrs, job, data, timeout=60)
        job_id = next((g['attrs']['job-id'][0] for g in groups if 'job-id' in g['attrs']), None)
        if not isinstance(job_id, int):
            raise IppError('CUPS no devolvió el número de trabajo')
        return job_id

    def cancel(self, printer, job_id: int):
        attrs = _attr(_URI, 'printer-uri', self.printer_uri(printer)) + _attr(_INTEGER, 'job-id', job_id)
        attrs += _attr(_NAME, 'requesting-user-name', self.user)
        self._op(CANCEL_JOB, '/jobs/', attrs)


def page_ranges(text: str | None) -> list[tuple[int, int]] | None:
    """'1-3,5' → [(1, 3), (5, 5)]."""
    if not text:
        return None
    out = []
    for part in text.split(','):
        lo, _, hi = part.partition('-')
        out.append((int(lo), int(hi or lo)))
    return out
