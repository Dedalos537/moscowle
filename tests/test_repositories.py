import pytest
from app.repositories.base import BaseRepository
from app.repositories.service_request_repo import ServiceRequestRepository, service_request_repo
from app.models.service_request import ServiceRequest
from app.models.user import User
from app.extensions import bcrypt


class TestBaseRepository:
    def test_get_by_id_returns_none_for_missing(self, session, db):
        repo = BaseRepository(ServiceRequest)
        assert repo.get_by_id(99999) is None

    def test_get_by_id_or_404_raises(self, session, db):
        repo = BaseRepository(ServiceRequest)
        with pytest.raises(Exception):
            repo.get_by_id_or_404(99999)

    def test_create_and_get(self, session, db, test_user):
        repo = BaseRepository(ServiceRequest)
        record = repo.create(
            requester_id=test_user.id,
            category='test',
            title='Repo test',
        )
        assert record.id is not None
        fetched = repo.get_by_id(record.id)
        assert fetched is not None
        assert fetched.title == 'Repo test'

    def test_list_all_with_filters(self, session, db, test_user):
        repo = BaseRepository(ServiceRequest)
        repo.create(requester_id=test_user.id, category='cat_a', title='A')
        repo.create(requester_id=test_user.id, category='cat_b', title='B')
        results = repo.list_all(category='cat_a')
        assert len(results) == 1
        assert results[0].title == 'A'

    def test_update_record(self, session, db, test_user):
        repo = BaseRepository(ServiceRequest)
        record = repo.create(requester_id=test_user.id, category='test', title='Original')
        repo.update(record, title='Updated')
        assert record.title == 'Updated'
        fetched = repo.get_by_id(record.id)
        assert fetched.title == 'Updated'


class TestServiceRequestRepository:
    def test_approve(self, session, db, test_user):
        sr = service_request_repo.create(
            requester_id=test_user.id, category='it', title='Approve repo'
        )
        result = service_request_repo.approve(sr.id, test_user.id, notes='OK')
        assert result.status == 'approved'
        assert result.admin_notes == 'OK'

    def test_reject(self, session, db, test_user):
        sr = service_request_repo.create(
            requester_id=test_user.id, category='it', title='Reject repo'
        )
        result = service_request_repo.reject(sr.id, test_user.id, notes='No')
        assert result.status == 'rejected'
        assert result.admin_notes == 'No'

    def test_find_by_requester(self, session, db, test_user):
        service_request_repo.create(requester_id=test_user.id, category='hr', title='Req 1')
        service_request_repo.create(requester_id=test_user.id, category='hr', title='Req 2')
        page = service_request_repo.find_by_requester(test_user.id)
        assert page.total >= 2

    def test_find_pending(self, session, db, test_user):
        service_request_repo.create(requester_id=test_user.id, category='ops', title='Pending')
        page = service_request_repo.find_pending()
        for item in page.items:
            assert item.status == 'pending'
