import json

from flask import current_app


def parse_objectives(planned_text):
    objectives = []
    lines = planned_text.split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('## '):
            name = stripped[3:].strip()
            if name and len(name) > 3:
                objectives.append({'name': name, 'status': 'pendiente', 'evidence': ''})
        elif stripped.startswith('- ') or stripped.startswith('* '):
            name = stripped[2:].strip()
            if name and len(name) > 5 and not name.startswith('['):
                objectives.append({'name': name, 'status': 'pendiente', 'evidence': ''})
    if not objectives:
        sentences = [s.strip() for s in planned_text.replace('\n', '. ').split('.') if len(s.strip()) > 15]
        for s in sentences[:8]:
            objectives.append({'name': s[:120], 'status': 'pendiente', 'evidence': ''})
    return objectives[:15]


def map_classification(classification):
    mapping = {
        'logrado': 'completado',
        'parcial': 'parcial',
        'no_cubierto': 'pendiente',
        'cumple': 'completado',
        'cumple_parcial': 'parcial',
        'no_cumple': 'pendiente',
    }
    return mapping.get(classification, 'pendiente')


def enrich_objectives_from_audit(objectives, audit_report_json):
    if not audit_report_json:
        return objectives
    try:
        report = json.loads(audit_report_json)
        report_objs = {o.get('name', '').lower().strip(): o for o in (report.get('objectives') or [])}
        for obj in objectives:
            key = obj['name'].lower().strip()
            if key in report_objs:
                r = report_objs[key]
                obj['status'] = map_classification(r.get('classification', ''))
                obj['evidence'] = r.get('evidence', '')
    except (json.JSONDecodeError, TypeError, AttributeError) as exc:
        current_app.logger.debug('objectives report parse failed: %s', exc)
    return objectives
