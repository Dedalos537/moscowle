import logging
from datetime import datetime, timedelta

from app.services.automation.financial_analysis import PatientFinancialStatus
from app.services.email_service import EmailService


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

            from app.repositories.patient_repository import PatientRepository

            repo = PatientRepository()
            patients = repo.get_active_patients()

            for p in patients:
                if not p.email:
                    continue

                try:
                    is_finished = False
                    is_finishing_soon = False

                    total = p.sessions_total or 0
                    attended = p.sessions_attended or 0

                    if total > 0:
                        if attended >= total:
                            is_finished = True
                        elif attended >= (total - 1):
                            is_finishing_soon = True

                    if p.payment_due_date and p.payment_due_date <= today.date():
                        is_finished = True

                    should_send = False
                    if (
                        is_finished
                        or is_finishing_soon
                        and p.payment_due_date
                        and (p.payment_due_date - today.date()).days <= 3
                    ):
                        should_send = True

                    if not should_send:
                        continue

                    fin = PatientFinancialStatus(p.id)
                    current_debt = fin.calculate_balance()

                    next_block_sessions = p.sessions_total or 4
                    next_block_sessions = max(next_block_sessions, 4)

                    unit_cost = p.session_cost or 0
                    new_block_cost = next_block_sessions * unit_cost

                    total_to_pay = new_block_cost + max(0, current_debt)

                    end_date_obj = p.payment_due_date if p.payment_due_date else today.date()
                    end_date_str = end_date_obj.strftime('%d/%m/%Y')

                    next_period_start = end_date_obj
                    next_period_end = next_period_start + timedelta(weeks=4)

                    email_data = {
                        'tutor_name': p.guardian_name or 'Estimado Cliente',
                        'patient_name': p.username,
                        'end_date': end_date_str,
                        'period_start': next_period_start.strftime('%d/%m/%Y'),
                        'period_end': next_period_end.strftime('%d/%m/%Y'),
                        'new_block_cost': f'{new_block_cost:.2f}',
                        'debt': f'{max(0, current_debt):.2f}',
                        'total': f'{total_to_pay:.2f}',
                    }

                    logger.info(f'Preparing renewal email for {p.username} ({p.email})')
                    if send_renewal_email(p.email, email_data):
                        logger.info(f'SUCCESS: Sent to {p.email}')
                    else:
                        logger.error(f'FAILED: Could not send to {p.email}')

                except Exception as e:
                    logger.error(f'Error processing patient {p.id}: {str(e)}')
                    continue

        except Exception as e:
            logger.critical(f'Critical Automation Failure: {str(e)}')


def send_renewal_email(to_email, data, retries=3):
    """
    Sends the specific renewal template with retry logic.
    """
    attempt = 0
    while attempt < retries:
        try:
            subject = f'Renovación de Bloque de Terapias - {data["patient_name"]}'

            body = f"""
Estimado/a {data['tutor_name']}, muy buenas tardes. Esperamos que se encuentre muy bien.

Le escribimos para comentarle que el día {data['end_date']} {data['patient_name']} finalizó con éxito su bloque de terapias. Para poder asegurar la continuidad de sus sesiones y que no pierda el ritmo de sus avances, le compartimos el estado de cuenta actual para la renovación:

* Nuevo bloque de terapias: S/ {data['new_block_cost']}
* Saldo pendiente anterior: S/ {data['debt']}
* Total a cancelar: S/ {data['total']}

Le agradeceríamos mucho si nos puede enviar el comprobante de pago a la brevedad para dejar sus próximos horarios 100% confirmados. ¡Quedamos atentos y muchas gracias!
            """

            EmailService.send_email(
                subject=subject,
                recipients=[to_email],
                text_body=body,
                html_body=f"<pre style='font-family: sans-serif; font-size: 14px;'>{body}</pre>",
            )
            return True

        except Exception as e:
            attempt += 1
            print(f'Email attempt {attempt} failed: {e}')
            if attempt == retries:
                logging.error(f'Failed to send email to {to_email} after {retries} attempts.')
                return False
