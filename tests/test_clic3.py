"""Clic 3.0 → JClic: lectura de actividades y paquetes, contenedor .pcc y subida al catálogo."""

import io
import json
import struct
import uuid
import zipfile
from xml.dom import minidom

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Game, User
from app.services import clic3

CHINC = clic3.CHINC
FONT = '20,8,0,0,700,0,0,0,0,3,2,1,34,Arial'
TRIPLE = 'FFFFFF,000000,808080,0'


def enc(text):
    """Texto → bytes como los guardaba Clic (cp1252 con los marcadores 0x8E/0x8F)."""
    out = bytearray()
    for ch in text:
        if ch in clic3.ANSI:
            out.append(0x80 + clic3.ANSI.index(ch))
        else:
            out.append(ord(ch))
    return bytes(out)


def header(desc, init, end, bools, cw, ch):
    return [
        '119',
        desc,
        '‡',
        FONT,
        TRIPLE,
        FONT,
        TRIPLE,
        FONT,
        TRIPLE,
        '1,1,1,1,C0C0C0,C0C0C0,-1,-1,1,0,0',
        '',
        init,
        end,
        str(bools),
        cw,
        ch,
        '0',
        '',
        '',
        '0',
        '',
        '',
    ]


ASS = '\r\n'.join(
    header('Asociación de prueba', 'Une cada animal con su sonido', '¡Muy bien!', 3, '140;140', '60;60')
    + ['0', '3', '1', 'animales.txt', 'sonidos.txt', '1', '1', '0', '0']
)
TARGET = f'{CHINC}_,0,4,4,0,0,200,60,0,{CHINC}guau|Guau{CHINC}{CHINC}{CHINC}{CHINC}guau{CHINC}'
TXA = '\r\n'.join(
    header('Huecos de prueba', 'Completa la frase', '¡Bien!', 0, '500', '300')
    + [
        FONT,
        TRIPLE,
        '0000FF,C0C0C0,FFFFFF,0000FF',
        '0,662,3,6,0,30,12',
        'Revisar',
        f'El perro dice {TARGET}.',
        '‡',
        '‡',
        '‡',
    ]
)
SOP = '\r\n'.join(
    header('Sopa de prueba', 'Busca los colores', '¡Perfecto!', 0, '30', '30')
    + ['*', '1', '1', '4', '3', '2', 'ROJO', 'AZUL', 'XXXX', 'rojo', 'azul']
)
PAC = '\r\n'.join(['119', 'Paquete de prueba', '‡', 'asoc.ass', 'texto.txa', 'sopa.sop'])
FILES = {
    'asoc.ass': enc(ASS),
    'texto.txa': enc(TXA),
    'sopa.sop': enc(SOP),
    'prueba.pac': enc(PAC),
    'animales.txt': enc('Perro\r\nGato\r\nVaca\r\n'),
    'sonidos.txt': enc('Guau\r\nMiau\r\nMuu\r\n'),
}


def pcc(files):
    """Arma un contenedor .pcc (cabecera PCC00, índice y datos en posiciones absolutas)."""
    head = b'PCC00\r\nPrueba\r\n' + struct.pack('<HI', len(files), 0)
    index_len = sum(len(n) + 1 + 8 for n in files)
    offset = len(head) + index_len
    index = b''
    blob = b''
    for name, data in files.items():
        index += name.upper().encode() + b'\x00' + struct.pack('<II', offset + len(blob), len(data))
        blob += data
    return head + index + blob


def test_reads_each_activity_type():
    a = clic3.read_activity('asoc.ass', FILES['asoc.ass'])
    assert (a.mode, a.puz_mode, a.ncw, a.nch) == (clic3.ASSOCIA, clic3.NORMAL, 3, 1)
    assert a.content[:2] == ['animales.txt', 'sonidos.txt'] and a.init_mess == 'Une cada animal con su sonido'
    t = clic3.read_activity('texto.txa', FILES['texto.txa'])
    assert t.puz_mode == clic3.FORATS and CHINC in t.base_text and t.check_text == 'Revisar'
    s = clic3.read_activity('sopa.sop', FILES['sopa.sop'])
    assert s.grid_text == ['ROJO', 'AZUL', 'XXXX'] and s.tags[0] == ['ROJO', 'AZUL']
    assert clic3.read_pac('prueba.pac', FILES['prueba.pac']).acts == ['asoc.ass', 'texto.txa', 'sopa.sop']


def test_colors_follow_windows_bgr():
    assert clic3.color('FF0000') == '0x0000FF'
    assert clic3.color('0000FF') == '0xFF0000'


def test_builds_a_valid_jclic_project():
    project = clic3.build_project(FILES, 'Prueba')
    dom = minidom.parseString(project.xml.encode('utf-8'))
    classes = [a.getAttribute('class') for a in dom.getElementsByTagName('activity')]
    assert classes == ['@associations.SimpleAssociation', '@text.FillInBlanks', '@textGrid.WordSearch']
    assert project.activities == 3 and project.warnings == []
    xml = project.xml
    assert '<p>Perro</p>' in xml and '<p>Muu</p>' in xml
    assert '<answer>guau</answer><answer>Guau</answer>' in xml
    assert '<response fill="_" length="4" maxLength="4" />' in xml and '<text>guau</text></target>' in xml
    assert '<checkButton>Revisar</checkButton>' not in xml  # con corrección continua no hay botón
    assert '<row>ROJO</row>' in xml and '<clue id="1">AZUL</clue>' in xml
    # La secuencia empieza en el .pac para que «ir al paquete» funcione.
    item = dom.getElementsByTagName('item')[0]
    assert item.getAttribute('id') == 'prueba.pac' and item.getAttribute('name') == 'asoc.ass'


def test_reads_a_pcc_container():
    files = clic3.read_pcc(pcc(FILES))
    assert files['asoc.ass'] == FILES['asoc.ass'] and files['sonidos.txt'] == FILES['sonidos.txt']
    with pytest.raises(clic3.Clic3Error):
        clic3.read_pcc(b'NOPE\r\n')


def test_broken_activity_is_reported_not_fatal():
    files = {**FILES, 'rota.puz': enc('119\r\nRota\r\n‡\r\n')}
    project = clic3.build_project(files, 'Prueba')
    assert project.activities == 3
    assert any('rota.puz' in w for w in project.warnings)


def _admin():
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'adm{tag}', email=f'{tag}@c3.test', password='x', role='admin')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def games_dir(tmp_path, monkeypatch):
    from app.services import game_catalog

    monkeypatch.setattr(game_catalog, 'games_dir', lambda: str(tmp_path))
    return tmp_path


def _upload(client, user, name, data, title='Paquete'):
    return client.post(
        '/api/games/upload',
        data={'file': (io.BytesIO(data), name), 'title': title},
        headers={'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))},
        content_type='multipart/form-data',
    )


def test_upload_pcc_creates_a_playable_game(client, games_dir):
    r = _upload(client, _admin(), 'EJEMPLO.PCC', pcc(FILES), 'Animales y colores')
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body['activities'] == 3
    game = db.session.get(Game, body['game']['id'])
    meta = json.loads(game.meta)
    assert meta['kind'] == 'clic3' and meta['entry'].endswith('/project.jclic')
    assert (games_dir / meta['entry']).read_text(encoding='utf-8').startswith('<?xml')
    catalog = client.get(
        '/api/games/catalog', headers={'Authorization': 'Bearer ' + create_access_token(identity=str(_admin().id))}
    ).get_json()
    entry = next(g for g in catalog['games'] if g['id'] == game.id)
    assert entry['kind'] == 'clic3' and '_jclic_launcher.html?game=clic3/' in entry['play_url']
    db.session.delete(game)
    db.session.commit()


def test_upload_zip_with_pac_and_loose_files(client, games_dir):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for name, data in FILES.items():
            zf.writestr(f'CLIC/{name.upper()}', data)
    r = _upload(client, _admin(), 'actividades.zip', buf.getvalue())
    assert r.status_code == 200 and r.get_json()['activities'] == 3
    db.session.delete(db.session.get(Game, r.get_json()['game']['id']))
    db.session.commit()


def test_web_zip_needs_index_and_safe_paths(client, games_dir):
    admin = _admin()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('../escape.html', '<h1>x</h1>')
    assert _upload(client, admin, 'malo.zip', buf.getvalue()).status_code == 400

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('juego/index.html', '<h1>Hola</h1>')
        zf.writestr('juego/app.js', 'console.log(1)')
        zf.writestr('juego/virus.exe', 'MZ')
    r = _upload(client, admin, 'juego.zip', buf.getvalue(), 'Mi juego')
    assert r.status_code == 200
    game = db.session.get(Game, r.get_json()['game']['id'])
    assert (games_dir / game.filename).exists() and not list(games_dir.rglob('virus.exe'))
    assert r.get_json()['warnings']
    db.session.delete(game)
    db.session.commit()


def test_patients_cannot_upload(client, games_dir):
    tag = uuid.uuid4().hex[:8]
    patient = User(username=f'pac{tag}', email=f'{tag}@c3.test', password='x', role='jugador')
    db.session.add(patient)
    db.session.commit()
    assert _upload(client, patient, 'x.html', b'<h1>x</h1>').status_code == 403
