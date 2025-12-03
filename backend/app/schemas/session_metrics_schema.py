from marshmallow import Schema, fields, validate, ValidationError


class SessionMetricsSchema(Schema):
    """Schema for serializing SessionMetrics model."""
    
    # Read-only fields
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    
    # Required fields
    patient_id = fields.Int(required=True, validate=validate.Range(min=1))
    game_name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    
    # Performance metrics
    accuracy_rate = fields.Float(
        required=True, 
        validate=validate.Range(min=0, max=100),
        description="Accuracy percentage (0-100)"
    )
    average_time = fields.Float(
        required=True, 
        validate=validate.Range(min=0),
        description="Average time in seconds"
    )
    failed_attempts = fields.Int(
        required=True, 
        validate=validate.Range(min=0),
        description="Number of failed attempts"
    )
    
    # Level information
    previous_level = fields.Int(
        required=True, 
        validate=validate.Range(min=1, max=3),
        description="Current level (1-3)"
    )
    predicted_next_level = fields.Int(
        required=False, 
        allow_none=True,
        validate=validate.Range(min=0, max=3),
        description="Next predicted level (0, 1, 2, 3, or null)"
    )
    
    # Machine Learning
    cluster_id = fields.Int(
        required=False, 
        allow_none=True,
        validate=validate.Range(min=0),
        description="K-Means cluster ID assigned by ML algorithm"
    )


class CreateSessionMetricsSchema(Schema):
    """Schema for creating new SessionMetrics records (POST requests)."""
    
    patient_id = fields.Int(required=True, validate=validate.Range(min=1))
    game_name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    accuracy_rate = fields.Float(required=True, validate=validate.Range(min=0, max=100))
    average_time = fields.Float(required=True, validate=validate.Range(min=0))
    failed_attempts = fields.Int(required=True, validate=validate.Range(min=0))
    previous_level = fields.Int(required=True, validate=validate.Range(min=1, max=3))
    predicted_next_level = fields.Int(required=False, allow_none=True, validate=validate.Range(min=0, max=3))
    cluster_id = fields.Int(required=False, allow_none=True, validate=validate.Range(min=0))


class UpdateSessionMetricsSchema(Schema):
    """Schema for updating existing SessionMetrics records (PUT/PATCH requests)."""
    
    game_name = fields.Str(required=False, validate=validate.Length(min=1, max=255))
    accuracy_rate = fields.Float(required=False, validate=validate.Range(min=0, max=100))
    average_time = fields.Float(required=False, validate=validate.Range(min=0))
    failed_attempts = fields.Int(required=False, validate=validate.Range(min=0))
    previous_level = fields.Int(required=False, validate=validate.Range(min=1, max=3))
    predicted_next_level = fields.Int(required=False, allow_none=True, validate=validate.Range(min=0, max=3))
    cluster_id = fields.Int(required=False, allow_none=True, validate=validate.Range(min=0))
