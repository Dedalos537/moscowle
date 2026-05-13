"""
Servicio de Auditoría IA para Sesiones Terapéuticas.
Integra Whisper (STT vía Groq) + Llama 3 (Auditoría vía Groq) para comparar
la Programación (.docx) contra la Ejecución Real (audio + fotos).

Cumple con:
  - HU-06: Extracción de objetivos del Word
  - HU-08: Privacidad — audio eliminado tras transcripción
  - HU-09: Clasificación de objetivos en Logrado / Parcial / No cubierto
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# FASE 1 — Extracción de texto del Word (.docx)
# ═══════════════════════════════════════════════════════════════

def extract_docx_text(file_path):
    """
    Extrae todo el texto de un archivo .docx usando python-docx.
    Preserva la estructura de párrafos y tablas para que el LLM
    pueda identificar secciones como Objetivos, Actividades, Materiales.
    
    Args:
        file_path: Ruta absoluta al archivo .docx
        
    Returns:
        str: Texto completo extraído del documento
        
    Raises:
        ValueError: Si el archivo no es un .docx válido
    """
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx no está instalado. Ejecuta: pip install python-docx")
    
    if not os.path.exists(file_path):
        raise ValueError(f"Archivo no encontrado: {file_path}")
    
    try:
        doc = Document(file_path)
    except Exception as e:
        raise ValueError(f"Error al abrir el archivo Word: {str(e)}")
    
    sections = []
    
    # Extraer párrafos con su estilo (heading, normal, etc.)
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        # Marcar headings para dar contexto al LLM
        if para.style and para.style.name.startswith('Heading'):
            sections.append(f"\n## {text}")
        else:
            sections.append(text)
    
    # Extraer tablas (frecuentes en programaciones terapéuticas)
    for table in doc.tables:
        table_rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            table_rows.append(" | ".join(cells))
        if table_rows:
            sections.append("\n[TABLA]\n" + "\n".join(table_rows) + "\n[/TABLA]")
    
    full_text = "\n".join(sections)
    
    if not full_text.strip():
        raise ValueError("El documento Word está vacío o no contiene texto extraíble")
    
    logger.info(f"Texto extraído del Word: {len(full_text)} caracteres")
    return full_text


# ═══════════════════════════════════════════════════════════════
# FASE 2 — Transcripción de Audio (Whisper vía Groq API)
# ═══════════════════════════════════════════════════════════════

def transcribe_audio(file_path):
    """
    Envía el archivo de audio a la API de Groq (Whisper) para transcripción.
    
    PRIVACIDAD (RNF-02 / HU-08): El archivo de audio se ELIMINA
    del servidor INMEDIATAMENTE después de obtener la transcripción,
    sin importar si la transcripción fue exitosa o no.
    
    Args:
        file_path: Ruta absoluta al archivo de audio (.webm, .wav, .mp3, etc.)
        
    Returns:
        dict: {
            'text': str,              # Transcripción completa
            'duration': int,          # Duración en segundos (estimada)
            'language': str           # Idioma detectado
        }
        
    Raises:
        ValueError: Si el archivo no existe o la API falla
    """
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY no está configurada en las variables de entorno")
    
    if not os.path.exists(file_path):
        raise ValueError(f"Archivo de audio no encontrado: {file_path}")
    
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        # Leer y enviar el archivo a Whisper
        with open(file_path, 'rb') as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(file_path), audio_file),
                model="whisper-large-v3-turbo",
                language="es",           # Español (sesiones en Perú)
                response_format="verbose_json",
                temperature=0.0          # Máxima precisión
            )
        
        transcript_text = transcription.text or ""
        duration = getattr(transcription, 'duration', None)
        language = getattr(transcription, 'language', 'es')
        
        logger.info(f"Audio transcrito: {len(transcript_text)} caracteres, duración={duration}s")
        
        return {
            'text': transcript_text,
            'duration': int(duration) if duration else 0,
            'language': language
        }
        
    except Exception as e:
        logger.error(f"Error en transcripción Whisper/Groq: {str(e)}")
        raise ValueError(f"Error al transcribir el audio: {str(e)}")
    
    finally:
        # ═══════════════════════════════════════════════════════════
        # ELIMINACION OBLIGATORIA DEL AUDIO (RNF-02 / HU-08)
        # El archivo se borra SIEMPRE, incluso si la transcripción falló.
        # ═══════════════════════════════════════════════════════════
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Audio eliminado por privacidad: {file_path}")
        except Exception as del_err:
            logger.error(f"ERROR CRITICO: No se pudo eliminar el audio {file_path}: {del_err}")


# ═══════════════════════════════════════════════════════════════
# FASE 3 — Auditoría IA (Llama 3 vía Groq API)
# ═══════════════════════════════════════════════════════════════

AUDIT_SYSTEM_PROMPT = """Eres un auditor clínico experto del Centro de Terapias Juan Pablo II.
Tu tarea es comparar la PROGRAMACIÓN PLANIFICADA (objetivos terapéuticos del documento Word)
con la TRANSCRIPCIÓN REAL de la sesión (audio transcrito por Whisper).

INSTRUCCIONES ESTRICTAS:
1. Identifica TODOS los objetivos terapéuticos del documento de programación.
2. Busca evidencia en la transcripción de que cada objetivo fue abordado.
3. Clasifica CADA objetivo como:
   - "logrado": Se abordó completamente según lo planificado
   - "parcial": Se mencionó o intentó pero no se completó
   - "no_cubierto": No hay evidencia de que se haya trabajado
4. Calcula un score de cumplimiento (0-100).
5. Identifica actividades extra que se realizaron pero no estaban planificadas.

SIEMPRE responde en este formato JSON exacto (sin texto adicional):
{
  "score": 85.0,
  "status": "cumple_parcial",
  "objectives": [
    {
      "name": "Nombre del objetivo",
      "classification": "logrado|parcial|no_cubierto",
      "evidence": "Extracto relevante de la transcripción que lo respalda"
    }
  ],
  "planned_activities": ["actividad 1", "actividad 2"],
  "executed_activities": ["actividad ejecutada 1"],
  "missing_activities": ["actividad no ejecutada"],
  "extra_activities": ["actividad no planificada que sí se realizó"],
  "observations": "Observaciones generales del auditor",
  "recommendations": ["Recomendación 1", "Recomendación 2"]
}

REGLAS para el campo "status":
- "cumple": score >= 80
- "cumple_parcial": score >= 50 y < 80
- "no_cumple": score < 50
"""


def run_audit(appointment_id):
    """
    Ejecuta la auditoría IA completa para una sesión.
    Compara el planned_text vs transcript_text usando Llama 3 vía Groq.
    
    Args:
        appointment_id: ID de la cita/sesión
        
    Returns:
        dict: Reporte de auditoría parseado
        
    Raises:
        ValueError: Si faltan datos o la IA falla
    """
    from app.models import SessionAudit, SessionImage, db
    
    audit = SessionAudit.query.filter_by(appointment_id=appointment_id).first()
    if not audit:
        raise ValueError("No existe registro de auditoría para esta sesión")
    
    if not audit.planned_text:
        raise ValueError("No se ha subido la programación (.docx) para esta sesión")
    
    if not audit.transcript_text:
        raise ValueError("No se ha transcrito el audio de esta sesión")
    
    # Marcar como en proceso
    audit.audit_status = 'processing'
    db.session.commit()
    
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        audit.audit_status = 'error'
        db.session.commit()
        raise ValueError("GROQ_API_KEY no configurada")
    
    # Obtener fotos de la sesión como contexto adicional
    images = SessionImage.query.filter_by(appointment_id=appointment_id).all()
    photos_context = ""
    if images:
        photo_descriptions = [f"- Foto {i+1}: tipo={img.image_type}, notas='{img.notes or 'sin notas'}'" 
                             for i, img in enumerate(images)]
        photos_context = f"\n\nFOTOS DE LA SESIÓN ({len(images)} archivos):\n" + "\n".join(photo_descriptions)
    
    # Construir el prompt del usuario
    user_prompt = f"""PROGRAMACIÓN PLANIFICADA (extraída del documento Word):
---
{audit.planned_text}
---

TRANSCRIPCIÓN REAL DE LA SESIÓN (audio transcrito por Whisper):
---
{audit.transcript_text}
---
{photos_context}

Analiza y genera el reporte de cumplimiento en formato JSON."""
    
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": AUDIT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Parsear JSON
        report = json.loads(raw_content)
        
        # Guardar resultado
        audit.audit_report_json = json.dumps(report, ensure_ascii=False)
        audit.audit_score = float(report.get('score', 0))
        audit.audit_status = 'completed'
        audit.audited_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Auditoría completada para sesión {appointment_id}: score={audit.audit_score}")
        return report
        
    except json.JSONDecodeError as e:
        audit.audit_status = 'error'
        audit.audit_report_json = json.dumps({
            'error': 'El LLM no devolvió JSON válido',
            'raw_response': raw_content[:500]
        })
        db.session.commit()
        logger.error(f"Error parseando JSON de Llama: {e}")
        raise ValueError(f"Error al procesar respuesta de IA: {str(e)}")
        
    except Exception as e:
        audit.audit_status = 'error'
        db.session.commit()
        logger.error(f"Error en auditoría IA: {str(e)}")
        raise ValueError(f"Error en auditoría IA: {str(e)}")
