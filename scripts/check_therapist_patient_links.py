"""Informe de coherencia entre las TRES formas de guardar "este terapeuta
atiende a este paciente". NO escribe nada: no se puede decidir cual es la
buena sin saber cual usa el resto del sistema.

El dominio es N:M (un paciente puede tener varios terapeutas y al reves), y
el sistema guarda el vinculo de tres maneras distintas que NO coinciden:

  patient_therapist        tabla puente, 67 filas, la unica con forma N:M
  assigned_therapist_id    columna unica en user, solo puede guardar UNO
  appointment.therapist_id quien impartio cada sesion

Medido en produccion: para el terapeuta 1 las tres dan 42, 26 y 16 pacientes
respectivamente, y hay 5 pacientes que solo estan en la columna y no en la
puente. Ninguna fuente contiene a las otras, asi que no hay forma automatica de
elegir: hace falta que alguien diga cual manda.

Uso:
    python -m scripts.check_therapist_patient_links
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402


def main():
    app = create_app()
    with app.app_context():

        def ids(sql, **kw):
            return {r[0] for r in db.session.execute(sa.text(sql), kw).fetchall()}

        terapeutas = db.session.execute(sa.text(
            "select id, username from user where role='terapista' order by id")).fetchall()
        pacientes = {r[0] for r in db.session.execute(
            sa.text("select id from user where role='jugador'")).fetchall()}

        print(f'Pacientes: {len(pacientes)} | Terapeutas: {len(terapeutas)}\n')
        print(f'{"ter":<5}{"nombre":<24}{"puente":>8}{"columna":>8}{"sesiones":>10}{"hoy+":>6}   veredicto')
        for tid, nombre in terapeutas:
            puente = ids("select patient_id from patient_therapist where therapist_id=:t", t=tid)
            columna = ids(
                "select id from user where assigned_therapist_id=:t and role='jugador'", t=tid)
            sesiones = ids(
                "select distinct patient_id from appointment "
                "where therapist_id=:t and status!='cancelled'", t=tid)
            hoy = ids(
                "select distinct patient_id from appointment "
                "where therapist_id=:t and status!='cancelled' and start_time>=now()", t=tid)
            union = puente | columna | sesiones
            if not (puente | columna | sesiones):
                v = 'sin ningun vinculo'
            elif puente and puente >= (columna | sesiones):
                v = 'la puente es la mas amplia'
            elif not (columna | sesiones) - puente:
                v = 'la puente contiene a las demas'
            else:
                v = f'DISCREPANCIA: {len(puente - (columna | sesiones))} solo en puente, ' \
                    f'{len((columna | sesiones) - puente)} fuera'
            print(f'{tid:<5}{nombre[:22]:<24}{len(puente):>8}{len(columna):>8}'
                  f'{len(sesiones):>10}{len(hoy):>6}   {v}')
            if puente - (columna | sesiones):
                print(f'      solo en la puente: {sorted(puente - (columna | sesiones))}')
            if (columna | sesiones) - puente:
                print(f'      fuera de la puente: {sorted((columna | sesiones) - puente)}')

        huerfanos = pacientes - ids("select distinct patient_id from patient_therapist")
        print(f'\nPacientes sin ninguna fila en patient_therapist: {len(huerfanos)} '
              f'{sorted(huerfanos) if huerfanos else ""}')
        print('Ninguna fila se modifico. Esto es solo un informe.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
