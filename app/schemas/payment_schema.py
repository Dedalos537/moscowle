from marshmallow import Schema, ValidationError, fields, validate


class PaymentRegisterSchema(Schema):
    patient_id = fields.Int(required=True)
    amount = fields.Float(required=True, validate=validate.Range(min=0.01))
    discount = fields.Float(required=False, load_default=0.0, validate=validate.Range(min=0))
    method = fields.Str(required=True, validate=validate.Length(min=2, max=50))
    reference = fields.Str(required=False, allow_none=True)
    next_due_date = fields.Date(required=False, allow_none=True)


def validate_payment_register(data):
    schema = PaymentRegisterSchema()
    try:
        return schema.load(data), None
    except ValidationError as err:
        return None, err.messages
