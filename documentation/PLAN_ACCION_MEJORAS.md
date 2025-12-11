# 🚀 PLAN DE ACCIÓN - MEJORAS PRIORITARIAS

**Fecha:** 9 de diciembre, 2024  
**Responsable:** Dev Team  
**Estado:** Pendiente Implementación

---

## 📋 RESUMEN EJECUTIVO

Se identificaron **18 mejoras** categorizadas por criticidad:
- 🔴 **3 Críticas** (Semana 1-2)
- 🟠 **7 Altas** (Semana 3-6)
- 🟡 **5 Medias** (Semana 7-10)
- 🟢 **3 Bajas** (Backlog)

**Tiempo Estimado Total:** 10-12 semanas (con 1 dev FT)

---

## 🔴 FASE 1: CRÍTICAS (Semanas 1-2)

### 1.1 Relación Terapeuta-Paciente Múltiple

**Criticidad:** 🔴 CRÍTICA  
**Impacto:** Permite escalabilidad, múltiples terapeutas  
**Esfuerzo:** 20 horas

#### Cambios Necesarios:

1. **Crear tabla de relación**
```python
# models.py - ADD

class TherapistPatient(db.Model):
    __tablename__ = 'therapist_patient'
    id = db.Column(db.Integer, primary_key=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), 
                             nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), 
                          nullable=False, index=True)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='active')  # active, paused, completed
    notes = db.Column(db.Text, nullable=True)
    
    therapist = db.relationship('User', foreign_keys=[therapist_id], 
                               backref='assigned_patients')
    patient = db.relationship('User', foreign_keys=[patient_id], 
                             backref='assigned_therapists')
    
    __table_args__ = (db.UniqueConstraint('therapist_id', 'patient_id', 
                                         name='_therapist_patient_uc'),)
```

2. **Actualizar User model**
```python
# models.py - MODIFY User

class User(db.Model, UserMixin):
    # ... existing fields ...
    
    # REMOVE: therapist_id field (si existe)
    # ADD: Relationship via TherapistPatient
```

3. **Funciones auxiliares**
```python
# app.py - ADD

def get_therapist_patients(therapist_id):
    """Get all active patients for a therapist"""
    return db.session.query(User).join(
        TherapistPatient,
        User.id == TherapistPatient.patient_id
    ).filter(
        TherapistPatient.therapist_id == therapist_id,
        TherapistPatient.status == 'active'
    ).all()

def get_patient_therapists(patient_id):
    """Get all active therapists for a patient"""
    return db.session.query(User).join(
        TherapistPatient,
        User.id == TherapistPatient.therapist_id
    ).filter(
        TherapistPatient.patient_id == patient_id,
        TherapistPatient.status == 'active'
    ).all()

def assign_patient_to_therapist(therapist_id, patient_id):
    """Assign patient to therapist"""
    existing = TherapistPatient.query.filter_by(
        therapist_id=therapist_id,
        patient_id=patient_id
    ).first()
    
    if existing:
        if existing.status == 'paused':
            existing.status = 'active'
            db.session.commit()
            return existing
        return existing
    
    assignment = TherapistPatient(
        therapist_id=therapist_id,
        patient_id=patient_id
    )
    db.session.add(assignment)
    db.session.commit()
    return assignment
```

4. **Actualizar rutas afectadas**
```python
# app.py - MODIFY endpoints

@app.route('/patients/add', methods=['POST'])
@login_required
def add_patient():
    # ... validaciones ...
    new_patient = User(...)
    db.session.add(new_patient)
    db.session.commit()
    
    # NEW: Assign to current therapist
    assign_patient_to_therapist(current_user.id, new_patient.id)
    # ...

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'terapista':
        # OLD: User.query.filter_by(role='jugador', is_active=True)
        # NEW:
        active_patients = get_therapist_patients(current_user.id)
        active_patients_count = len(active_patients)
        
        # ... rest of code ...
    # ...

# Actualizar todas las queries que asuman 1 solo terapeuta
```

5. **Migración de datos**
```python
# Ejecutar UNA SOLA VEZ (script)
with app.app_context():
    admin = User.query.filter_by(role='terapista').first()
    if admin:
        patients = User.query.filter_by(role='jugador', is_active=True).all()
        for patient in patients:
            assign_patient_to_therapist(admin.id, patient.id)
```

**Checklist:**
- [ ] Crear tabla TherapistPatient
- [ ] Actualizar relationships
- [ ] Crear funciones auxiliares
- [ ] Actualizar rutas (5-6 endpoints)
- [ ] Tests: Crear paciente, ver solo mis pacientes
- [ ] Migración de datos existentes

---

### 1.2 CSRF Protection

**Criticidad:** 🔴 CRÍTICA  
**Impacto:** Seguridad obligatoria  
**Esfuerzo:** 4 horas

#### Cambios Necesarios:

1. **Instalar extensión**
```bash
pip install Flask-WTF
```

2. **Configurar app**
```python
# app.py - ADD at top

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
```

3. **Actualizar formularios HTML**
```html
<!-- templates/therapist/patients.html -->
<form method="POST" action="/patients/add">
    {% csrf_token() %}  <!-- ADD THIS -->
    <input type="email" name="email" required>
    <input type="text" name="username">
    <button type="submit">Agregar</button>
</form>

<!-- Todos los formularios POST necesitan esto -->
```

4. **Para AJAX, enviar token**
```javascript
// static/app.js - ADD helper function

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').content;
}

// En base.html, agregar:
<meta name="csrf-token" content="{{ csrf_token() }}">

// Al hacer POST:
fetch('/api/sessions', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
})
```

**Checklist:**
- [ ] pip install Flask-WTF
- [ ] Configurar CSRFProtect en app.py
- [ ] Agregar {% csrf_token() %} a 8-10 formularios
- [ ] Configurar meta tag csrf-token
- [ ] Actualizar AJAX requests
- [ ] Test: POST sin token debe fallar

---

### 1.3 Mejorar IA: Usar Datos Reales

**Criticidad:** 🔴 CRÍTICA  
**Impacto:** Predicciones reales vs aleatorias  
**Esfuerzo:** 12 horas

#### Cambios Necesarios:

1. **Refactorizar ai_service.py**
```python
# ai_service.py - REPLACE

import os
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from joblib import load, dump
from sklearn.svm import SVC
from datetime import datetime

MODEL_PATH = 'ai_models/svm_model.pkl'
METRICS_PATH = 'ai_models/model_metrics.pkl'

def generate_synthetic_data(n_samples=200):
    """Generate synthetic training data when insufficient real data"""
    X = []
    Y = []
    
    for _ in range(n_samples):
        acc = np.random.uniform(20, 100)
        time = np.random.uniform(200, 3000)
        
        # Labeling logic
        if acc >= 85 and time <= 800:
            label = 1  # Avanzar
        elif acc < 50 and time > 1500:
            label = 2  # Retroceder
        else:
            label = 0  # Mantener
        
        X.append([acc, time])
        Y.append(label)
    
    return np.array(X), np.array(Y)

def get_real_training_data():
    """Load real SessionMetrics from database"""
    from models import SessionMetrics
    
    metrics = SessionMetrics.query.all()
    
    if len(metrics) < 30:
        # Si hay pocos datos reales, combinar con sintéticos
        X_real = np.array([[m.accurracy, m.avg_time] for m in metrics])
        Y_real = np.array([predict_label(m.accurracy, m.avg_time) for m in metrics])
        
        X_synth, Y_synth = generate_synthetic_data(200)
        X = np.vstack([X_real, X_synth])
        Y = np.concatenate([Y_real, Y_synth])
        return X, Y
    else:
        # Usar solo datos reales
        X = np.array([[m.accurracy, m.avg_time] for m in metrics])
        Y = np.array([predict_label(m.accurracy, m.avg_time) for m in metrics])
        return X, Y

def predict_label(accuracy, avg_time):
    """Heuristic to assign label for training"""
    if accuracy >= 85 and avg_time <= 800:
        return 1  # Avanzar
    elif accuracy < 50 and avg_time > 1500:
        return 2  # Retroceder
    else:
        return 0  # Mantener

def train_model():
    """Train SVM model with real or synthetic data"""
    print("Entrenando modelo IA...")
    
    # Obtener datos de entrenamiento
    X, Y = get_real_training_data()
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, Y, test_size=0.2, random_state=42
    )
    
    # Crear y entrenar modelo
    model = SVC(kernel='rbf', probability=True, C=1.0, gamma='scale')
    model.fit(X_train, y_train)
    
    # Evaluación
    y_pred = model.predict(X_test)
    
    metrics = {
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'precision': float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
        'recall': float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
        'f1': float(f1_score(y_test, y_pred, average='weighted', zero_division=0)),
        'trained_at': datetime.utcnow().isoformat(),
        'training_samples': len(X)
    }
    
    print(f"  Accuracy: {metrics['accuracy']:.2%}")
    print(f"  Precision: {metrics['precision']:.2%}")
    print(f"  Recall: {metrics['recall']:.2%}")
    print(f"  F1-Score: {metrics['f1']:.2%}")
    print(f"  Muestras: {len(X)}")
    
    # Guardar modelo
    model_dir = os.path.dirname(MODEL_PATH)
    if model_dir and not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
    
    dump(model, MODEL_PATH)
    dump(metrics, METRICS_PATH)
    
    print("✅ Modelo entrenado y guardado")
    return model, metrics

def predict_level(accuracy, avg_time):
    """Predict recommendation level"""
    if not os.path.exists(MODEL_PATH):
        train_model()
    
    model = load(MODEL_PATH)
    pred = model.predict([[accuracy, avg_time]])[0]
    
    labels = {
        0: "Mantener Nivel",
        1: "Avanzar Nivel",
        2: "Retroceder/Apoyo"
    }
    
    return int(pred), labels[int(pred)]

def get_model_metrics():
    """Get last training metrics"""
    if not os.path.exists(METRICS_PATH):
        return None
    return load(METRICS_PATH)

def get_cluster(metrics_data):
    """Cluster patients by performance profile (NOT USED YET)"""
    if len(metrics_data) < 3:
        return []
    kmeans = KMeans(n_clusters=min(3, len(metrics_data)), n_init=10)
    kmeans.fit(metrics_data)
    return kmeans.labels_
```

2. **Reentrenamiento periódico**
```python
# app.py - ADD

from apscheduler.schedulers.background import BackgroundScheduler
from ai_service import train_model

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)  # 2 AM daily
def scheduled_model_training():
    """Retrain model daily with new data"""
    try:
        train_model()
        print("✅ Daily model retraining completed")
    except Exception as e:
        print(f"❌ Error in scheduled training: {str(e)}")

# Start scheduler
if __name__ == '__main__':
    scheduler.start()
    app.run(debug=True, port=5000)
```

3. **Endpoint para admin entrenar manual**
```python
# app.py - ADD

@app.route('/admin/train-model', methods=['POST'])
@login_required
def admin_train_model():
    """Admin endpoint to manually trigger model training"""
    if current_user.role != 'terapista' or current_user.email != os.getenv('ADMIN_EMAIL'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    try:
        model, metrics = train_model()
        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

**Checklist:**
- [ ] Refactorizar ai_service.py
- [ ] Implementar get_real_training_data()
- [ ] Agregar train_test_split y métricas
- [ ] Instalar APScheduler
- [ ] Configurar reentrenamiento diario
- [ ] Tests: Entrenar con datos reales
- [ ] Documentar en README

---

## 🟠 FASE 2: ALTAS (Semanas 3-6)

### 2.1 Persistencia de Nivel Adaptativo

**Criticidad:** 🟠 ALTA  
**Impacto:** Dificultad realmente adaptativa  
**Esfuerzo:** 8 horas

#### Cambios:

1. **models.py - Actualizar User**
```python
class User(db.Model, UserMixin):
    # ... existing fields ...
    
    # ADD THESE:
    current_level = db.Column(db.Integer, default=1)
    max_level_reached = db.Column(db.Integer, default=1)
    last_level_update = db.Column(db.DateTime, nullable=True)
    level_update_reason = db.Column(db.String(255), nullable=True)
```

2. **app.py - Función para actualizar nivel**
```python
def update_player_level(user_id, prediction_code):
    """Update player's current level based on IA prediction"""
    user = User.query.get(user_id)
    if not user:
        return
    
    old_level = user.current_level
    
    if prediction_code == 1:  # Avanzar
        user.current_level = min(user.current_level + 1, 10)
        reason = "Rendimiento alto sostenido"
    elif prediction_code == 2:  # Retroceder
        user.current_level = max(user.current_level - 1, 1)
        reason = "Rendimiento bajo, soporte necesario"
    else:  # Mantener
        reason = "Rendimiento consistente"
    
    # Track max level
    user.max_level_reached = max(user.max_level_reached, user.current_level)
    user.last_level_update = datetime.utcnow()
    user.level_update_reason = reason
    
    db.session.commit()
    
    # Log change
    if old_level != user.current_level:
        print(f"  [LEVEL UPDATE] {user.username}: {old_level} → {user.current_level}")
        create_notification(
            user_id=user_id,
            message=f"Tu nivel cambió de {old_level} a {user.current_level}: {reason}"
        )

# En save_game endpoint:
@app.route('/api/save_game', methods=['POST'])
@login_required
def save_game():
    data = request.json
    acc = data['accuracy']
    time = data['avg_time']
    pred_code, pred_text = predict_level(acc, time)

    metric = SessionMetrics(
        user_id=current_user.id,
        game_name='Reflejos Rápidos',
        accurracy=acc,
        avg_time=time,
        prediction=pred_code
    )
    db.session.add(metric)
    db.session.commit()
    
    # NEW:
    update_player_level(current_user.id, pred_code)
    
    return jsonify({
        'recommendation': pred_text,
        'code': pred_code,
        'new_level': current_user.current_level  # ADD THIS
    })
```

3. **Frontend - Mostrar nivel actual**
```javascript
// static/game.js

async function saveGameResult(accuracy, avgTime) {
    const response = await fetch('/api/save_game', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            accuracy: accuracy,
            avg_time: avgTime
        })
    });
    
    const data = await response.json();
    
    // Show result with level update
    showResult(data.recommendation, data.code, data.new_level);
}

function showResult(recommendation, code, newLevel) {
    let message = '';
    let emoji = '';
    
    if (code === 1) {
        emoji = '✨';
        message = `¡Excelente! Avanzas al nivel ${newLevel}`;
    } else if (code === 2) {
        emoji = '📚';
        message = `Necesitas práctica. Nivel ajustado a ${newLevel}`;
    } else {
        emoji = '✓';
        message = `¡Bien hecho! Mantienes nivel ${newLevel}`;
    }
    
    // Show modal with animation
    showModal(`${emoji} ${message}`);
}
```

**Checklist:**
- [ ] Agregar campos a User
- [ ] Crear función update_player_level()
- [ ] Actualizar save_game endpoint
- [ ] Frontend muestra nivel actual
- [ ] Migración de datos (setear nivel 1 por defecto)
- [ ] Tests

---

### 2.2 Email Notifications para Eventos

**Criticidad:** 🟠 ALTA  
**Impacto:** Usuarios no pierden eventos importantes  
**Esfuerzo:** 10 horas

#### Cambios:

1. **Crear plantillas de email**
```bash
mkdir -p templates/emails
touch templates/emails/appointment_notification.html
touch templates/emails/message_notification.html
touch templates/emails/level_update.html
```

2. **app.py - Funciones de email**
```python
def send_appointment_email(recipient_email, appointment, patient_name):
    """Send appointment notification email"""
    if not app.config.get('MAIL_USERNAME'):
        return False
    
    try:
        subject = f"Nueva cita programada - {appointment.start_time.strftime('%d %b %Y')}"
        
        html = render_template('emails/appointment_notification.html',
            appointment=appointment,
            patient_name=patient_name,
            datetime_str=appointment.start_time.strftime('%d de %B, %Y a las %H:%M')
        )
        
        msg = MailMessage(
            subject=subject,
            recipients=[recipient_email],
            html=html
        )
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Failed to send appointment email: {str(e)}")
        return False

def send_message_notification_email(recipient_email, sender_name, message_preview):
    """Send new message notification email"""
    if not app.config.get('MAIL_USERNAME'):
        return False
    
    try:
        subject = f"Nuevo mensaje de {sender_name}"
        
        html = render_template('emails/message_notification.html',
            sender_name=sender_name,
            preview=message_preview[:100],
            messages_link=url_for('messages_list', _external=True)
        )
        
        msg = MailMessage(
            subject=subject,
            recipients=[recipient_email],
            html=html
        )
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Failed to send message email: {str(e)}")
        return False

def send_level_update_email(recipient_email, patient_name, old_level, new_level, reason):
    """Send level update notification"""
    if not app.config.get('MAIL_USERNAME'):
        return False
    
    try:
        if new_level > old_level:
            subject = f"¡Felicidades! Avanzaste al nivel {new_level}"
        else:
            subject = f"Ajuste de nivel de dificultad"
        
        html = render_template('emails/level_update.html',
            patient_name=patient_name,
            old_level=old_level,
            new_level=new_level,
            reason=reason
        )
        
        msg = MailMessage(
            subject=subject,
            recipients=[recipient_email],
            html=html
        )
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Failed to send level update email: {str(e)}")
        return False
```

3. **Actualizar endpoints para enviar email**
```python
# En api_create_session:
@app.route('/api/sessions', methods=['POST'])
@login_required
def api_create_session():
    # ... existing code ...
    
    appt = Appointment(...)
    db.session.add(appt)
    db.session.commit()
    
    # NEW: Send email to patient
    send_appointment_email(
        patient.email,
        appt,
        patient.username
    )
    
    # ... rest of code ...

# En send_message:
@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    # ... existing code ...
    
    message = Message(...)
    db.session.add(message)
    db.session.commit()
    
    # NEW: Send email to receiver
    send_message_notification_email(
        receiver.email,
        current_user.username,
        message.body
    )
    
    # ... rest ...

# En update_player_level:
def update_player_level(user_id, prediction_code):
    # ... existing code ...
    
    if old_level != user.current_level:
        # NEW: Send email
        send_level_update_email(
            user.email,
            user.username,
            old_level,
            user.current_level,
            reason
        )
```

4. **Crear plantillas HTML**
```html
<!-- templates/emails/appointment_notification.html -->
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #75a83a; color: white; padding: 20px; border-radius: 5px; }
        .content { padding: 20px 0; }
        .button { display: inline-block; background: #75a83a; color: white; padding: 10px 20px; 
                  text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Nueva Cita Programada</h2>
        </div>
        <div class="content">
            <p>Hola {{ patient_name }},</p>
            <p>Tu terapeuta ha programado una nueva sesión contigo:</p>
            <p>
                <strong>Fecha y Hora:</strong> {{ datetime_str }}<br>
                {% if appointment.location %}
                <strong>Ubicación:</strong> {{ appointment.location }}<br>
                {% endif %}
                {% if appointment.notes %}
                <strong>Notas:</strong> {{ appointment.notes }}
                {% endif %}
            </p>
            <p>
                <a href="{{ url_for('calendar_patient', _external=True) }}" class="button">
                    Ver en tu Calendario
                </a>
            </p>
        </div>
    </div>
</body>
</html>
```

**Checklist:**
- [ ] Crear plantillas email (3x)
- [ ] Funciones para cada tipo de email
- [ ] Integrar en endpoints (3-4)
- [ ] Configurar SMTP fallback
- [ ] Tests de envío
- [ ] Template testing en desarrollo

---

### 2.3 Tabla Game Catalogada

**Criticidad:** 🟠 ALTA  
**Impacto:** Mejor gestión de juegos  
**Esfuerzo:** 6 horas

#### Cambios:

1. **Crear modelo Game**
```python
# models.py - ADD

class Game(db.Model):
    __tablename__ = 'game'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # 'reflejos-rapidos'
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(255), nullable=True)  # URL o nombre de icon
    difficulty_min = db.Column(db.Integer, default=1)
    difficulty_max = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    metrics = db.relationship('SessionMetrics', backref='game_obj', lazy=True)

# Actualizar SessionMetrics
class SessionMetrics(db.Model):
    # ... existing fields ...
    
    # MODIFY:
    # game_name = db.Column(db.String(100), nullable=False)  # REMOVE THIS
    
    # ADD:
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=True)
    game_name = db.Column(db.String(100), nullable=True)  # KEEP FOR BACKWARDS COMPAT
```

2. **Seed de games**
```python
# app.py - In app context at startup

with app.app_context():
    db.create_all()
    
    # Create default games
    default_games = [
        {'name': 'Reflejos Rápidos', 'slug': 'reflejos-rapidos', 
         'description': 'Reacciona rápido a los estímulos visuales', 
         'difficulty_min': 1, 'difficulty_max': 10},
        {'name': 'Memoria Visual', 'slug': 'memoria-visual',
         'description': 'Memoriza patrones visuales',
         'difficulty_min': 1, 'difficulty_max': 8},
        {'name': 'Seguimiento de Objetos', 'slug': 'seguimiento',
         'description': 'Sigue objetos en movimiento',
         'difficulty_min': 1, 'difficulty_max': 8},
    ]
    
    for game_data in default_games:
        if not Game.query.filter_by(slug=game_data['slug']).first():
            game = Game(**game_data)
            db.session.add(game)
    
    db.session.commit()
    train_model()
```

3. **Actualizar save_game**
```python
@app.route('/api/save_game', methods=['POST'])
@login_required
def save_game():
    data = request.json
    acc = data['accuracy']
    time = data['avg_time']
    game_name = data.get('game_name', 'Reflejos Rápidos')
    pred_code, pred_text = predict_level(acc, time)

    # Get game object
    game = Game.query.filter_by(name=game_name).first()
    if not game:
        # Fallback: create entry with name only
        game_id = None
    else:
        game_id = game.id

    metric = SessionMetrics(
        user_id=current_user.id,
        game_id=game_id,
        game_name=game_name,
        accurracy=acc,
        avg_time=time,
        prediction=pred_code
    )
    db.session.add(metric)
    db.session.commit()
    
    update_player_level(current_user.id, pred_code)
    
    return jsonify({
        'recommendation': pred_text,
        'code': pred_code,
        'new_level': current_user.current_level
    })
```

**Checklist:**
- [ ] Crear modelo Game
- [ ] Migración: SessionMetrics.game_id
- [ ] Seed default games
- [ ] Actualizar save_game
- [ ] Dashboard games filter by is_active
- [ ] Tests

---

## 🟡 FASE 3 & 4: MEDIAS Y FINALES

(Documentación completa disponible pero resumida por brevedad)

### 3.1-3.7 Tareas Medias

| # | Tarea | Esfuerzo | Semana |
|---|-------|----------|--------|
| 3.1 | Real-time Notifications (SocketIO) | 16h | 7-8 |
| 3.2 | Recordatorios de Citas (APScheduler) | 8h | 8 |
| 3.3 | Validación Conflictos Citas | 6h | 9 |
| 4.1 | Auditoría & Logging | 12h | 9-10 |
| 4.2 | API REST v1 Completa | 16h | 10-11 |
| 4.3 | Exportar Reportes (PDF/CSV) | 10h | 11-12 |

---

## 📊 TIMELINE VISUAL

```
SEMANA    TAREA
────────────────────────────────────────────
1-2       🔴 CRÍTICAS
          ├─ Terapeuta-Paciente (20h)
          ├─ CSRF Protection (4h)
          └─ IA Mejorada (12h)
          
3-6       🟠 ALTAS
          ├─ Nivel Adaptativo (8h)
          ├─ Email Notifications (10h)
          └─ Game Catalogada (6h)
          
7-8       🟡 SOCKET.IO (16h)
9         🟡 Recordatorios + Validación (14h)
9-10      🟡 Auditoría (12h)
10-11     🟡 API REST (16h)
11-12     🟡 Reportes (10h)
────────────────────────────────────────────
TOTAL:    ~134 horas = 4-5 dev-weeks (1 dev FT)
```

---

## ✅ CRITERIOS DE ACEPTACIÓN

### Para cada mejora:

- [ ] Código escrito y testeado
- [ ] Tests unitarios (>80% coverage)
- [ ] Documentación actualizada
- [ ] Code review completado
- [ ] Integración con branch master
- [ ] Sin regresiones en funcionalidad existente

### Antes de Producción:

- [ ] Todos los tests pasan
- [ ] Coverage > 80%
- [ ] Security audit pasado
- [ ] Load testing completado
- [ ] Documentación API completa
- [ ] GDPR compliance verificado

---

## 🔧 REQUISITOS DE SETUP

```bash
# Instalar nuevas dependencias
pip install Flask-WTF Flask-SocketIO python-socketio python-engineio
pip install APScheduler
pip install ReportLab  # Para PDF
pip install pandas

# Crear directorio para modelos
mkdir -p ai_models

# Migrar BD
flask db upgrade  # Si usa Alembic
# O simplemente recrear (desarrollo)
```

---

## 📞 NOTAS IMPORTANTES

1. **Backups:** Hacer backup de BD antes de migrar models
2. **Testing:** Cada cambio requiere test coverage > 80%
3. **Comunicación:** Notificar a stakeholders de cambios en UX
4. **Documentación:** Mantener README actualizado

---

**Plan preparado:** 9 de diciembre, 2024  
**Estimado por:** Dev Lead Team  
**Siguiente revisión:** Post-Fase 1
