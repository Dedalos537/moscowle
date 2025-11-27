from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    role_id = fields.Int()
    created_at = fields.DateTime(dump_only=True)


class CreateUserSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    role_id = fields.Int(required=False)
    role = fields.Str(required=False)
