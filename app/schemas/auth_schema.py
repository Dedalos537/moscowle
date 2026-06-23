import re

from marshmallow import Schema, ValidationError, fields, validate


def validate_password_strength(value):
    if len(value) < 8:
        raise ValidationError('La contraseña debe tener al menos 8 caracteres')
    if not re.search(r'[A-Z]', value):
        raise ValidationError('La contraseña debe tener al menos una mayúscula')
    if not re.search(r'[a-z]', value):
        raise ValidationError('La contraseña debe tener al menos una minúscula')
    if not re.search(r'[0-9]', value):
        raise ValidationError('La contraseña debe tener al menos un número')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', value):
        raise ValidationError('La contraseña debe tener al menos un carácter especial')
    return value


class LoginSchema(Schema):
    email = fields.Email(required=True, error_messages={'required': 'Email es requerido'})
    password = fields.Str(required=True, validate=validate.Length(min=1), error_messages={'required': 'Password es requerida'})


class RegisterSchema(Schema):
    email = fields.Email(required=True, error_messages={'required': 'Email es requerido'})
    password = fields.Str(required=True, validate=validate_password_strength, error_messages={'required': 'Password es requerida'})


def validate_login_input(data):
    schema = LoginSchema()
    try:
        return schema.load(data), None
    except ValidationError as err:
        return None, err.messages


def validate_register_input(data):
    schema = RegisterSchema()
    try:
        return schema.load(data), None
    except ValidationError as err:
        return None, err.messages
