# Diseño de Base de Datos Integral
## Centro de Terapias Juan Pablo II

### Análisis del Flujo de Datos

#### **Página Web Principal (Landing Page)**
- **Función**: Marketing, información de servicios, contacto y login
- **Usuarios**: Visitantes anónimos, padres de familia, pacientes potenciales
- **Datos requeridos**: Información de contacto, solicitudes de citas, leads

#### **Dashboard Administrativo**
- **Función**: Gestión completa del centro de terapias
- **Usuarios**: Administradores, terapeutas, asistentes
- **Módulos existentes**:
  - Dashboard Home (estadísticas generales)
  - Gestión de Usuarios (terapeutas, asistentes, admins)
  - Módulo de Horarios/Citas
  - Módulo Financiero/ERP
  - Módulo de Mensajería
  - Módulo de Reportes
  - Módulo de Asistencia
  - Módulo de Inventario
  - Módulo ITIL (gestión de incidencias)
  - Módulo de Juegos

---

## **Diseño de Base de Datos**

### **1. USUARIOS Y AUTENTICACIÓN**

```sql
-- Tabla de roles del sistema
CREATE TABLE roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL, -- 'admin', 'therapist', 'assistant', 'patient', 'parent'
    description TEXT,
    permissions JSON, -- Permisos específicos por módulo
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla principal de usuarios
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT NOT NULL,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP NULL,
    last_login TIMESTAMP NULL,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Perfiles de usuarios del sistema (staff)
CREATE TABLE user_profiles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    specialty VARCHAR(100), -- Para terapeutas
    license_number VARCHAR(100), -- Número de cédula profesional
    hire_date DATE,
    birth_date DATE,
    address TEXT,
    emergency_contact_name VARCHAR(200),
    emergency_contact_phone VARCHAR(20),
    photo_url VARCHAR(500),
    bio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### **2. PACIENTES Y FAMILIAS**

```sql
-- Tabla de pacientes
CREATE TABLE patients (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_code VARCHAR(50) UNIQUE NOT NULL, -- Código único del paciente
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birth_date DATE NOT NULL,
    gender ENUM('M', 'F', 'Other') NOT NULL,
    identification_type VARCHAR(20), -- 'DNI', 'Passport', etc.
    identification_number VARCHAR(50),
    address TEXT,
    medical_history TEXT,
    allergies TEXT,
    medications TEXT,
    emergency_medical_info TEXT,
    photo_url VARCHAR(500),
    status ENUM('active', 'inactive', 'discharged') DEFAULT 'active',
    admission_date DATE NOT NULL,
    discharge_date DATE NULL,
    referring_doctor VARCHAR(200),
    insurance_provider VARCHAR(200),
    insurance_policy_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabla de responsables/familiares
CREATE TABLE patient_guardians (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    relationship VARCHAR(50) NOT NULL, -- 'Padre', 'Madre', 'Tutor', etc.
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    is_primary_contact BOOLEAN DEFAULT FALSE,
    can_authorize_treatment BOOLEAN DEFAULT FALSE,
    address TEXT,
    occupation VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);
```

### **3. SERVICIOS Y TERAPIAS**

```sql
-- Catálogo de servicios/terapias
CREATE TABLE therapy_services (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL, -- 'Terapias', 'Terapias Integrales', 'Apoyo Virtual', 'Material Concreto'
    description TEXT,
    duration_minutes INT DEFAULT 60,
    price DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    requires_materials BOOLEAN DEFAULT FALSE,
    max_participants INT DEFAULT 1, -- Para terapias grupales
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Especialidades de terapeutas
CREATE TABLE specialties (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL, -- 'Lenguaje', 'Ocupacional', 'Física', 'Psicológica'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relación terapeutas-especialidades (muchos a muchos)
CREATE TABLE therapist_specialties (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    specialty_id INT NOT NULL,
    certification_date DATE,
    certification_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (specialty_id) REFERENCES specialties(id),
    UNIQUE KEY unique_therapist_specialty (user_id, specialty_id)
);

-- Relación servicios-especialidades
CREATE TABLE service_specialties (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    specialty_id INT NOT NULL,
    FOREIGN KEY (service_id) REFERENCES therapy_services(id) ON DELETE CASCADE,
    FOREIGN KEY (specialty_id) REFERENCES specialties(id),
    UNIQUE KEY unique_service_specialty (service_id, specialty_id)
);
```

### **4. CITAS Y HORARIOS**

```sql
-- Horarios disponibles de terapeutas
CREATE TABLE therapist_schedules (
    id INT PRIMARY KEY AUTO_INCREMENT,
    therapist_id INT NOT NULL,
    day_of_week TINYINT NOT NULL, -- 1=Lunes, 7=Domingo
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (therapist_id) REFERENCES users(id),
    INDEX idx_therapist_day (therapist_id, day_of_week)
);

-- Salas/consultorios
CREATE TABLE rooms (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    capacity INT DEFAULT 1,
    equipment TEXT, -- Descripción del equipo disponible
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Citas programadas
CREATE TABLE appointments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    therapist_id INT NOT NULL,
    service_id INT NOT NULL,
    room_id INT,
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status ENUM('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show') DEFAULT 'scheduled',
    notes TEXT,
    cancellation_reason TEXT,
    created_by INT NOT NULL, -- Usuario que creó la cita
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (therapist_id) REFERENCES users(id),
    FOREIGN KEY (service_id) REFERENCES therapy_services(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_appointment_date (appointment_date),
    INDEX idx_therapist_date (therapist_id, appointment_date)
);

-- Sesiones de terapia (registro de lo realizado)
CREATE TABLE therapy_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    appointment_id INT UNIQUE NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    objectives TEXT,
    activities_performed TEXT,
    patient_response TEXT,
    therapist_notes TEXT,
    homework_assigned TEXT,
    next_session_goals TEXT,
    materials_used TEXT,
    session_rating TINYINT, -- 1-5 rating
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE
);
```

### **5. FINANZAS Y FACTURACIÓN**

```sql
-- Planes de tratamiento
CREATE TABLE treatment_plans (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    service_id INT NOT NULL,
    therapist_id INT NOT NULL,
    total_sessions INT NOT NULL,
    sessions_completed INT DEFAULT 0,
    price_per_session DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    discount_percentage DECIMAL(5,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    final_amount DECIMAL(10,2) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    status ENUM('active', 'completed', 'cancelled', 'suspended') DEFAULT 'active',
    notes TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (service_id) REFERENCES therapy_services(id),
    FOREIGN KEY (therapist_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Facturas
CREATE TABLE invoices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    patient_id INT NOT NULL,
    treatment_plan_id INT,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    status ENUM('draft', 'sent', 'paid', 'overdue', 'cancelled') DEFAULT 'draft',
    payment_terms VARCHAR(100),
    notes TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (treatment_plan_id) REFERENCES treatment_plans(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Detalles de factura
CREATE TABLE invoice_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_id INT NOT NULL,
    service_id INT NOT NULL,
    appointment_id INT, -- Si es por sesión específica
    description TEXT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES therapy_services(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);

-- Pagos
CREATE TABLE payments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_id INT NOT NULL,
    payment_date DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method ENUM('cash', 'card', 'transfer', 'check', 'other') NOT NULL,
    reference_number VARCHAR(100),
    notes TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Gastos del centro
CREATE TABLE expenses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    category VARCHAR(100) NOT NULL, -- 'Materiales', 'Equipos', 'Servicios', 'Salarios', etc.
    description TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    expense_date DATE NOT NULL,
    payment_method ENUM('cash', 'card', 'transfer', 'check') NOT NULL,
    vendor VARCHAR(200),
    receipt_number VARCHAR(100),
    is_recurring BOOLEAN DEFAULT FALSE,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

### **6. INVENTARIO Y MATERIALES**

```sql
-- Categorías de materiales
CREATE TABLE material_categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventario de materiales
CREATE TABLE inventory_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    category_id INT NOT NULL,
    sku VARCHAR(100) UNIQUE,
    description TEXT,
    current_stock INT NOT NULL DEFAULT 0,
    minimum_stock INT DEFAULT 0,
    unit_cost DECIMAL(10,2),
    location VARCHAR(100), -- Dónde se guarda
    supplier VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES material_categories(id)
);

-- Movimientos de inventario
CREATE TABLE inventory_movements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    item_id INT NOT NULL,
    movement_type ENUM('in', 'out', 'adjustment') NOT NULL,
    quantity INT NOT NULL,
    reason VARCHAR(200) NOT NULL,
    reference_id INT, -- ID de la cita o compra relacionada
    notes TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES inventory_items(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

### **7. COMUNICACIÓN Y MENSAJERÍA**

```sql
-- Conversaciones/hilos de mensajes
CREATE TABLE conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200),
    type ENUM('user_to_user', 'group', 'patient_support') DEFAULT 'user_to_user',
    patient_id INT, -- Si es relacionado con un paciente específico
    is_archived BOOLEAN DEFAULT FALSE,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Participantes en conversaciones
CREATE TABLE conversation_participants (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    user_id INT,
    guardian_id INT, -- Para padres/responsables
    role ENUM('admin', 'participant') DEFAULT 'participant',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    left_at TIMESTAMP NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (guardian_id) REFERENCES patient_guardians(id)
);

-- Mensajes
CREATE TABLE messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    sender_user_id INT,
    sender_guardian_id INT,
    message_text TEXT NOT NULL,
    message_type ENUM('text', 'file', 'image', 'system') DEFAULT 'text',
    file_url VARCHAR(500),
    is_read BOOLEAN DEFAULT FALSE,
    is_system_message BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_user_id) REFERENCES users(id),
    FOREIGN KEY (sender_guardian_id) REFERENCES patient_guardians(id)
);

-- Notificaciones
CREATE TABLE notifications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    guardian_id INT,
    type VARCHAR(50) NOT NULL, -- 'appointment_reminder', 'payment_due', 'message', etc.
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSON, -- Datos adicionales específicos del tipo
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (guardian_id) REFERENCES patient_guardians(id)
);
```

### **8. REPORTES Y ESTADÍSTICAS**

```sql
-- Reportes programados
CREATE TABLE scheduled_reports (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(100) NOT NULL, -- 'financial', 'attendance', 'progress', etc.
    parameters JSON, -- Configuración del reporte
    frequency ENUM('daily', 'weekly', 'monthly', 'quarterly') NOT NULL,
    recipients JSON, -- Lista de emails o user_ids
    is_active BOOLEAN DEFAULT TRUE,
    last_run TIMESTAMP NULL,
    next_run TIMESTAMP NOT NULL,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Log de actividades del sistema
CREATE TABLE activity_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50), -- 'patient', 'appointment', 'invoice', etc.
    entity_id INT,
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### **9. SISTEMA DE TICKETS/INCIDENCIAS (ITIL)**

```sql
-- Categorías de incidencias
CREATE TABLE ticket_categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    sla_hours INT DEFAULT 24, -- Tiempo de respuesta en horas
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tickets/Incidencias
CREATE TABLE tickets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category_id INT NOT NULL,
    priority ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    status ENUM('open', 'in_progress', 'pending', 'resolved', 'closed') DEFAULT 'open',
    assigned_to INT,
    created_by INT NOT NULL,
    resolved_at TIMESTAMP NULL,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES ticket_categories(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

### **10. CONTACTOS Y LEADS (DESDE LA WEB)**

```sql
-- Formularios de contacto desde la web
CREATE TABLE contact_inquiries (
    id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    message TEXT,
    service_interest VARCHAR(200), -- Servicio de interés
    status ENUM('new', 'contacted', 'scheduled', 'converted', 'closed') DEFAULT 'new',
    assigned_to INT,
    follow_up_date DATE,
    notes TEXT,
    source VARCHAR(100) DEFAULT 'website', -- 'website', 'referral', 'social_media', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users(id)
);

-- Seguimiento de leads
CREATE TABLE lead_activities (
    id INT PRIMARY KEY AUTO_INCREMENT,
    inquiry_id INT NOT NULL,
    activity_type ENUM('call', 'email', 'meeting', 'note') NOT NULL,
    description TEXT NOT NULL,
    scheduled_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inquiry_id) REFERENCES contact_inquiries(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

---

## **Flujo de Integración Entre Sistemas**

### **1. Página Web → Dashboard**
- **Formularios de contacto** → `contact_inquiries`
- **Solicitudes de cita** → `contact_inquiries` con tipo especial
- **Login de padres** → Sistema de autenticación unificado

### **2. Dashboard → Página Web**
- **Información de servicios** actualizada desde `therapy_services`
- **Horarios disponibles** calculados desde `therapist_schedules` y `appointments`
- **Testimonios** desde datos reales de pacientes (con permisos)

### **3. Datos Compartidos**
- **Catálogo de servicios**: Sincronización automática
- **Información de contacto**: Actualización en tiempo real
- **Estadísticas públicas**: KPIs generados desde datos reales

---

## **Consideraciones Técnicas**

### **Seguridad (ISO 25010)**
- Encriptación de contraseñas con bcrypt
- Tokens JWT para autenticación
- Logs de auditoría completos
- Validación de entrada en todas las capas
- Backup automático diario

### **Performance**
- Índices optimizados para consultas frecuentes
- Cacheing de datos estáticos
- Paginación en listados grandes
- Compresión de imágenes

### **Mantenibilidad**
- Estructura modular
- Documentación automática de API
- Versionado de esquema de BD
- Migraciones controladas

### **Escalabilidad**
- Diseño normalizado con desnormalización selectiva
- Particionado por fechas en tablas grandes
- Archivado automático de datos antiguos

---

## **Próximos Pasos de Implementación**

1. **Crear API REST** para conectar ambos sistemas
2. **Implementar autenticación JWT** unificada
3. **Desarrollar formularios de contacto** dinámicos
4. **Crear dashboard de leads** en el sistema administrativo
5. **Implementar notificaciones** en tiempo real
6. **Desarrollar sistema de reportes** automatizados
7. **Integrar pasarela de pagos** online
8. **Crear portal de padres** con acceso limitado

¿Te gustaría que proceda con la implementación de algún módulo específico?