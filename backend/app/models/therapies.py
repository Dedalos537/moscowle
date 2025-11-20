from ..extensions import db

class Therapy(db.Model):
    __tablename__ = 'therapies'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Numeric(10,2), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'duration_minutes': int(self.duration_minutes) if self.duration_minutes else None,
            'price': float(self.price) if self.price else None,
        }
