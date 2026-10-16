"""Email-based privileged access while ordinary participants remain student-only."""
import pytest

from test_api import api, auth, event
from test_clubs import club
from app import main as m


def external_login(api, monkeypatch, email):
    monkeypatch.setattr(m, 'verify_google', lambda _: {
        'sub': 'google-' + email, 'email': email, 'email_verified': True, 'name': 'Google User',
    })
    return api.post('/auth/google', json={'credential': 'verified-google-credential'})


def test_bootstrap_gmail_can_login_without_opening_student_policy(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', True)
    monkeypatch.setattr(m.settings, 'superadmin_emails', 'hovietanh147@gmail.com')
    response = external_login(api, monkeypatch, 'hovietanh147@gmail.com')
    assert response.status_code == 200, response.text
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    assert api.get('/auth/me', headers=headers).json()['role'] == 'superadmin'
    assert external_login(api, monkeypatch, 'stranger@gmail.com').status_code == 403


def test_superadmin_can_grant_by_email_only_before_first_login(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', True)
    root = auth(api, monkeypatch)
    response = api.post('/access/grants', headers=root, json={'email': ' Staff@Gmail.com ', 'role': 'superadmin'})
    assert response.status_code == 201, response.text
    assert response.json()['email'] == 'staff@gmail.com'
    login = external_login(api, monkeypatch, 'staff@gmail.com')
    assert login.status_code == 200, login.text
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    identity = api.get('/auth/me', headers=headers).json()
    assert identity['role'] == 'superadmin' and identity['name'] == 'Google User'
    assert api.delete('/superadmins/' + str(identity['id']), headers=root).status_code == 204
    assert api.post('/events', headers=headers, json={'title': 'No', 'starts_at': '2026-10-17T08:00:00+07:00'}).status_code == 403
    assert external_login(api, monkeypatch, 'staff@gmail.com').status_code == 403


def test_gmail_club_admin_gets_only_assigned_scope(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', True)
    root = auth(api, monkeypatch)
    eid = event(api, root)
    first, second = club(api, root, eid), club(api, root, eid, 'DSC')
    response = api.post('/access/grants', headers=root,
                        json={'email': 'admin@gmail.com', 'role': 'admin', 'event_id': eid, 'club_id': first})
    assert response.status_code == 201, response.text
    login = external_login(api, monkeypatch, 'admin@gmail.com')
    assert login.status_code == 200, login.text
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    assert api.get('/auth/me', headers=headers).json()['admin_club_ids'] == [first]
    assert api.get(f'/events/{eid}/clubs/{first}/students', headers=headers).status_code == 200
    assert api.get(f'/events/{eid}/clubs/{second}/students', headers=headers).status_code == 403
    assert api.post('/access/grants', headers=headers, json={'email': 'other@gmail.com', 'role': 'superadmin'}).status_code == 403


@pytest.mark.parametrize('body', [
    {'email': 'x@gmail.com', 'role': 'admin'},
    {'email': 'x@gmail.com', 'role': 'owner'},
    {'email': 'not-an-email', 'role': 'superadmin'},
    {'email': 'x@gmail.com', 'role': 'superadmin', 'club_id': 1},
])
def test_invalid_role_grants_do_not_create_privileges(api, monkeypatch, body):
    root = auth(api, monkeypatch)
    assert api.post('/access/grants', headers=root, json=body).status_code == 422


def test_external_admin_grants_do_not_enable_external_student_import(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', True)
    root = auth(api, monkeypatch)
    eid = event(api, root)
    cid = club(api, root, eid)
    body = {'email': 'admin@gmail.com', 'name': 'Staff'}
    assert api.post(f'/events/{eid}/clubs/{cid}/admins', headers=root, json=body).status_code == 201
    assert api.post(f'/events/{eid}/clubs/{cid}/students', headers=root, json=body).status_code == 422


def test_external_admin_still_requires_verified_google_identity(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'student_email_only', True)
    monkeypatch.setattr(m.settings, 'superadmin_emails', 'hovietanh147@gmail.com')
    monkeypatch.setattr(m, 'verify_google', lambda _: {
        'sub': 'external', 'email': 'hovietanh147@gmail.com', 'email_verified': False, 'name': 'Staff',
    })
    assert api.post('/auth/google', json={'credential': 'invalid-google-credential'}).status_code == 403
