from datetime import datetime

from app.extensions import bcrypt
from app.models import Appointment, Chat, Message, Notification, Payment, User


class TestUserModel:
    def test_create_user(self, session):
        user = User(
            username='newuser',
            email='new@example.com',
            role='terapista',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.commit()
        assert user.id is not None
        assert user.username == 'newuser'
        assert user.email == 'new@example.com'
        assert user.role == 'terapista'

    def test_user_repr(self, session):
        user = User(
            username='repruser',
            email='repr@example.com',
            role='admin',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.commit()
        assert 'User' in repr(user)
        assert str(user.id) in repr(user)

    def test_user_default_role(self, session):
        user = User(
            username='norole',
            email='norole@example.com',
            role='admin',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.commit()
        assert user.role is not None


class TestPaymentModel:
    def test_create_payment(self, session, test_user):
        payment = Payment(patient_id=test_user.id, amount=150.00, method='yape', status='completed')
        session.add(payment)
        session.commit()
        assert payment.id is not None
        assert float(payment.amount) == 150.0
        assert payment.status == 'completed'

    def test_payment_default_status(self, session, test_user):
        payment = Payment(patient_id=test_user.id, amount=50.0, method='cash')
        session.add(payment)
        session.commit()
        assert payment.status is not None


class TestAppointmentModel:
    def _make_patient(self, session):
        p = User(
            username='patient',
            email='patient@example.com',
            role='paciente',
            password=bcrypt.generate_password_hash('test').decode('utf-8'),
        )
        session.add(p)
        session.commit()
        return p

    def test_create_appointment(self, session, test_user):
        patient = self._make_patient(session)
        appointment = Appointment(
            therapist_id=test_user.id, patient_id=patient.id, start_time=datetime.utcnow(), status='scheduled'
        )
        session.add(appointment)
        session.commit()
        assert appointment.id is not None
        assert appointment.status == 'scheduled'

    def test_appointment_has_default_status(self, session, test_user):
        patient = User(
            username='apt-patient',
            email='apt-patient@example.com',
            role='paciente',
            password=bcrypt.generate_password_hash('test').decode('utf-8'),
        )
        session.add(patient)
        session.flush()
        appointment = Appointment(therapist_id=test_user.id, patient_id=patient.id, start_time=datetime.utcnow())
        session.add(appointment)
        session.flush()
        assert appointment.status is not None


class TestNotificationModel:
    def test_create_notification(self, session, test_user):
        notification = Notification(user_id=test_user.id, message='Test notification')
        session.add(notification)
        session.commit()
        assert notification.id is not None
        assert notification.message == 'Test notification'

    def test_notification_default_is_read(self, session, test_user):
        notification = Notification(user_id=test_user.id, message='Unread')
        session.add(notification)
        session.commit()
        assert notification.is_read is False


class TestChatModel:
    def test_create_chat(self, session, test_user):
        from app.models.chat import ChatParticipant

        user2 = User(
            username='user2',
            email='user2@example.com',
            role='paciente',
            password=bcrypt.generate_password_hash('test').decode('utf-8'),
        )
        session.add(user2)
        session.commit()
        chat = Chat(created_by_id=test_user.id)
        session.add(chat)
        session.commit()
        cp1 = ChatParticipant(chat_id=chat.id, user_id=test_user.id)
        cp2 = ChatParticipant(chat_id=chat.id, user_id=user2.id)
        session.add_all([cp1, cp2])
        session.commit()
        assert chat.id is not None

    def test_chat_message(self, session, test_user):
        from app.models.chat import ChatParticipant

        user2 = User(
            username='user3',
            email='user3@example.com',
            role='paciente',
            password=bcrypt.generate_password_hash('test').decode('utf-8'),
        )
        session.add(user2)
        session.commit()
        chat = Chat(created_by_id=test_user.id)
        session.add(chat)
        session.commit()
        cp1 = ChatParticipant(chat_id=chat.id, user_id=test_user.id)
        cp2 = ChatParticipant(chat_id=chat.id, user_id=user2.id)
        session.add_all([cp1, cp2])
        session.commit()
        msg = Message(chat_id=chat.id, sender_id=test_user.id, receiver_id=user2.id, body='Hello!')
        session.add(msg)
        session.commit()
        assert msg.id is not None
        assert msg.body == 'Hello!'
