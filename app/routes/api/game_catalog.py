"""Catálogo de juegos y niveles de KPI.

El paciente solo ve los juegos activos para jugar: nunca KPIs ni niveles. El equipo (terapeuta, supervisor,
administrador) ve los niveles; el terapeuta solo los de sus pacientes. Editar la ficha y los umbrales es del admin.
"""

import os
import shutil

from flask import jsonify, request
from sqlalchemy import or_

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models.appointment import SessionMetrics
from app.models.game import Game
from app.models.user import User
from app.routes.api import api_bp
from app.services import game_catalog, game_kpis

STAFF = ('admin', 'supervisor', 'terapista')


def _is_staff():
    return current_user.role in STAFF


def _patient_ids_for_therapist(therapist):
    ids = {u.id for u in User.query.filter_by(assigned_therapist_id=therapist.id).all()}
    ids |= {u.id for u in therapist.associated_patients.all()}
    return ids


def _can_see_patient(pid):
    if current_user.role in ('admin', 'supervisor'):
        return True
    return current_user.role == 'terapista' and pid in _patient_ids_for_therapist(current_user)


@api_bp.route('/games/catalog', methods=['GET'])
@login_required
def games_catalog():
    game_catalog.sync_catalog()
    staff = _is_staff()
    q = Game.query
    if not staff or request.args.get('active') == '1':
        q = q.filter(Game.is_active.is_(True))
    games = [g for g in q.order_by(Game.title).all()]
    if not staff:
        games = [g for g in games if game_catalog.file_exists(g)]
    out = {'success': True, 'games': [game_catalog.serialize(g, staff) for g in games]}
    if staff:
        out['kpi_catalog'] = [{'key': k, **v} for k, v in game_kpis.KPIS.items()]
        out['levels'] = game_kpis.LEVELS
        out['kinds'] = game_catalog.KINDS
    return jsonify(out)


@api_bp.route('/games/<int:game_id>', methods=['PATCH'])
@login_required
def games_update(game_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Solo el administrador edita los juegos.'}), 403
    game = db.session.get(Game, game_id)
    if game is None:
        return jsonify({'success': False, 'error': 'Juego no encontrado'}), 404
    data = request.get_json(silent=True) or {}

    if 'title' in data:
        title = (data.get('title') or '').strip()
        if not title or len(title) > 100:
            return jsonify({'success': False, 'error': 'El nombre es obligatorio (máx. 100 caracteres).'}), 400
        game.title = title
    if 'description' in data:
        game.description = (data.get('description') or '').strip()[:1000] or None
    if 'is_active' in data:
        game.is_active = bool(data['is_active'])
    meta = {}
    for key, limit in (('area', 80), ('ages', 20)):
        if key in data:
            meta[key] = (data.get(key) or '').strip()[:limit] or None
    if 'kind' in data:
        if data['kind'] not in game_catalog.KINDS:
            return jsonify({'success': False, 'error': 'Tipo de juego no válido'}), 400
        meta['kind'] = data['kind']
    if 'kpis' in data:
        if data['kpis'] is None:
            meta['kpis'] = None  # vuelve al perfil por defecto de su tipo
        else:
            try:
                meta['kpis'] = game_kpis.validate_profile(data['kpis'])
            except game_kpis.KpiError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
    if meta:
        game_catalog.set_meta(game, **meta)
    db.session.commit()
    return jsonify({'success': True, 'game': game_catalog.serialize(game, True)})


@api_bp.route('/games/<int:game_id>', methods=['DELETE'])
@login_required
def games_delete(game_id):
    """Con partidas registradas el juego solo se desactiva: borrarlo dejaría huérfano el historial."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Solo el administrador elimina juegos.'}), 403
    game = db.session.get(Game, game_id)
    if game is None:
        return jsonify({'success': False, 'error': 'Juego no encontrado'}), 404
    plays = SessionMetrics.query.filter(
        or_(SessionMetrics.game_id == game.id, SessionMetrics.game_name == game.filename)
    ).count()
    if plays:
        game.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'archived': True, 'plays': plays})

    base = game_catalog.games_dir()
    meta = game_catalog.meta_of(game)
    target = os.path.normpath(os.path.join(base, meta.get('entry') or game.filename))
    if target.startswith(base + os.sep) and game.filename not in game_catalog.BUILTIN:
        folder = meta.get('folder')
        if folder:
            path = os.path.normpath(os.path.join(base, folder))
            if path.startswith(base + os.sep) and os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
        elif os.path.isfile(target):
            os.remove(target)
    db.session.delete(game)
    db.session.commit()
    return jsonify({'success': True, 'archived': False})


@api_bp.route('/games/<int:game_id>/levels', methods=['GET'])
@login_required
def games_levels(game_id):
    """Nivel de cada paciente en este juego (el terapeuta ve solo los suyos)."""
    if not _is_staff():
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    game = db.session.get(Game, game_id)
    if game is None:
        return jsonify({'success': False, 'error': 'Juego no encontrado'}), 404

    q = db.session.query(SessionMetrics.user_id).filter(
        or_(SessionMetrics.game_id == game.id, SessionMetrics.game_name == game.filename)
    )
    player_ids = {row[0] for row in q.distinct().all()}
    if current_user.role == 'terapista':
        player_ids &= _patient_ids_for_therapist(current_user)
    users = {u.id: u for u in User.query.filter(User.id.in_(player_ids)).all()} if player_ids else {}

    rows = []
    for pid, user in users.items():
        lv = game_kpis.patient_levels(game, pid)
        rows.append({'patient_id': pid, 'patient': user.username, **lv})
    rows.sort(key=lambda r: (r['level_index'] is None, r['level_index'] or 0, r['patient'].lower()))
    distribution = {lvl['id']: 0 for lvl in game_kpis.LEVELS}
    for r in rows:
        if r['level']:
            distribution[r['level']] += 1
    return jsonify(
        {
            'success': True,
            'game': game_catalog.serialize(game, True),
            'patients': rows,
            'distribution': distribution,
            'levels': game_kpis.LEVELS,
        }
    )


@api_bp.route('/games/levels/patient/<int:patient_id>', methods=['GET'])
@login_required
def games_levels_for_patient(patient_id):
    """Niveles de un paciente en cada juego que jugó."""
    if not _is_staff() or not _can_see_patient(patient_id):
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    game_ids = {
        row[0]
        for row in db.session.query(SessionMetrics.game_id)
        .filter(SessionMetrics.user_id == patient_id, SessionMetrics.game_id.isnot(None))
        .distinct()
        .all()
    }
    games = Game.query.filter(Game.id.in_(game_ids)).all() if game_ids else []
    out = [{'game': game_catalog.serialize(g, True), **game_kpis.patient_levels(g, patient_id)} for g in games]
    out.sort(key=lambda r: r['last_played'] or '', reverse=True)
    return jsonify({'success': True, 'games': out, 'levels': game_kpis.LEVELS})
