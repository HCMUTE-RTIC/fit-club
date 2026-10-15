"""Temporary open Google email mode preserves identity and role boundaries."""
import pytest
from test_api import api, auth, event
from app import main as m


def external_login(api, monkeypatch, email='tester@gmail.com', **extra):
    claims = {'sub': 'google-' + str(email), 'email': email, 'email_verified': True, 'name': 'External Tester', **extra}
    monkeypatch.setattr(m, 'verify_google', lambda credential: claims)
    return api.post('/auth/google', json={'credential': 'test-google-credential'})


def test_default_is_strict():
    assert m.Settings.model_fields['student_email_only'].default is True


def test_strict_rejects_external(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', True)
    assert external_login(api, monkeypatch).status_code == 403


def test_open_google_login_and_me(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', False)
    response = external_login(api, monkeypatch)
    assert response.status_code == 200, response.text
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    me = api.get('/auth/me', headers=headers).json()
    assert me['email'] == 'tester@gmail.com'
    assert me['name'] == 'External Tester'
    assert me['role'] == 'student'
    assert me['student_id'].startswith('g') and len(me['student_id']) == 15
    first_id = me['id']
    response = external_login(api, monkeypatch)
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    assert api.get('/auth/me', headers=headers).json()['id'] == first_id


@pytest.mark.parametrize('claims', [{'email_verified': False}, {'email_verified': 'true'}, {'sub': ''}, {'email': 'invalid'}, {'email': None}])
def test_open_still_rejects_unverified_or_invalid(api, monkeypatch, claims):
    monkeypatch.setattr(m.settings, 'student_email_only', False)
    assert external_login(api, monkeypatch, **claims).status_code in (403, 422)


def test_open_identifier_stable_and_separate(monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', False)
    assert m.student_email(' TESTER@GMAIL.COM ') == m.student_email('tester@gmail.com')
    identifiers = {m.student_email(f'{i}@gmail.com')[1] for i in range(2000)}
    assert len(identifiers) == 2000
    assert m.student_email('10000001@student.hcmute.edu.vn')[1] == '10000001'


def test_open_external_admin_assignment(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', False)
    root = auth(api, monkeypatch)
    eid = event(api, root)
    response = api.post(f'/events/{eid}/admins', headers=root, json={'email': 'tester@gmail.com', 'name': 'Tester'})
    assert response.status_code == 201, response.text
    expected_id = response.json()['id']
    response = external_login(api, monkeypatch)
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    me = api.get('/auth/me', headers=headers).json()
    assert me['id'] == expected_id and me['role'] == 'admin'
    assert me['admin_event_ids'] == [eid]
    assert api.get(f'/events/{eid}/students', headers=headers).status_code == 200
    assert api.post('/events', headers=headers, json={'title': 'Denied', 'starts_at': '2026-10-17T08:00:00+07:00'}).status_code == 403


def test_open_prevents_google_identity_rebinding(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', False)
    assert external_login(api, monkeypatch).status_code == 200
    assert external_login(api, monkeypatch, sub='different-sub').status_code == 403
