"""FIT Club Day: a shared event with isolated club rosters and booth check-ins."""
from io import BytesIO

from openpyxl import load_workbook
import pytest

from test_api import api, auth, event, excel


def club(api, root, event_id, name='RTIC', opened=True):
    response = api.post(f'/events/{event_id}/clubs', headers=root,
                        json={'name': name, 'description': 'Gian hàng học thuật', 'checkin_open': opened})
    assert response.status_code == 201, response.text
    return response.json()['id']


def setup_clubs(api, monkeypatch):
    root = auth(api, monkeypatch)
    eid = event(api, root, 'FIT CLUB DAY 2026')
    first, second = club(api, root, eid), club(api, root, eid, 'DSC')
    base = f'/events/{eid}/clubs'
    for cid, sid in [(first, '10000002'), (second, '10000004')]:
        response = api.post(f'{base}/{cid}/admins', headers=root,
                            json={'email': f'{sid}@student.hcmute.edu.vn', 'name': f'Admin {sid}'})
        assert response.status_code == 201, response.text
    admin = auth(api, monkeypatch, '10000002')
    other_admin = auth(api, monkeypatch, '10000004')
    student = auth(api, monkeypatch, '10000003')
    for cid in [first, second]:
        response = api.post(f'{base}/{cid}/students', headers=root,
                            json={'email': '10000003@student.hcmute.edu.vn', 'name': 'Sinh viên'})
        assert response.status_code == 201, response.text
    return root, admin, other_admin, student, eid, first, second


def test_club_admin_identity_and_visibility_are_scoped(api, monkeypatch):
    root, admin, _, student, eid, first, second = setup_clubs(api, monkeypatch)
    identity = api.get('/auth/me', headers=admin).json()
    assert identity['role'] == 'admin'
    assert identity['admin_club_ids'] == [first]
    assert [e['id'] for e in api.get('/events', headers=admin).json()] == [eid]
    assert [c['id'] for c in api.get(f'/events/{eid}/clubs', headers=admin).json()] == [first]
    assert {c['id'] for c in api.get(f'/events/{eid}/clubs', headers=student).json()} == {first, second}
    assert len(api.get(f'/events/{eid}/clubs', headers=root).json()) == 2
    # A club admin gains no access to the legacy event-wide roster.
    assert api.get(f'/events/{eid}/students', headers=admin).status_code == 403


@pytest.mark.parametrize('suffix', ['students', 'summary', 'students/template', 'attendance/export', 'admins'])
def test_admin_cannot_read_another_club(api, monkeypatch, suffix):
    _, admin, _, _, eid, _, second = setup_clubs(api, monkeypatch)
    assert api.get(f'/events/{eid}/clubs/{second}/{suffix}', headers=admin).status_code == 403


def test_booth_checkins_are_independent_and_cross_club_qr_is_rejected(api, monkeypatch):
    _, admin, other_admin, student, eid, first, second = setup_clubs(api, monkeypatch)
    one, two = [f'/events/{eid}/clubs/{cid}' for cid in [first, second]]
    qr = api.get(one + '/qr', headers=student)
    assert qr.status_code == 200, qr.text
    token = qr.json()['token']
    assert api.post(two + '/attendance/scan', headers=other_admin, json={'token': token}).status_code == 403
    checked = api.post(one + '/attendance/scan', headers=admin, json={'token': token})
    assert checked.status_code == 200, checked.text
    assert checked.json()['already_checked_in'] is False
    again = api.post(one + '/attendance/scan', headers=admin, json={'token': token})
    assert again.json()['already_checked_in'] is True
    assert checked.json()['checked_at'] == again.json()['checked_at']
    assert api.get(one + '/me', headers=student).json()['attended'] is True
    assert api.get(two + '/me', headers=student).json()['attended'] is False
    assert api.get(one + '/summary', headers=admin).json()['attended'] == 1
    assert api.get(two + '/summary', headers=other_admin).json()['attended'] == 0


def test_club_search_pagination_and_export_share_filters(api, monkeypatch):
    root, admin, _, _, eid, first, _ = setup_clubs(api, monkeypatch)
    base = f'/events/{eid}/clubs/{first}'
    assert api.post(base + '/students', headers=root,
                    json={'email': '10000005@student.hcmute.edu.vn', 'name': 'Nguyễn Minh An'}).status_code == 201
    result = api.get(base + '/students', headers=admin, params={'search': 'Minh', 'limit': 1})
    assert result.status_code == 200, result.text
    assert result.json()['total'] == 1
    assert result.json()['items'][0]['student_id'] == '10000005'
    result = api.get(base + '/students', headers=admin, params={'offset': 1, 'limit': 1}).json()
    assert result['total'] == 2 and len(result['items']) == 1
    assert result['items'][0]['student_id'] == '10000005'
    exported = api.get(base + '/attendance/export', headers=admin, params={'search': 'Minh'})
    assert exported.status_code == 200
    rows = list(load_workbook(BytesIO(exported.content)).active.values)
    assert len(rows) == 2 and rows[1][0] == '10000005'
    assert api.get(base + '/students', headers=admin, params={'search': '%'}).json()['total'] == 0


def test_import_is_club_scoped_and_atomic_on_invalid_rows(api, monkeypatch):
    _, admin, other_admin, _, eid, first, second = setup_clubs(api, monkeypatch)
    base = f'/events/{eid}/clubs/{first}'
    files = excel([('10000005', 'Năm', ''), ('10000006', 'Sai email', '10000007@student.hcmute.edu.vn')])
    result = api.post(base + '/students/import', headers=admin, files=files)
    assert result.status_code == 200, result.text
    assert result.json()['imported'] == 0 and result.json()['errors']
    assert api.get(base + '/students', headers=admin).json()['total'] == 1
    files = excel([('10000005', 'Năm', ''), ('10000003', 'Trùng', '')])
    result = api.post(base + '/students/import', headers=admin, files=files).json()
    assert result['imported'] == 1 and len(result['duplicates']) == 1
    assert api.get(f'/events/{eid}/clubs/{second}/students', headers=other_admin).json()['total'] == 1


def test_club_and_event_closure_both_prevent_checkin(api, monkeypatch):
    root, admin, _, student, eid, first, _ = setup_clubs(api, monkeypatch)
    base = f'/events/{eid}/clubs/{first}'
    qr = api.get(base + '/qr', headers=student).json()['token']
    assert api.patch(base + '/checkin', headers=admin, json={'checkin_open': False}).status_code == 200
    assert api.get(base + '/qr', headers=student).status_code == 409
    assert api.post(base + '/attendance/scan', headers=admin, json={'token': qr}).status_code == 409
    assert api.patch(base + '/checkin', headers=admin, json={'checkin_open': True}).status_code == 200
    api.put(f'/events/{eid}', headers=root,
            json={'title': 'Đóng', 'starts_at': '2026-10-17T08:00:00+07:00', 'checkin_open': False})
    assert api.post(base + '/attendance/scan', headers=admin, json={'token': qr}).status_code == 409


def test_revoking_club_admin_takes_effect_with_existing_token(api, monkeypatch):
    root, admin, _, _, eid, first, _ = setup_clubs(api, monkeypatch)
    uid = api.get('/auth/me', headers=admin).json()['id']
    base = f'/events/{eid}/clubs/{first}'
    assert api.delete(base + f'/admins/{uid}', headers=root).status_code == 204
    assert api.get(base + '/students', headers=admin).status_code == 403
    assert api.patch(base + '/checkin', headers=admin, json={'checkin_open': False}).status_code == 403


def test_event_summary_is_superadmin_only_and_counts_booth_visits(api, monkeypatch):
    root, admin, other_admin, student, eid, first, second = setup_clubs(api, monkeypatch)
    for cid, manager in [(first, admin), (second, other_admin)]:
        base = f'/events/{eid}/clubs/{cid}'
        qr = api.get(base + '/qr', headers=student).json()['token']
        assert api.post(base + '/attendance/scan', headers=manager, json={'token': qr}).status_code == 200
    response = api.get(f'/events/{eid}/summary', headers=root)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result['registered'], result['attended'], result['clubs'], result['unique_attendees']) == (2, 2, 2, 1)
    assert api.get(f'/events/{eid}/summary', headers=admin).status_code == 403


def test_student_cannot_manage_club_or_see_roster(api, monkeypatch):
    _, _, _, student, eid, first, _ = setup_clubs(api, monkeypatch)
    base = f'/events/{eid}/clubs/{first}'
    assert api.get(base + '/students', headers=student).status_code == 403
    assert api.get(base + '/summary', headers=student).status_code == 403
    assert api.patch(base + '/checkin', headers=student, json={'checkin_open': False}).status_code == 403
    assert api.post(f'/events/{eid}/clubs', headers=student, json={'name': 'No'}).status_code == 403


def test_cross_club_writes_and_role_assignment_are_denied(api, monkeypatch):
    _, admin, _, _, eid, _, second = setup_clubs(api, monkeypatch)
    base = f'/events/{eid}/clubs/{second}'
    person = {'email': '10000005@student.hcmute.edu.vn', 'name': 'Không được thêm'}
    assert api.post(base + '/students', headers=admin, json=person).status_code == 403
    assert api.post(base + '/students/import', headers=admin, files=excel([('10000005', 'Năm', '')])).status_code == 403
    assert api.patch(base + '/checkin', headers=admin, json={'checkin_open': False}).status_code == 403
    assert api.post(base + '/admins', headers=admin, json=person).status_code == 403


def test_qr_must_have_club_purpose_valid_lifetime_and_matching_event(api, monkeypatch):
    from app import main as m
    root, admin, _, student, eid, first, _ = setup_clubs(api, monkeypatch)
    base = f'/events/{eid}/clubs/{first}'
    uid = api.get('/auth/me', headers=student).json()['id']
    for kind, seconds, expected in [('checkin', 120, 401), ('club_checkin', -1, 401)]:
        token = m.token({'sub': str(uid), 'kind': kind, 'event_id': eid, 'club_id': first}, seconds)
        assert api.post(base + '/attendance/scan', headers=admin, json={'token': token}).status_code == expected
    token = api.get(base + '/qr', headers=student).json()['token']
    assert api.get('/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401
    assert api.post(base + '/attendance/scan', headers=admin, json={'token': token[:-8] + 'tampered'}).status_code == 401
    other_event = event(api, root, 'Other event')
    assert api.get(f'/events/{other_event}/clubs/{first}/students', headers=root).status_code == 404


def test_empty_club_summary_and_invalid_or_duplicate_names(api, monkeypatch):
    root = auth(api, monkeypatch)
    eid = event(api, root)
    assert api.post(f'/events/{eid}/clubs', headers=root, json={'name': '  '}).status_code == 422
    cid = club(api, root, eid)
    assert api.post(f'/events/{eid}/clubs', headers=root, json={'name': 'RTIC'}).status_code == 409
    data = api.get(f'/events/{eid}/clubs/{cid}/summary', headers=root).json()
    assert (data['registered'], data['attended'], data['rate'], data['recent']) == (0, 0, 0, [])


def test_legacy_event_admin_cannot_bypass_club_isolation(api, monkeypatch):
    root, admin, _, _, eid, _, _ = setup_clubs(api, monkeypatch)
    assert api.post(f'/events/{eid}/admins', headers=root,
                    json={'email': '10000002@student.hcmute.edu.vn', 'name': 'Legacy admin'}).status_code == 201
    for suffix in ['students', 'students/template', 'attendance/export']:
        assert api.get(f'/events/{eid}/{suffix}', headers=admin).status_code == 403
