from datetime import datetime

from app.extensions import db
from app.models.service_request import ServiceRequest
from app.repositories.base import BaseRepository


class ServiceRequestRepository(BaseRepository[ServiceRequest]):
    def __init__(self):
        super().__init__(ServiceRequest)

    def find_by_requester(self, user_id, page=1, per_page=20):
        return self.paginate(page=page, per_page=per_page, requester_id=user_id)

    def find_pending(self, page=1, per_page=20):
        return self.paginate(page=page, per_page=per_page, status='pending')

    def approve(self, request_id, admin_id, notes=None):
        record = self.get_by_id_or_404(request_id)
        record.status = 'approved'
        record.approved_by_id = admin_id
        record.admin_notes = notes
        record.resolved_at = datetime.utcnow()
        db.session.commit()
        return record

    def reject(self, request_id, admin_id, notes=None):
        record = self.get_by_id_or_404(request_id)
        record.status = 'rejected'
        record.approved_by_id = admin_id
        record.admin_notes = notes
        record.resolved_at = datetime.utcnow()
        db.session.commit()
        return record


service_request_repo = ServiceRequestRepository()
