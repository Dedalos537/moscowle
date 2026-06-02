from datetime import datetime
from app.extensions import db


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    method = db.Column(db.String(50), nullable=False)
    reference = db.Column(db.String(100), nullable=True)
    receipt_image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='completed')
    notes = db.Column(db.Text, nullable=True)
    discount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    method = db.Column(db.String(50), nullable=True)
    receipt_image_path = db.Column(db.String(255), nullable=True)
    therapist = db.relationship('User', backref=db.backref('expenses', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class YapeTransaction(db.Model):

    __tablename__ = 'yape_transaction'

    id = db.Column(db.Integer, primary_key=True)

    operation_number = db.Column(db.String(100), unique=True, nullable=False, index=True)

    transaction_date = db.Column(db.DateTime, nullable=False)
    sender_name = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    message = db.Column(db.Text, nullable=True)

    category = db.Column(db.String(50), default='unclassified')
    is_expense = db.Column(db.Boolean, default=False)

    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=True)
    expense = db.relationship('Expense', backref='yape_transaction')

    receipt_image_path = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    import_batch_id = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<YapeTransaction {self.operation_number} - {self.amount}>'
