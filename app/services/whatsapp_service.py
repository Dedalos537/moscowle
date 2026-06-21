import json
import logging
import os
import subprocess
import tempfile
import threading
from datetime import datetime

from flask import current_app

logger = logging.getLogger(__name__)

WHATSAPP_SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'whatsapp_sessions')


class WhatsAppService:
    """WhatsApp integration via Baileys (Node.js bridge)

    Uses a small Node.js script that runs Baileys to connect to WhatsApp Web.
    Falls back to wa.me links if the bridge is not connected.
    """

    def __init__(self):
        self.connected = False
        self.qr_code = None
        self._process = None
        self._ready = threading.Event()
        self.session_path = WHATSAPP_SESSION_DIR

    def start(self):
        """Start the Baileys Node.js bridge process"""
        bridge_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp_bridge')
        main_js = os.path.join(bridge_path, 'index.js')

        if not os.path.exists(main_js):
            logger.warning("WhatsApp bridge not found at %s. Run 'node setup.js' in whatsapp_bridge/", main_js)
            return False

        try:
            self._process = subprocess.Popen(
                ['node', 'index.js'],
                cwd=bridge_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            threading.Thread(target=self._read_output, daemon=True).start()
            return True
        except FileNotFoundError:
            logger.error("Node.js not found. Install Node.js to use WhatsApp.")
            return False

    def _read_output(self):
        for line in self._process.stdout:
            try:
                data = json.loads(line.strip())
                if data.get('type') == 'qr':
                    self.qr_code = data['qr']
                    self.connected = False
                elif data.get('type') == 'ready':
                    self.connected = True
                    self.qr_code = None
                    self._ready.set()
                elif data.get('type') == 'disconnected':
                    self.connected = False
                    self._ready.clear()
            except (json.JSONDecodeError, KeyError):
                pass

    def stop(self):
        if self._process:
            self._process.terminate()
            self._process = None
        self.connected = False
        self.qr_code = None

    @property
    def is_connected(self):
        return self.connected

    def send_message(self, phone, message):
        """Send a WhatsApp message via Baileys bridge or fallback to wa.me"""
        if not self.connected:
            return self._generate_wa_link(phone, message)

        if self._process:
            payload = json.dumps({'type': 'send', 'phone': phone, 'message': message})
            self._process.stdin.write(payload + '\n')
            self._process.stdin.flush()
            return {'sent': True, 'method': 'baileys'}

        return self._generate_wa_link(phone, message)

    def send_installment_reminder(self, patient_name, patient_phone, installment_number,
                                  due_date, amount, days_overdue=0):
        """Send a debt reminder for an installment"""
        if days_overdue <= 0:
            msg = (
                f"Hola {patient_name}, 👋\\n\\n"
                f"Recordarte que tu cuota N°{installment_number} de S/ {amount:.2f} "
                f"vence el {due_date}.\\n\\n"
                f"¡Gracias por confiar en nosotros! 🙌"
            )
        else:
            msg = (
                f"Hola {patient_name}, 👋\\n\\n"
                f"Tu cuota N°{installment_number} de S/ {amount:.2f} "
                f"tiene {days_overdue} días de atraso (vencía el {due_date}).\\n\\n"
                f"Por favor regulariza tu situación para evitar bloqueos. "
                f"¡Estamos para ayudarte! 🙌"
            )

        return self.send_message(patient_phone, msg)

    @staticmethod
    def _generate_wa_link(phone, message):
        """Fallback: generate wa.me link for manual sending"""
        import urllib.parse
        clean_phone = ''.join(filter(str.isdigit, phone))
        if clean_phone.startswith('0'):
            clean_phone = '51' + clean_phone[1:]
        if not clean_phone.startswith('51'):
            clean_phone = '51' + clean_phone
        encoded = urllib.parse.quote(message[:500])
        link = f'https://wa.me/{clean_phone}?text={encoded}'
        return {'sent': False, 'method': 'link', 'url': link}


whatsapp_service = WhatsAppService()
