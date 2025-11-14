"""
Rutas de mensajería básicas
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional

from app.models import (
    ContactInquiryCreate, ContactInquiryResponse, 
    MessageCreate, MessageResponse,
    SuccessResponse
)
from app.services import InquiryService, MessageService
from app.api.auth import get_current_user
from app.models import UserResponse
from app.core.logging import get_logger

logger = get_logger("messaging_routes")

router = APIRouter(prefix="/messaging", tags=["Messaging"])


def get_client_ip(request: Request) -> str:
    """Obtener IP del cliente"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host


# Rutas públicas
@router.post("/inquiries", response_model=ContactInquiryResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_inquiry(
    inquiry_data: ContactInquiryCreate,
    request: Request
):
    """Crear nueva consulta de contacto (público)"""
    try:
        ip_address = get_client_ip(request)
        inquiry = InquiryService.create_inquiry(inquiry_data, ip_address)
        
        if inquiry is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating inquiry"
            )
        
        logger.info(f"New inquiry created: {inquiry.inquiry_code}")
        return inquiry
        
    except Exception as e:
        logger.error(f"Error creating inquiry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing inquiry"
        )


@router.get("/inquiries/by-code/{inquiry_code}", response_model=ContactInquiryResponse)
async def get_inquiry_by_code(inquiry_code: str):
    """Obtener consulta por código (público)"""
    try:
        inquiry = InquiryService.get_inquiry_by_code(inquiry_code)
        
        if inquiry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inquiry not found"
            )
        
        return inquiry
        
    except Exception as e:
        logger.error(f"Error getting inquiry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving inquiry"
        )


# Rutas privadas (requieren autenticación)
@router.get("/inquiries/{inquiry_id}", response_model=ContactInquiryResponse)
async def get_inquiry_by_id(
    inquiry_id: int,
    current_user: UserResponse = Depends(get_current_user)
):
    """Obtener consulta por ID (autenticado)"""
    try:
        inquiry = InquiryService.get_inquiry_by_id(inquiry_id)
        
        if inquiry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inquiry not found"
            )
        
        return inquiry
        
    except Exception as e:
        logger.error(f"Error getting inquiry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving inquiry"
        )


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_data: MessageCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Crear nuevo mensaje (autenticado)"""
    try:
        # Configurar sender según el usuario actual
        if current_user.role == "admin":
            message_data.sender_type = "admin"
        elif current_user.role == "therapist":
            message_data.sender_type = "therapist"
        
        message_data.sender_id = current_user.id
        
        message = MessageService.create_message(message_data)
        
        if message is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating message"
            )
        
        logger.info(f"New message created by {current_user.username}")
        return message
        
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating message"
        )