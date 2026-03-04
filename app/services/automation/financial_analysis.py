from datetime import datetime, timedelta
from app.models import User, Payment, Appointment, db
from flask import current_app
from sqlalchemy import func
import logging

class PatientFinancialStatus:
    def __init__(self, patient_id):
        self.patient = User.query.get(patient_id)
        self.logger = logging.getLogger('automation.financial')

    def calculate_balance(self):
        """
        Calculates the patient's current financial balance.
        DEBT = (Total Sessions Consumed * Cost Per Session) - (Total Payments Made)
        """
        if not self.patient:
            return 0.0

        # 1. Total Payments
        total_paid = db.session.query(func.sum(Payment.amount)).filter(
            Payment.patient_id == self.patient.id,
            Payment.status == 'completed'
        ).scalar() or 0.0

        # 2. Total Cost Incurred (Sessions Attended * Rate)
        # We use the current session_cost. 
        # Ideally, we should track cost at the time of session, but for MVP we use current rate.
        sessions_attended = self.patient.sessions_attended or 0
        current_rate = self.patient.session_cost or 0.0
        
        # Consider block history if complex? 
        # For now, simplistic approach:
        # Cost = sessions_attended * rate
        
        # BUT user prompt mentions: "Un bloque de renovación comprende exactamente 4 semanas."
        # And "total de terapias dinámicamente".
        # Let's assume sessions_total is the block size.
        
        total_cost = sessions_attended * current_rate
        
        balance = total_cost - total_paid
        return balance

    def get_block_status(self):
        """
        Determines if the current block is finished.
        """
        total = self.patient.sessions_total or 0
        attended = self.patient.sessions_attended or 0
        
        if total == 0:
            return "no_block"
            
        remaining = total - attended
        
        if remaining <= 0:
            return "finished"
        elif remaining <= 2: # Warning threshold
            return "finishing_soon"
        else:
            return "active"

    def calculate_new_block_cost(self):
        """
        Calculates cost for a new 4-week block based on frequency.
        Frequency is derived from 'payment_plan' or explicitly stored?
        User model has 'payment_plan' (monthly/bi-weekly). 
        Let's infer frequency from allocated sessions or add a field if needed.
        
        Assuming:
        - Monthly = 4 weeks.
        - Sessions per week = Total sessions / 4.
        """
        current_total = self.patient.sessions_total
        if not current_total or current_total == 0:
             # Default fallback: 1 session a week = 4 sessions
             sessions_per_block = 4
        else:
             # Reuse previous block size
             sessions_per_block = current_total
             
        unit_cost = self.patient.session_cost or 0
        return sessions_per_block * unit_cost
