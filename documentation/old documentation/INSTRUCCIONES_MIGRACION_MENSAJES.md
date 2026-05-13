# Instrucciones para Migrar la Base de Datos (Modelo Message)

## Contexto
Se ha añadido un nuevo modelo `Message` a `models.py` para implementar el sistema de mensajería entre terapeutas y pacientes.

## Opción 1: Migración con Flask-Migrate (Recomendado)

### Paso 1: Instalar Flask-Migrate (si no está instalado)
```bash
pip install Flask-Migrate
```

### Paso 2: Inicializar las migraciones (solo primera vez)
```bash
flask db init
```

### Paso 3: Crear la migración para el modelo Message
```bash
flask db migrate -m "Add Message model for messaging system"
```

### Paso 4: Aplicar la migración
```bash
flask db upgrade
```

## Opción 2: Recrear la Base de Datos (Rápido pero pierde datos)

**⚠️ ADVERTENCIA: Esto eliminará todos los datos existentes**

### Paso 1: Eliminar la base de datos actual
```bash
rm instance/game.db
```

### Paso 2: Recrear la base de datos con todos los modelos
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database created!')"
```

## Opción 3: Migración Manual SQL (Para preservar datos)

### Paso 1: Entrar a SQLite
```bash
sqlite3 instance/game.db
```

### Paso 2: Ejecutar el SQL para crear la tabla Message
```sql
CREATE TABLE message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    subject VARCHAR(200),
    body TEXT NOT NULL,
    is_read BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    parent_message_id INTEGER,
    FOREIGN KEY (sender_id) REFERENCES user(id),
    FOREIGN KEY (receiver_id) REFERENCES user(id),
    FOREIGN KEY (parent_message_id) REFERENCES message(id)
);

CREATE INDEX idx_message_receiver ON message(receiver_id);
CREATE INDEX idx_message_sender ON message(sender_id);
CREATE INDEX idx_message_read ON message(is_read);
```

### Paso 3: Salir de SQLite
```
.exit
```

## Verificar que la migración funcionó

```bash
python -c "from app import app, db; from models import Message; app.app_context().push(); print('Messages table exists:', db.engine.has_table('message'))"
```

## Probar el sistema de mensajería

1. Iniciar el servidor: `python app.py`
2. Iniciar sesión como terapeuta
3. Ir a **Mensajes** en el sidebar
4. Seleccionar un paciente y enviar un mensaje
5. Iniciar sesión como paciente
6. Verificar que aparece el badge de mensajes sin leer
7. Abrir la conversación y responder

## Rutas relacionadas con mensajería

- `/messages` - Lista de conversaciones (terapeuta) o mensajes con terapeuta (paciente)
- `/messages/<user_id>` - Conversación con un usuario específico (solo terapeuta)
- `/api/messages/send` - API para enviar mensajes (POST)
- `/api/messages/unread-count` - API para obtener el conteo de mensajes sin leer (GET)

## Modelo Message - Campos

```python
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200))
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_message_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]))
```

## Troubleshooting

### Error: "no such table: message"
- Ejecutar Opción 2 o Opción 3 para crear la tabla

### Error: "UNIQUE constraint failed"
- Verificar que no haya datos duplicados antes de la migración

### Error al importar Message en app.py
- Verificar que la línea de importación sea: `from models import ..., Message`
- Verificar que no haya conflicto con `flask_mail.Message` (debe importarse como `MailMessage`)

## Siguiente paso

Después de ejecutar la migración, todas las funcionalidades de mensajería estarán completamente operativas:

✅ Vista de detalle de paciente con historial completo  
✅ Sistema de mensajería básico entre terapeuta y paciente  
✅ Perfil editable para ambos roles  
✅ Notificaciones de mensajes nuevos  
✅ Contadores de mensajes sin leer en sidebar  
