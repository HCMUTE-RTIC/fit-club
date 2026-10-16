"""Open event discovery and self-registration never grant roster-management access."""
from test_api import api, auth, event
from test_clubs import club


def setup_catalog(api, monkeypatch, opened=True):
    root = auth(api, monkeypatch)
    eid = event(api, root, 'FIT Club Day')
    cid = club(api, root, eid, 'RTIC', opened=opened)
    student = auth(api, monkeypatch, '10000003')
    return root, student, eid, cid


def test_unregistered_student_can_discover_open_event_and_clubs(api, monkeypatch):
    _, student, eid, cid = setup_catalog(api, monkeypatch)
    response = api.get('/events/discover', headers=student)
    assert response.status_code == 200, response.text
    assert [item['id'] for item in response.json()] == [eid]
    response = api.get(f'/events/{eid}/clubs/discover', headers=student)
    assert response.status_code == 200, response.text
    assert response.json()[0]['id'] == cid
    assert response.json()[0]['registered'] is False
    assert response.json()[0]['can_manage'] is False
    assert api.get(f'/events/{eid}/clubs/{cid}/me', headers=student).json()['registered'] is False
    assert api.get(f'/events/{eid}/clubs/{cid}/students', headers=student).status_code == 403


def test_self_join_is_idempotent_and_registers_only_current_user(api, monkeypatch):
    root, student, eid, cid = setup_catalog(api, monkeypatch)
    base = f'/events/{eid}/clubs/{cid}'
    root_id = api.get('/auth/me', headers=root).json()['id']
    for _ in range(2):
        response = api.post(base + '/join', headers=student, json={'user_id': root_id})
        assert response.status_code == 200, response.text
        assert response.json()['registered'] is True
    rows = api.get(base + '/students', headers=root).json()
    assert rows['total'] == 1
    assert rows['items'][0]['student_id'] == '10000003'
    assert rows['items'][0]['attended'] is False
    assert api.get('/auth/me', headers=student).json()['role'] == 'student'
    assert api.get(base + '/qr', headers=student).status_code == 200


def test_join_available_before_booth_checkin_opens(api, monkeypatch):
    root, student, eid, cid = setup_catalog(api, monkeypatch, opened=False)
    base = f'/events/{eid}/clubs/{cid}'
    assert api.post(base + '/join', headers=student).status_code == 200
    assert api.get(base + '/qr', headers=student).status_code == 409
    assert api.patch(base + '/checkin', headers=root, json={'checkin_open': True}).status_code == 200
    assert api.get(base + '/qr', headers=student).status_code == 200


def test_closed_event_is_not_discoverable_and_cannot_be_joined(api, monkeypatch):
    root, student, eid, cid = setup_catalog(api, monkeypatch)
    api.put(f'/events/{eid}', headers=root, json={'title': 'Closed', 'starts_at': '2026-10-17T08:00:00+07:00', 'checkin_open': False})
    assert api.get('/events/discover', headers=student).json() == []
    assert api.get(f'/events/{eid}/clubs/discover', headers=student).json() == []
    assert api.post(f'/events/{eid}/clubs/{cid}/join', headers=student).status_code == 409
    assert api.get(f'/events/{eid}/clubs/{cid}/students', headers=root).json()['total'] == 0


def test_anonymous_cannot_discover_or_join(api, monkeypatch):
    _, _, eid, cid = setup_catalog(api, monkeypatch)
    assert api.get('/events/discover').status_code in (401, 403)
    assert api.post(f'/events/{eid}/clubs/{cid}/join').status_code in (401, 403)
