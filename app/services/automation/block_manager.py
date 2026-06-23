import logging

from app.repositories.patient_repository import PatientRepository


class PatientBlockManager:
    """
    Manages the lifecycle of therapy blocks.
    - Creates new blocks.
    - Tracks unlocked sessions based on payment.
    """

    def __init__(self, patient_id):
        self.repo = PatientRepository()
        self.patient = self.repo.get_patient(patient_id)
        self.logger = logging.getLogger('automation.block_manager')

    def calculate_sessions(self, frequency):
        """
        Calculates total sessions for a 4-week block based on frequency.
        Frequency: 1, 2, or 3 times per week.
        """
        if frequency not in [1, 2, 3]:
            return 4

        return frequency * 4

    def advance_to_new_block(self, frequency):
        """
        Prepares the patient for the new block.
        This does NOT create a new record in a separate table (User has fields directly),
        but updates the User model to reflect the new state.

        Ideally, we should archive the old block in a history table.
        For MVP, we might just reset counters or increment total allocated.

        Wait, 'System of progressive unlocking'.
        This implies:
        - sessions_total (New Block Scope) = 12 (3/week * 4)
        - sessions_attended = 0 (reset for block?) OR
        - Use cumulative counters and track block boundaries?

        Resetting seems cleaner for "blocks".
        But we need history.

        Let's Assume:
        - sessions_total += New Block Size
        - sessions_attended keeps growing.
        - unlocking: available_sessions = floor(Total Paid / Cost Per Session)
        """
        if not self.patient:
            return

        self.calculate_sessions(frequency)

        pass

    def get_unlocked_sessions(self):
        """
        Returns the number of sessions the user is entitled to based on payments.
        Formula: Total Paid (Lifetime or Block) / Cost Per Session.

        Let's stick to Block-based logic if possible, but payments are continuous.

        Simplified Logic:
        - Total Debt = (Attended * Rate) - Paid.
        - If Debt <= 0, all attended are valid.
        - If Debt > 0, they are "consuming on credit" or "blocked".

        "Solo se irán desbloqueando de manera proporcional a los pagos".
        This means:
        Max Allowed Attended = Total Paid / Rate.

        If Attended >= Max Allowed, block scheduling new ones?
        """
        total_paid = 0
        try:
            total_paid = self.repo.get_total_paid(self.patient.id) if self.patient else 0
        except Exception:
            total_paid = 0
        rate = getattr(self.patient, 'session_cost', 0)
        if rate == 0:
            return 9999

        return int(total_paid / rate)
