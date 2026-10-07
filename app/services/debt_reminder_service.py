"""Recordatorios automáticos de cuotas vencidas a los apoderados (WhatsApp, con SMS de respaldo).

Antes el trabajo de las 9:00 llamaba a `whatsapp_service.send_installment_reminder`, que no existe: fallaba en la
primera cuota y ningún recordatorio de cobranza salía. Ahora sale por `MessagingService` (número del apoderado, tope
diario, registro en `message_log`) y respeta el interruptor global / modo prueba de `automation_settings`.
"""

import logging

from app.extensions import db
from app.services import automation_settings
from app.services.messaging import MessagingService
from app.services.sms_whatsapp_service import SMSWhatsAppService

logger = logging.getLogger(__name__)


class DebtReminderService:
    def __init__(self, messaging=None, templates=None):
        self.messaging = messaging or MessagingService()
        self.templates = templates or SMSWhatsAppService()

    @staticmethod
    def _should_remind(inst):
        # Se avisa la primera vez y luego cada 7 días de atraso.
        return not inst.get('reminder_sent') or (inst.get('days_overdue') or 0) % 7 == 0

    def run(self, due=None):
        from app.models.contract import Installment
        from app.services.contract_service import ContractService

        due = ContractService().get_due_installments() if due is None else due
        counts = {'sent': 0, 'due': len(due), 'blocked': 0, 'failed': 0}
        for inst in due:
            pid = inst.get('patient_id')
            if not pid or not inst.get('patient_phone') or not self._should_remind(inst):
                continue
            channels = [ch for ch in ('whatsapp', 'sms') if automation_settings.allows(pid, 'debts', ch)[0]]
            if not channels:
                counts['blocked'] += 1
                continue
            due_str = (
                inst['due_date'].strftime('%d/%m/%Y')
                if hasattr(inst.get('due_date'), 'strftime')
                else str(inst.get('due_date') or 'N/A')
            )
            args = (inst['patient_name'], inst['remaining'], due_str, inst['days_overdue'])
            delivered = False
            for channel in channels:
                body = (
                    self.templates._get_whatsapp_template_body(*args)
                    if channel == 'whatsapp'
                    else self.templates._get_sms_template_body(*args)
                )
                result = self.messaging.send_to_patient(
                    pid, body, channel=channel, trigger='automated', template_key='debt_installment'
                )
                if result.get('status') == 'sent':
                    delivered = True
                    break  # WhatsApp salió: no se duplica por SMS
            if delivered:
                installment = db.session.get(Installment, inst['installment_id'])
                if installment:
                    installment.reminder_sent = True
                    db.session.commit()
                counts['sent'] += 1
            else:
                counts['failed'] += 1
        return counts
