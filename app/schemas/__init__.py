from marshmallow import INCLUDE, Schema, ValidationError, fields, validate


class CreateUserSchema(Schema):
    email = fields.Email(required=True)
    username = fields.Str(required=False, allow_none=True, validate=validate.Length(min=1))
    role = fields.Str(
        required=True, validate=validate.OneOf(['terapista', 'jugador', 'terapeuta', 'supervisor', 'admin'])
    )


class UpdateUserSchema(Schema):
    id = fields.Int(required=True)
    username = fields.Str(required=False, allow_none=True)
    role = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.OneOf(['terapista', 'jugador', 'admin', 'terapeuta', 'supervisor']),
    )
    is_active = fields.Bool(required=False)

    sede_id = fields.Raw(required=False, allow_none=True)
    sede_ids = fields.Raw(required=False, allow_none=True)

    modality = fields.Raw(required=False)
    payment_plan = fields.Str(required=False)
    payment_amount = fields.Raw(required=False)
    sessions_attended = fields.Raw(required=False)
    sessions_total = fields.Int(required=False)

    salary_base = fields.Raw(required=False)
    contract_hours = fields.Raw(required=False)
    work_start_time = fields.Str(required=False)
    work_end_time = fields.Str(required=False)
    work_days = fields.Str(required=False)

    class Meta:
        unknown = INCLUDE


class AssignTherapistSchema(Schema):
    patient_id = fields.Int(required=True)
    therapist_id = fields.Int(required=False, allow_none=True)
    therapist_ids = fields.List(fields.Int(), required=False, allow_none=True)


class SendMessageSchema(Schema):
    receiver_id = fields.Int(required=True)
    subject = fields.Str(required=False, allow_none=True)
    body = fields.Str(required=True, validate=validate.Length(min=1))
