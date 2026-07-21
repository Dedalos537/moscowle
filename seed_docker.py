import random
from datetime import datetime, timedelta

from flask_bcrypt import Bcrypt

from app import create_app, db
from app.models import Appointment, SessionMetrics, User

app = create_app()
bcrypt = Bcrypt(app)

with app.app_context():
    db.create_all()

    admin = User(
        email='diegocenteno537@gmail.com',
        password=bcrypt.generate_password_hash('Rucula_530').decode('utf-8'),
        username='admin',
        role='admin',
        is_active=True,
    )
    therapist = User(
        email='terapeuta@test.com',
        password=bcrypt.generate_password_hash('terapia123').decode('utf-8'),
        username='Dra. Maria Lopez',
        role='terapista',
        is_active=True,
    )
    patient = User(
        email='paciente@test.com',
        password=bcrypt.generate_password_hash('paciente123').decode('utf-8'),
        username='Carlos Perez',
        role='jugador',
        is_active=True,
    )
    db.session.add_all([admin, therapist, patient])
    db.session.flush()

    patient.assigned_therapist_id = therapist.id

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(7):
        day = today - timedelta(days=i)
        db.session.execute(
            db.text(
                'INSERT INTO appointment (is_active, therapist_id, patient_id, title, start_time, end_time, status, attendance) '
                'VALUES (TRUE, :tid, :pid, :title, :st, :et, :status, :attendance)'
            ),
            {
                'tid': therapist.id,
                'pid': patient.id,
                'title': f'Sesion {i + 1}',
                'st': day + timedelta(hours=10),
                'et': day + timedelta(hours=11),
                'status': 'completed' if i > 0 else 'scheduled',
                'attendance': 'present',
            },
        )
        db.session.flush()

    result = db.session.execute(
        db.text('SELECT id FROM appointment WHERE patient_id = :pid ORDER BY start_time'), {'pid': patient.id}
    )
    appt_ids = [row[0] for row in result]

    for i, appt_id in enumerate(appt_ids):
        day = today - timedelta(days=i)
        db.session.execute(
            db.text(
                'INSERT INTO session_metrics (is_active, user_id, session_id, game_name, accurracy, avg_time, date, prediction) '
                'VALUES (TRUE, :uid, :sid, :game, :acc, :avg, :dt, 0)'
            ),
            {
                'uid': patient.id,
                'sid': appt_id,
                'game': 'Aprender Flechas',
                'acc': round(random.uniform(60, 100), 2),
                'avg': round(random.uniform(0.5, 3.0), 2),
                'dt': day,
            },
        )

    db.session.execute(
        db.text('UPDATE "user" SET payment_due_date = :dd, payment_amount = :amt WHERE id = :pid'),
        {'dd': (today + timedelta(days=25)).date(), 'amt': 200.0, 'pid': patient.id},
    )
    db.session.commit()
    print(f'OK: {User.query.count()} users, {Appointment.query.count()} appts, {SessionMetrics.query.count()} metrics')
