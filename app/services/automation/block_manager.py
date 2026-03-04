from datetime import datetime, timedelta
from app.models import User, db, payment_therapist, therapist_sede
from sqlalchemy.exc import SQLAlchemyError
import logging

class PatientBlockManager:
    """
    Manages the lifecycle of therapy blocks.
    - Creates new blocks.
    - Tracks unlocked sessions based on payment.
    """
    def __init__(self, patient_id):
        self.patient = User.query.get(patient_id)
        self.logger = logging.getLogger('automation.block_manager')

    def calculate_sessions(self, frequency):
        """
        Calculates total sessions for a 4-week block based on frequency.
        Frequency: 1, 2, or 3 times per week.
        """
        if frequency not in [1, 2, 3]:
            # Default to current estimation
            return 4 # Default 1 per week
            
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
             
        new_sessions = self.calculate_sessions(frequency)
        # We need a way to track "sessions paid for".
        # Let's add that concept in DB or calculate on fly.
        
        # Strategy:
        # 1. Archive current block (if needed, maybe just logs).
        # 2. Update next due date = +4 weeks.
        # 3. Update payment_amount = new block cost.
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
        total_paid = 0 # Query sum(payments)
        rate = self.patient.session_cost
        if rate == 0: return 9999
        
        return int(total_paid / rate)
