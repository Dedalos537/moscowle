from marshmallow import Schema, fields, validate, ValidationError


class LoginSchema(Schema):
    email = fields.Email(required=True, error_messages={'required': 'Email es requerido'})
    password = fields.Str(required=True, validate=validate.Length(min=6), error_messages={'required': 'Password es requerida'})


def validate_login_input(data):
    schema = LoginSchema()
    try:
        return schema.load(data), None
    except ValidationError as err:
        return None, err.messages
