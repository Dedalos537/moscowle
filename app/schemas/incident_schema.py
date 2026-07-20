from marshmallow import INCLUDE, Schema, ValidationError, fields, validate

CATEGORIAS_VALIDAS = {'HARDWARE', 'SOFTWARE', 'RED', 'ACCESOS', 'OPERACIONES'}
ESTADOS_VALIDOS = {'NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR', 'RESUELTO', 'CERRADO'}
EVIDENCIAS_VALIDAS = {'SYSTEM_ALERT', 'EVALUATION', 'USER_REPORT', 'MONITORING', 'MANUAL'}
PRIORIDADES_VALIDAS = {1, 2, 3, 4}


class IncidentCreateSchema(Schema):
    titulo = fields.Str(required=True, validate=validate.Length(min=5, max=200))
    descripcion = fields.Str(required=True, validate=validate.Length(min=10))
    categoria = fields.Str(required=True, validate=validate.OneOf(CATEGORIAS_VALIDAS))
    subcategoria = fields.Str(load_default=None, validate=validate.Length(max=100))
    prioridad = fields.Int(load_default=3, validate=validate.OneOf(PRIORIDADES_VALIDAS))
    impacto = fields.Int(load_default=None)
    urgencia = fields.Int(load_default=None)
    appointment_id = fields.Int(load_default=None)
    evidencia_tipo = fields.Str(
        load_default='MANUAL',
        validate=validate.OneOf(EVIDENCIAS_VALIDAS),
    )
    evidencia_original = fields.Str(load_default='')

    class Meta:
        unknown = INCLUDE


class IncidentStatusSchema(Schema):
    estado = fields.Str(required=True, validate=validate.OneOf(ESTADOS_VALIDOS))


class IncidentAssignSchema(Schema):
    responsable_id = fields.Int(required=True)


class IncidentCommentSchema(Schema):
    contenido = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    es_interno = fields.Bool(load_default=False)


def validate_incident_create(data):
    schema = IncidentCreateSchema()
    try:
        return schema.load(data), None
    except ValidationError as err:
        return None, err.messages


def validate_incident_status(data):
    schema = IncidentStatusSchema()
    try:
        return schema.load(data), None
    except ValidationError as err:
        return None, err.messages


def validate_incident_assign(data):
    schema = IncidentAssignSchema()
    try:
        return schema.load(data), None
    except ValidationError as err:
        return None, err.messages


def validate_incident_comment(data):
    schema = IncidentCommentSchema()
    try:
        return schema.load(data), None
    except ValidationError as err:
        return None, err.messages
