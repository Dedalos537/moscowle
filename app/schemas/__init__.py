from marshmallow import Schema, fields, validate, ValidationError

class CreateUserSchema(Schema):
    email = fields.Email(required=True)
    username = fields.Str(required=False, allow_none=True, validate=validate.Length(min=1))
    role = fields.Str(required=True, validate=validate.OneOf(['terapista', 'jugador', 'terapeuta']))

class UpdateUserSchema(Schema):
    id = fields.Int(required=True)
    username = fields.Str(required=False, allow_none=True)
    role = fields.Str(required=False, allow_none=True, validate=validate.OneOf(['terapista', 'jugador', 'admin', 'terapeuta']))
    is_active = fields.Bool(required=False)

class AssignTherapistSchema(Schema):
    patient_id = fields.Int(required=True)
    therapist_id = fields.Int(required=True)

class SendMessageSchema(Schema):
    receiver_id = fields.Int(required=True)
    subject = fields.Str(required=False, allow_none=True)
    body = fields.Str(required=True, validate=validate.Length(min=1))
