from datetime import datetime, timedelta
from app.models import User, db, Payment, Appointment
from app.services.email_service import EmailService
from app.services.automation.financial_analysis import PatientFinancialStatus
from app.services.automation.block_manager import PatientBlockManager
from flask import current_app
import logging

def auto_generate_billing_reminder(app):
    """
    Cron Job Function:
    1. Scan patients who are close to finishing a block.
    2. Logic:
       - If sessions_total is set (e.g. 4), check sessions_attended (e.g. 3 or 4).
       - If attended >= total, send "Finalized Block" email immediately.
       - If attended == total - 1, send "Finishing Soon" warning (optional).
    3. Generate costs based on block frequency.
    4. Send email.
    """
    with app.app_context():
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('automation.billing')
        
        try:
            today = datetime.now()
            
            # Find Active Patients (excluding dropped out/inactive)
            patients = User.query.filter_by(role='jugador', is_active=True).all()
            
            for p in patients:
                # 0. Skip if email missing
                if not p.email:
                    continue
                    
                try:
                    # 1. Check Block Status
                    # Logic: A "Block" is finished if attended >= total.
                    # Or if due_date is passed.
                    
                    is_finished = False
                    is_finishing_soon = False
                    
                    total = p.sessions_total or 0
                    attended = p.sessions_attended or 0
                    
                    if total > 0:
                        if attended >= total:
                            is_finished = True
                        elif attended >= (total - 1):
                            is_finishing_soon = True
                    
                    # Also check date-based expiration if sessions are slow
                    if p.payment_due_date and p.payment_due_date <= today.date():
                        is_finished = True

                    # Trigger Condition: Only send if "finished" or "finishing soon" AND not already sent recently?
                    # We need a way to track "last_renewal_email_sent_at".
                    # Since we don't have that column yet, let's use a simple heuristic:
                    # If finished/finishing soon AND due_date is close (within 3 days) OR passed.
                    
                    should_send = False
                    if is_finished:
                        should_send = True
                    elif is_finishing_soon and p.payment_due_date and (p.payment_due_date - today.date()).days <= 3:
                        should_send = True
                        
                    if not should_send:
                        continue

                    # 2. Calculate Costs
                    fin = PatientFinancialStatus(p.id)
                    current_debt = fin.calculate_balance() # (Attended * Rate) - Paid
                    
                    # New Block Cost Calculation (Strict Rules)
                    # "Siempre son minimo 4 sesiones, 4 semanas".
                    # Frequency Logic:
                    # - If sessions_total indicates a weekly pattern (e.g., 4, 8, 12, etc.), trust it.
                    # - If irregular, assume minimum 4 (1/week).
                    # - If plan is 'weekly', careful not to multiply by 4 again if sessions_total is already weekly count.
                    # BUT user logic says "Bloque de renovacion comprende exactamente 4 semanas".
                    # So cost must cover 4 weeks.
                    
                    # Estimate weekly frequency
                    # If sessions_total represents the FULL BLOCK (monthly), then we use it.
                    # If sessions_total represents WEEKLY frequency, we multiply by 4.
                    # Standard practice for 'monthly' plan: sessions_total = 4, 8, 12.
                    
                    next_block_sessions = p.sessions_total or 4
                    if next_block_sessions < 4:
                        next_block_sessions = 4 # Enforce minimum 4 sessions rule
                        
                    unit_cost = p.session_cost or 0
                    new_block_cost = next_block_sessions * unit_cost
                    
                    # Total
                    total_to_pay = new_block_cost + max(0, current_debt)

                    # 3. Prepare Email Data
                    # End Date Logic: If due date exists, use it. Else calculate 4 weeks from today? 
                    # No, "end_date" means when the current block ends.
                    # "4 semanas a partir de la sesion" -> implies next due date is +28 days from now/last due date.
                    
                    end_date_obj = p.payment_due_date if p.payment_due_date else today.date()
                    end_date_str = end_date_obj.strftime('%d/%m/%Y')
                    
                    # Determine Next Period (for context)
                    next_period_start = end_date_obj
                    next_period_end = next_period_start + timedelta(weeks=4)
                    
                    email_data = {
                        'tutor_name': p.guardian_name or "Estimado Cliente",
                        'patient_name': p.username,
                        'end_date': end_date_str, # The date current block finishes
                        'period_start': next_period_start.strftime('%d/%m/%Y'),
                        'period_end': next_period_end.strftime('%d/%m/%Y'),
                        'new_block_cost': "{:.2f}".format(new_block_cost),
                        'debt': "{:.2f}".format(max(0, current_debt)),
                        'total': "{:.2f}".format(total_to_pay)
                    }
                    
                    # 4. Send Email
                    logger.info(f"Preparing renewal email for {p.username} ({p.email})")
                    if send_renewal_email(p.email, email_data):
                        logger.info(f"SUCCESS: Sent to {p.email}")
                        # TODO: Mark as sent in DB to avoid dupes (e.g. update status to 'notified')
                    else:
                        logger.error(f"FAILED: Could not send to {p.email}")

                except Exception as e:
                    logger.error(f"Error processing patient {p.id}: {str(e)}")
                    continue

        except Exception as e:
            logger.critical(f"Critical Automation Failure: {str(e)}")

def send_renewal_email(to_email, data, retries=3):
    """
    Sends the specific renewal template with retry logic.
    """
    attempt = 0
    while attempt < retries:
        try:
            # Construct Subject
            subject = f"Renovación de Bloque de Terapias - {data['patient_name']}"
            
            # Construct Body (Template from Prompt)
            body = f"""
Estimado/a {data['tutor_name']}, muy buenas tardes. Esperamos que se encuentre muy bien.

Le escribimos para comentarle que el día {data['end_date']} {data['patient_name']} finalizó con éxito su bloque de terapias. Para poder asegurar la continuidad de sus sesiones y que no pierda el ritmo de sus avances, le compartimos el estado de cuenta actual para la renovación:

* Nuevo bloque de terapias: S/ {data['new_block_cost']}
* Saldo pendiente anterior: S/ {data['debt']}
* Total a cancelar: S/ {data['total']}

Le agradeceríamos mucho si nos puede enviar el comprobante de pago a la brevedad para dejar sus próximos horarios 100% confirmados. ¡Quedamos atentos y muchas gracias!
            """
            
            # Use EmailService
            EmailService.send_email(
                subject=subject,
                recipients=[to_email],
                text_body=body,
                html_body=f"<pre style='font-family: sans-serif; font-size: 14px;'>{body}</pre>" 
            )
            return True
            
        except Exception as e:
            attempt += 1
            print(f"Email attempt {attempt} failed: {e}")
            if attempt == retries:
                # Log final failure
                logging.error(f"Failed to send email to {to_email} after {retries} attempts.")
                return False
