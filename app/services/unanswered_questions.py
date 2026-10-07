"""Registro de preguntas que el asistente no supo responder, para cualquier canal.

Solo CUENTA la pregunta (y, al repetirse, la propone como FAQ y avisa a supervisión). No consulta el catálogo de FAQ
para responder: el chat web responde únicamente con herramientas.
"""

from app.services.faq_service import note_if_unanswered as note_if_unanswered  # noqa: PLC0414
