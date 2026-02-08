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
    
    # Flexible fields for plan updates (Patient)
    modality = fields.Int(required=False)
    payment_plan = fields.Str(required=False)
    payment_amount = fields.Raw(required=False) # Accept float or string
    sessions_attended = fields.Int(required=False)
    sessions_total = fields.Int(required=False)
    
    # Flexible fields for plan updates (Therapist)
    salary_base = fields.Raw(required=False)
    contract_hours = fields.Int(required=False)

    class Meta:
        unknown = 'INCLUDE' # Allow extra fields to pass through


class AssignTherapistSchema(Schema):
    patient_id = fields.Int(required=True)
    therapist_id = fields.Int(required=False, allow_none=True)
    therapist_ids = fields.List(fields.Int(), required=False, allow_none=True)

class SendMessageSchema(Schema):
    receiver_id = fields.Int(required=True)
    subject = fields.Str(required=False, allow_none=True)
    body = fields.Str(required=True, validate=validate.Length(min=1))
