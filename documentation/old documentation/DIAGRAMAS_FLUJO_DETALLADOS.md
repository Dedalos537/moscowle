# 📊 DIAGRAMAS DE FLUJO DETALLADOS - MOSCOWLE IA

---

## 1. FLUJO COMPLETO DE AUTENTICACIÓN

```
┌──────────────────────────────────────────────────────────────┐
│                    USUARIO NO LOGUEADO                       │
└──────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴────────┐
                    │                │
            ┌───────▼────────┐  ┌────▼────────┐
            │ LOGIN Básico   │  │ OAuth2      │
            │ (Email+Pass)   │  │ (Google/MS) │
            └────────┬───────┘  └────┬────────┘
                     │               │
        ┌────────────┴───────────────┴───────────────┐
        │                                            │
        ├─ Validar Email Format                      │
        ├─ Query User por email                      │
        ├─ Verificar is_active = True                │
        ├─ Check Password Hash (Bcrypt)              │
        │                                            │
        ├─ SI VÁLIDO:                               │
        │  └─ flask_login.login_user(user)          │
        │     └─ Crea sesión Flask                   │
        │        └─ Set cookies                      │
        │           └─ Redirect /dashboard           │
        │                                            │
        └─ SI INVÁLIDO:                             │
           └─ Flash error message                    │
              └─ Re-render login.html                │
```

---

## 2. FLUJO: CREACIÓN DE PACIENTE

```
┌─────────────────────────────────────────────────┐
│   Terapeuta en /patients/manage                 │
└─────────────────────────────────────────────────┘
                    │
                    ▼
        ┌──────────────────────┐
        │ Click: "Agregar      │
        │ Paciente"            │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │ Ingresa:                      │
        │ • Email (requerido)           │
        │ • Username (opcional)         │
        └──────────┬───────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │ POST /patients/add            │
        │                              │
        │ Validaciones:                │
        │ ├─ Email válido              │
        │ ├─ Email no existe           │
        │ └─ User role = 'terapista'  │
        └──────────┬───────────────────┘
                   │
            ┌──────┴──────┐
            │             │
      ┌─────▼──────┐ ┌───▼──────┐
      │ VALIDACIÓN │ │ VALIDACIÓN
      │ EXITOSA    │ │ FALLIDA
      └─────┬──────┘ └───┬──────┘
            │            │
            │        Flash Error
            │        Redirect
            ▼        /patients/manage
    ┌──────────────────────────┐
    │ Generar Password         │
    │ (12 caracteres seguros)  │
    │ pwd = secrets.choice()   │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ Hash Password            │
    │ hashed = bcrypt.         │
    │   generate_password_hash │
    │         (pwd)            │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ Crear User               │
    │ • email                  │
    │ • password (hashed)      │
    │ • role = 'jugador'       │
    │ • is_active = True       │
    │ • created_at = now()     │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ db.session.add(user)     │
    │ db.session.commit()      │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ Crear Notification       │
    │ (para Terapeuta)         │
    │ msg = "Paciente added... │
    │        Email: ...        │
    │        Pass: ..."        │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ send_welcome_email()     │
    │                          │
    │ IF email configured:     │
    │  ├─ Create MailMessage   │
    │  ├─ body = credentials   │
    │  ├─ mail.send(msg)       │
    │  └─ RETURN True          │
    │                          │
    │ ELSE:                    │
    │  └─ RETURN False         │
    │     (show warning)       │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ Flash Success Message    │
    │                          │
    │ IF email sent:           │
    │  ✅ "Paciente agregado.  │
    │     Email enviado a..."  │
    │                          │
    │ ELSE:                    │
    │  ⚠️  "Paciente agregado  │
    │      pero email falló.   │
    │      Copia manual: ..."  │
    └──────────┬───────────────┘
               │
               ▼
        Redirect /patients/manage
```

---

## 3. FLUJO: GAMIFICACIÓN & PREDICCIÓN IA

```
┌─────────────────────────────────────┐
│  Paciente en game.html              │
│  Jugando "Reflejos Rápidos"         │
└─────────────────────────────────────┘
        │
        ├─ Canvas con objetos que aparecen
        ├─ Paciente hace click cuando ve
        ├─ Se registran tiempos de reacción
        │
        ▼
┌──────────────────────────────────────┐
│ Fin de Sesión de Juego               │
│                                      │
│ Calcula:                             │
│ • accuracy = (hits / total) * 100    │
│ • avg_time = promedio tiempos reacción│
└───────────┬──────────────────────────┘
            │
            ▼
┌──────────────────────────────────────┐
│ POST /api/save_game (JSON)           │
│ {                                    │
│   "accuracy": 85.5,                  │
│   "avg_time": 450.2                  │
│ }                                    │
└───────────┬──────────────────────────┘
            │
            ▼
┌──────────────────────────────────────┐
│ Backend: save_game()                 │
│                                      │
│ 1. Extraer data from JSON            │
│ 2. Validar user autenticado          │
│                                      │
│ 3. predict_level(acc=85.5,           │
│                   time=450.2)        │
│    ├─ Load modelo SVM desde archivo  │
│    ├─ Llamar model.predict()         │
│    │  [[85.5, 450.2]] → [1]         │
│    │                                 │
│    │  Labels:                        │
│    │  0 = Mantener Nivel             │
│    │  1 = Avanzar Nivel              │
│    │  2 = Retroceder                 │
│    │                                 │
│    └─ Retorna: (pred_code=1,        │
│                 pred_text="Avanzar")│
│                                      │
│ 4. Crear SessionMetrics              │
│    {                                 │
│      user_id: current_user.id,       │
│      game_name: "Reflejos Rápidos",  │
│      accuracy: 85.5,                 │
│      avg_time: 450.2,                │
│      prediction: 1,                  │
│      date: now()                     │
│    }                                 │
│                                      │
│ 5. db.session.add(metric)            │
│    db.session.commit()               │
│                                      │
│ 6. RETURN JSON                       │
│    {                                 │
│      "recommendation": "Avanzar",    │
│      "code": 1                       │
│    }                                 │
└───────────┬──────────────────────────┘
            │
            ▼
┌──────────────────────────────────────┐
│ Frontend: Mostrar Resultado          │
│                                      │
│ IF code == 0:                        │
│  ✓ "¡Bien hecho! Mantén tu nivel"   │
│                                      │
│ IF code == 1:                        │
│  ✨ "¡Excelente! Avanza al próximo"  │
│                                      │
│ IF code == 2:                        │
│  📚 "Practica más, te ayudaré"       │
│                                      │
│ Mostrar stats:                       │
│ • Accuracy: 85.5%                    │
│ • Tiempo: 450.2ms                    │
└──────────────────────────────────────┘
```

---

## 4. FLUJO: CREACIÓN DE CITA

```
┌────────────────────────────────────┐
│  Terapeuta en /sessions            │
│  Click: "Nueva Sesión"             │
└────────────────┬───────────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Modal/Form abre con:       │
    │ • Paciente (dropdown)      │
    │ • Fecha                    │
    │ • Hora inicio              │
    │ • Hora fin (opcional)      │
    │ • Título (opcional)        │
    │ • Ubicación                │
    │ • Notas                    │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Terapeuta llena formulario │
    │ y hace click "Guardar"     │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ POST /api/sessions (JSON)      │
    │ {                              │
    │   "patient_id": 5,             │
    │   "start_time": "2024-12-10    │
    │                14:00:00",      │
    │   "end_time": "2024-12-10      │
    │              15:00:00",        │
    │   "title": "Sesión...",        │
    │   "location": "Oficina 3",     │
    │   "notes": "Trabajar en..."    │
    │ }                              │
    └────────────┬───────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
    ┌───▼──────┐    ┌────▼────┐
    │ VALIDAR  │    │ VALIDAR │
    │ patient_ │    │start_   │
    │ id existe│    │time >=  │
    │y es      │    │ now()   │
    │jugador   │    │         │
    └───┬──────┘    └────┬────┘
        │                │
        └────────┬───────┘
                 │
            ┌────▼────┐
            │  TODO   │
            │ VÁLIDO  │
            └────┬────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ Crear Appointment              │
    │ {                              │
    │   therapist_id: 1,             │
    │   patient_id: 5,               │
    │   title: "Sesión...",          │
    │   start_time: datetime,        │
    │   end_time: datetime,          │
    │   status: 'scheduled',         │
    │   location: "Oficina 3",       │
    │   notes: "Trabajar en...",     │
    │   created_at: now()            │
    │ }                              │
    └────────────┬───────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ db.session.add(appt)           │
    │ db.session.commit()            │
    └────────────┬───────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ Crear Notificaciones:          │
    │                                │
    │ 1. Para Terapeuta:            │
    │    "Sesión programada: ...     │
    │     14:00 - 15:00"            │
    │                                │
    │ 2. Para Paciente:             │
    │    "Tienes nueva sesión       │
    │     con Dr. X el 10 dic 14:00"│
    └────────────┬───────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ RETURN JSON Success            │
    │ {                              │
    │   "id": 42,                    │
    │   "title": "Sesión...",        │
    │   "start_time": "2024-...",    │
    │   "patient": {                 │
    │     "id": 5,                   │
    │     "name": "Carlos"           │
    │   }                            │
    │ }                              │
    └────────────┬───────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ Frontend:                      │
    │ ✅ Success message             │
    │ Calendar refrescar             │
    │ Modal cierra                   │
    └────────────────────────────────┘
```

---

## 5. FLUJO: SISTEMA DE MENSAJES

```
┌──────────────────────────────────┐
│  CONVERSACIÓN ENTRE ROLES        │
└──────────────────────────────────┘

CASO 1: Terapeuta Inicia Mensaje
────────────────────────────────

Terapeuta
    │
    ▼
/messages (GET)
    ├─ Query Message donde sender=terapeuta O receiver=terapeuta
    ├─ Agrupar por other_user
    ├─ Contar unread
    └─ Mostrar lista conversaciones
        │
        ▼
Terapeuta click en conversación
    │
    ▼
/messages/<patient_id> (GET)
    ├─ Query Message entre terapeuta-paciente
    ├─ Ordenar por fecha
    ├─ Marcar receiver's messages como read
    └─ Render conversation.html
        │
        ▼
Terapeuta digita mensaje y click enviar
    │
    ▼
POST /api/messages/send (JSON)
{
  "receiver_id": 5,
  "subject": "Progreso",
  "body": "Veo mejora en..."
}
    │
    ├─ Crear Message record
    ├─ db.session.add()
    ├─ db.session.commit()
    │
    ├─ Crear Notification para Paciente
    │  "Nuevo mensaje de Dr. X"
    │
    └─ RETURN JSON success
            │
            ▼
Frontend: Agregar mensaje a chat visualmente


CASO 2: Paciente Responde
──────────────────────────

Paciente
    │
    ▼
/messages (GET)
    ├─ Encuentra Terapeuta único (role='terapista')
    ├─ Query Message con ese terapeuta
    ├─ Marcar como read
    └─ Render patient/messages.html
        │
        ▼
Paciente digita respuesta
    │
    ▼
POST /api/messages/send
{
  "receiver_id": 1,  # Terapeuta
  "subject": "RE: Progreso",
  "body": "Gracias! Me siento..."
}
    │
    ├─ Similar a arriba
    ├─ Notificar Terapeuta
    └─ RETURN JSON
            │
            ▼
Mensajes visible para ambos en /messages
```

---

## 6. FLUJO: DASHBOARD TERAPEUTA (DATOS)

```
┌─────────────────────────────────────┐
│  GET /dashboard (role='terapista')  │
└──────────┬──────────────────────────┘
           │
           ├─ QUERY 1: Active Patients
           │  SELECT COUNT(*) FROM user
           │  WHERE role='jugador' AND is_active=True
           │  → active_patients = 12
           │
           ├─ QUERY 2: Total Sessions
           │  SELECT COUNT(*) FROM appointment
           │  WHERE therapist_id=1
           │  → total_sessions = 47
           │
           ├─ QUERY 3: IA Precision (avg accuracy)
           │  SELECT AVG(accuracy) FROM sessionmetrics
           │  WHERE user_id IN (SELECT id FROM user
           │                    WHERE role='jugador')
           │  → ia_precision = 82.3
           │
           ├─ QUERY 4: Improvement Rate (30 vs 60 days)
           │  last_30 = AVG(accuracy) WHERE date >= now()-30
           │  prev_30 = AVG(accuracy) WHERE date >= now()-60
           │  improvement = ((last_30 - prev_30) / prev_30) * 100
           │  → improvement_rate = 5.8%
           │
           ├─ QUERY 5: Top 5 Pacientes
           │  SELECT * FROM user WHERE role='jugador'
           │  AND is_active=True
           │  FOR EACH patient:
           │    ├─ last_10_metrics = SessionMetrics 
           │    │                   .limit(10)
           │    ├─ avg_accuracy = AVG(accuracy)
           │    ├─ avg_time = AVG(avg_time)
           │    ├─ session_count = COUNT(*)
           │    └─ last_level = metrics[0].prediction
           │
           ├─ QUERY 6: Alerts (low performers)
           │  SELECT username FROM user JOIN sessionmetrics
           │  WHERE accuracy < 60
           │  LIMIT 2
           │  → [{"patient": "Carlos", 
           │      "message": "Rendimiento bajo"}]
           │
           └─ RETURN render_template('therapist/dashboard.html',
                stats={...},
                patients=[...],
                alerts=[...])
                   │
                   ▼
            Dashboard.html renderiza:
            ├─ Card: "12 Pacientes Activos"
            ├─ Card: "47 Sesiones Totales"
            ├─ Card: "82.3% Precisión IA"
            ├─ Card: "↑5.8% Mejora"
            ├─ Table: Top 5 Pacientes
            │  ├─ Nombre, Avatar
            │  ├─ Último Juego
            │  ├─ Nivel, Accuracy, Tiempo
            │  └─ Sessions Count
            └─ Alert Box: Bajo Rendimiento
```

---

## 7. FLUJO: DASHBOARD PACIENTE (DATOS)

```
┌─────────────────────────────────────┐
│  GET /dashboard (role='jugador')    │
└──────────┬──────────────────────────┘
           │
           ├─ QUERY 1: Total Sessions
           │  SELECT COUNT(*) FROM sessionmetrics
           │  WHERE user_id=current_user.id
           │  → total_sessions = 23
           │
           ├─ QUERY 2: Avg Accuracy
           │  SELECT AVG(accuracy) FROM sessionmetrics
           │  WHERE user_id=current_user.id
           │  → avg_accuracy = 78.5
           │
           ├─ QUERY 3: Avg Time
           │  SELECT AVG(avg_time) FROM sessionmetrics
           │  WHERE user_id=current_user.id
           │  → avg_time = 520.3 ms
           │
           ├─ QUERY 4: Last Played Date
           │  SELECT MAX(date) FROM sessionmetrics
           │  WHERE user_id=current_user.id
           │  → last_played = "9 de diciembre, 2024"
           │
           ├─ QUERY 5: Recent Sessions (last 5)
           │  SELECT * FROM sessionmetrics
           │  WHERE user_id=current_user.id
           │  ORDER BY date DESC
           │  LIMIT 5
           │  → Mostrar en tabla con timestamps
           │
           ├─ QUERY 6: Game Stats
           │  SELECT game_name, COUNT(*), AVG(accuracy), AVG(avg_time)
           │  FROM sessionmetrics
           │  WHERE user_id=current_user.id
           │  GROUP BY game_name
           │  → [{"Reflejos": 23 plays, 78.5% acc, 520ms}]
           │
           ├─ QUERY 7: Upcoming Appointments
           │  SELECT * FROM appointment
           │  WHERE patient_id=current_user.id
           │  AND start_time >= now()
           │  AND status='scheduled'
           │  ORDER BY start_time
           │  LIMIT 3
           │  → [{"Sesión con Dr. X", "10 dic 14:00"}]
           │
           └─ RETURN render_template('patient/dashboard.html',
                player_stats={...})
                   │
                   ▼
            Dashboard.html renderiza:
            ├─ Card: "23 Sesiones Totales"
            ├─ Card: "78.5% Precision"
            ├─ Card: "520.3ms Promedio Tiempo"
            ├─ Card: "Última vez: 9 dic, 2024"
            ├─ Table: Últimas 5 Sesiones
            │  ├─ Fecha, Hora
            │  ├─ Juego
            │  ├─ Accuracy, Tiempo
            │  └─ Recomendación IA
            ├─ Chart: Progreso por Juego
            └─ List: Próximas Citas (3)
```

---

## 8. FLUJO DE SEGURIDAD: LOGIN

```
User POST /login
{
  "email": "user@example.com",
  "password": "secreto123"
}
    │
    ▼
┌─────────────────────────────┐
│ Backend: login()            │
│                             │
│ 1. Extraer email, password  │
│    email = email.strip()    │
│           .lower()          │
│                             │
│ 2. Validar formato email    │
│    try:                     │
│      valid = validate_email │
│                (email)      │
│    except:                  │
│      Flash error, return    │
│                             │
│ 3. Query User por email     │
│    user = User.query       │
│      .filter_by(email)     │
│      .first()              │
│                             │
│ 4. Verificar:              │
│    if user AND            │
│       user.is_active AND  │
│       bcrypt.check_       │
│       password_hash()     │
│                             │
│    YES:                     │
│    ├─ login_user(user)      │
│    │  └─ Set session cookie │
│    └─ Redirect /dashboard   │
│                             │
│    NO:                      │
│    ├─ Flash error msg       │
│    └─ Render login.html     │
└─────────────────────────────┘
```

---

## 9. FLUJO DE AUDITORÍA (PROPUESTO)

```
Cualquier acción importante:
    │
    ├─ create_patient()
    ├─ delete_patient()
    ├─ update_appointment()
    ├─ create_appointment()
    └─ send_message()
    │
    ▼
┌──────────────────────────┐
│ @audit_action            │
│ decorator applied        │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Registrar AuditLog:          │
│ {                            │
│   user_id: current_user.id,  │
│   action: 'create_patient',  │
│   entity_type: 'User',       │
│   entity_id: 5,              │
│   old_value: NULL,           │
│   new_value: {               │
│     "email": "...",          │
│     "username": "..."        │
│   },                         │
│   timestamp: now()           │
│ }                            │
└──────────┬───────────────────┘
           │
           ▼
Almacenar para:
├─ Compliance GDPR
├─ Debugging
├─ Investigación de problemas
└─ Reportes de auditoría
```

---

## 10. FLUJO: ACTUALIZACIÓN DE NIVEL ADAPTATIVO (PROPUESTO)

```
Paciente guarda sesión de juego
    │
    ├─ accuracy: 88%
    └─ avg_time: 420ms
    │
    ▼
IA predice: 1 (Avanzar Nivel)
    │
    ▼
┌──────────────────────────────────┐
│ NEW: update_player_level()       │
│                                  │
│ IF prediction == 1:              │
│   user.current_level += 1        │
│   MAX: 10                        │
│                                  │
│ ELIF prediction == 2:            │
│   user.current_level -= 1        │
│   MIN: 1                         │
│                                  │
│ ELSE: (0)                        │
│   user.current_level unchanged   │
│                                  │
│ user.last_level_update = now()   │
│ db.session.commit()              │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Siguiente sesión de juego:       │
│                                  │
│ game.difficulty = user.          │
│                   current_level  │
│                                  │
│ ├─ Level 1: Objetos lentos       │
│ ├─ Level 5: Objetos normales     │
│ └─ Level 10: Objetos rápidos     │
│                                  │
│ ✅ VERDADERA ADAPTACIÓN          │
└──────────────────────────────────┘
```

---

**Diagrama generado:** 9 de diciembre, 2024
