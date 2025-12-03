"""
AI Endpoints Schemas
Marshmallow schemas for AI recommendation endpoint validation

Author: AI Assistant
Date: December 3, 2025
"""

from marshmallow import Schema, fields, validate, validates, ValidationError


class RecommendLevelRequestSchema(Schema):
    """
    Schema for POST /api/ai/recommend_level request validation
    
    Validates student metrics and optional session data
    """
    
    patient_id = fields.Int(
        required=True,
        validate=validate.Range(min=1),
        error_messages={'required': 'patient_id is required', 'invalid': 'patient_id must be an integer'}
    )
    
    game_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        error_messages={'required': 'game_name is required'}
    )
    
    accuracy_rate = fields.Float(
        required=True,
        validate=validate.Range(min=0, max=100),
        error_messages={'required': 'accuracy_rate is required', 'invalid': 'accuracy_rate must be a number between 0-100'}
    )
    
    average_time = fields.Float(
        required=True,
        validate=validate.Range(min=0),
        error_messages={'required': 'average_time is required', 'invalid': 'average_time must be non-negative'}
    )
    
    failed_attempts = fields.Int(
        required=True,
        validate=validate.Range(min=0),
        error_messages={'required': 'failed_attempts is required', 'invalid': 'failed_attempts must be non-negative'}
    )
    
    previous_level = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=3),
        error_messages={'required': 'previous_level is required', 'invalid': 'previous_level must be between 1-3'}
    )
    
    # Optional fields
    predicted_next_level = fields.Int(
        required=False,
        allow_none=True,
        validate=validate.Range(min=0, max=2),
        error_messages={'invalid': 'predicted_next_level must be 0, 1, or 2'}
    )
    
    cluster_id = fields.Int(
        required=False,
        allow_none=True,
        validate=validate.Range(min=0),
        error_messages={'invalid': 'cluster_id must be non-negative'}
    )
    
    @validates('accuracy_rate')
    def validate_accuracy(self, value):
        """Additional validation for accuracy rate"""
        if value < 0 or value > 100:
            raise ValidationError('Accuracy rate must be between 0 and 100')


class RecommendLevelResponseSchema(Schema):
    """
    Schema for POST /api/ai/recommend_level response
    
    Contains prediction result with confidence and message
    """
    
    recommended_level = fields.Int(
        description='Predicted next level (0=Mantener, 1=Avanzar, 2=Retroceder)'
    )
    
    message = fields.Str(
        description='Human-readable recommendation message'
    )
    
    confidence = fields.Float(
        description='Confidence score (0-1) for the prediction'
    )
    
    probabilities = fields.Dict(
        description='Full probability distribution for all classes',
        keys=fields.Str(),
        values=fields.Float()
    )
    
    session_metric_id = fields.Int(
        description='ID of saved SessionMetrics record in database'
    )
    
    success = fields.Bool(
        description='Whether the operation was successful'
    )


class AIStatusSchema(Schema):
    """
    Schema for GET /api/ai/status response
    
    Returns model and service status information
    """
    
    model_loaded = fields.Bool(
        description='Whether SVM model is loaded'
    )
    
    model_size_mb = fields.Float(
        description='Size of model in MB'
    )
    
    accuracy = fields.Float(
        description='Model training accuracy'
    )
    
    support_vectors = fields.Int(
        description='Number of support vectors'
    )
    
    status = fields.Str(
        description='Overall service status'
    )
    
    message = fields.Str(
        description='Additional status message'
    )
