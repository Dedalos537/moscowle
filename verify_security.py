from app import create_app, db
from app.models import User, Appointment, Game
from datetime import datetime
import json
from app.extensions import bcrypt
from config import Config

class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_security_v2.db'
    WTF_CSRF_ENABLED = False
    TESTING = True

app = create_app(TestConfig)

# Clean up previous run
import os
if os.path.exists('test_security_v2.db'):
    os.remove('test_security_v2.db')

with app.app_context():
    # Create users
    pw_hash = bcrypt.generate_password_hash('pw').decode('utf-8')
    therapist = User(username='doc', email='doc@test.com', password=pw_hash, role='terapista')
    patient = User(username='pat', email='pat@test.com', password=pw_hash, role='jugador')
    hacker = User(username='hacker', email='hacker@test.com', password=pw_hash, role='jugador')
    db.session.add_all([therapist, patient, hacker])
    db.session.commit()
    
    print(f"IDs: Therapist={therapist.id}, Patient={patient.id}, Hacker={hacker.id}")
    
    # Create session for patient
    appt = Appointment(
        therapist_id=therapist.id,
        patient_id=patient.id,
        start_time=datetime.utcnow(),
        status='scheduled',
        games=json.dumps(['game1.html'])
    )
    db.session.add(appt)
    db.session.commit()
    appt_id = appt.id
    
    t_id = therapist.id
    p_id = patient.id
    h_id = hacker.id

# Move tests outside app context to ensure clean request contexts
print(f"IDs: Therapist={t_id}, Patient={p_id}, Hacker={h_id}")

# Test 1: Hacker tries to save game for patient's session
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['_user_id'] = str(h_id)
        sess['_fresh'] = True
        
    res = client.post('/api/save_game', json={
        'session_id': appt_id,
        'game_name': 'game1.html',
        'accuracy': 100,
        'avg_time': 1.0
    })
    print(f"Hacker attempt status: {res.status_code}")
    if res.status_code == 403:
        print("PASS: Hacker blocked")
    else:
        print(f"FAIL: Hacker allowed ({res.status_code})")

# Test 2: Patient saves game correctly
print("\n--- Test 2 ---")
with app.test_client() as client:
    with client.session_transaction() as sess:
        print(f"Setting session user_id to {p_id}")
        sess['_user_id'] = str(p_id)
        sess['_fresh'] = True
        
    res = client.post('/api/save_game', json={
        'session_id': appt_id,
        'game_name': 'game1.html',
        'accuracy': 100,
        'avg_time': 1.0
    })
    print(f"Patient attempt status: {res.status_code}")
    if res.status_code == 200:
        print("PASS: Patient allowed")
    else:
        print(f"FAIL: Patient blocked ({res.status_code})")
        
# Test 3: Patient tries to save to completed session
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['_user_id'] = str(p_id)
        sess['_fresh'] = True
        
    res = client.post('/api/save_game', json={
        'session_id': appt_id,
        'game_name': 'game1.html',
        'accuracy': 100,
        'avg_time': 1.0
    })
    print(f"Completed session attempt status: {res.status_code}")
    if res.status_code == 400:
        print("PASS: Completed session blocked")
    else:
        print(f"FAIL: Completed session allowed ({res.status_code})")

# Cleanup
if os.path.exists('test_security_v2.db'):
    os.remove('test_security_v2.db')
