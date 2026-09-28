"""Repara User.assigned_therapist_id para que refleje a quien atiende de verdad.

El campo se desactualizo: Liam (14) y Valentina (42) apuntaban al terapeuta 13
pero sus sesiones las impartia el 1. El motor de politica lo compensa con la
agenda, pero la dato sucio se propaga a cualquier consulta que lo use.

REGLA (deliberadamente conservadora). Para cada paciente se busca el terapeuta
de su sesion no cancelada mas reciente, y se reasigna solo si:

  1. no tiene terapeuta asignado, o el asignado no existe / esta inactivo, o
  2. el terapeuta de la sesion mas reciente es distinto del asignado Y esa
     sesion es POSTERIOR a la ultima sesion del asignado.

La condicion 2 es la que corrige a Liam y Valentina sin tocar a un paciente al
que se reasigno correctamente y simplemente no se ha vuelto a ver: en ese caso
la sesion mas reciente sigue siendo del terapeuta asignado y no hay nada que
arreglar. Reasignar por 'mayoria historica' seria peor: tiraria el dato
correcto por Sessiones antiguas.

Uso:
    python -m scripts.sync_assigned_therapist              # dry-run, no escribe
    python -m scripts.sync_assigned_therapist --apply      # escribe
    python -m scripts.sync_assigned_therapist --apply --yes # sin confirmacion

El dry-run imprime cada fila que cambiaria, con el motivo. Revisarlo antes de
escribir: esto modifica datos de pacientes.
"""
import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as _app  # noqa: E402
from app.extensions import db  # noqa: E402

FECHA_CORTE_HISTORIAL = timedelta(days=365 * 2)


def analizar(corte_meses=24):
    """Devuelve (reparaciones, omitidas) sin escribir nada."""
    from app.models.appointment import Appointment
    from app.models.user import User

    terapeutas = {u.id: u for u in User.query.filter_by(role='terapista').all()}

    # ultima sesion no cancelada por paciente, y ultima del terapeuta asignado
    desde = datetime.utcnow() - FECHA_CORTE_HISTORIAL
    sesiones = (
        db.session.query(
            Appointment.patient_id,
            Appointment.therapist_id,
            Appointment.start_time,
        )
        .filter(Appointment.status != 'cancelled', Appointment.start_time >= desde)
        .order_by(Appointment.patient_id, Appointment.start_time.desc())
        .all()
    )

    por_paciente = {}
    for pid, tid, when in sesiones:
        por_paciente.setdefault(pid, []).append((when, tid))

    reparaciones, omitidas = [], []
    pacientes = User.query.filter_by(role='jugador').all()

    for p in pacientes:
        historial = por_paciente.get(p.id)
        if not historial:
            continue
        real = historial[0][1]
        if real is None or real not in terapeutas:
            omitidas.append((p, p.assigned_therapist_id, None, 'sin terapeuta valido en la sesion mas reciente'))
            continue
        actual = p.assigned_therapist_id

        if actual is None or actual not in terapeutas:
            reparaciones.append((p, actual, real, 'sin asignacion valida'))
            continue
        if not getattr(terapeutas[actual], 'is_active', True):
            reparaciones.append((p, actual, real, 'terapeuta asignado inactivo'))
            continue
        if real == actual:
            omitidas.append((p, actual, real, 'ya coincide'))
            continue

        ultima_asignada = next((w for w, t in historial if t == actual), None)
        if ultima_asignada is not None and historial[0][0] <= ultima_asignada:
            omitidas.append((p, actual, real, 'la sesion del asignado es mas reciente'))
            continue

        reparaciones.append((p, actual, real, 'atiende hoy otro terapeuta'))
    return reparaciones, omitidas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='escribe de verdad')
    ap.add_argument('--yes', action='store_true', help='sin confirmacion')
    args = ap.parse_args()

    app = _app.create_app()
    with app.app_context():
        reparaciones, omitidas = analizar()
        print(f'Candidatas a reparar: {len(reparaciones)}')
        print(f'Sin cambios:          {len(omitidas)}\n')
        for p, antes, despues, motivo in reparaciones:
            nom_antes = antes if antes else 'ninguno'
            print(
                f'  paciente {p.id:>3} {p.username[:28]:<28} '
                f'{motivo}: {nom_antes} -> {despues}'
            )
        if not args.apply:
            print('\nDRY-RUN: no se escribio nada. Usa --apply para confirmar.')
            return 0
        if not args.yes and input(f'\nEscribir {len(reparaciones)} cambios? [s/N] ').strip().lower() != 's':
            print('Cancelado.')
            return 1

        for p, _antes, despues, _motivo in reparaciones:
            p.assigned_therapist_id = despues
        db.session.commit()
        print(f'Escritos {len(reparaciones)} cambios.')
        try:
            from app.services.policy import get_policy

            get_policy().clear_cache()
        except Exception as e:
            print(f'aviso: no se pudo limpiar la cache de politica ({e}); '
                  f'el alcance se recalculara al reiniciar')
    return 0


if __name__ == '__main__':
    sys.exit(main())
