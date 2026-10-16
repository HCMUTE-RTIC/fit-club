"""Real browser journeys against the isolated API; Google is the only external boundary.

Run with: uv run --with-requirements requirements.txt --with playwright python -m pytest tests/test_browser.py
Install Chromium once with `uv run --with playwright playwright install chromium`.
"""
import json
import base64
import os
from pathlib import Path
import socket
from threading import Thread
import time

import pytest
import uvicorn

pw = pytest.importorskip('playwright.sync_api')
from test_api import api, auth, event
from test_clubs import setup_clubs, club
from app import main as m


@pytest.fixture
def browser(api):
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(m.app, log_level='error'))
    thread = Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started, 'Local browser test server did not start'
    try:
        with pw.sync_playwright() as playwright:
            options = {'headless': True}
            executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
            if executable:
                options['executable_path'] = executable
            chromium = playwright.chromium.launch(**options)
            yield chromium, f'http://127.0.0.1:{port}'
            chromium.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


def signed_page(browser, headers, width=1440):
    chromium, base_url = browser
    page = chromium.new_page(viewport={'width': width, 'height': 1000})
    page.route('https://accounts.google.com/**', lambda route: route.fulfill(body=''))
    token = headers['Authorization'][7:]
    page.add_init_script(f"sessionStorage.setItem('fit-token', {json.dumps(token)})")
    page.goto(base_url)
    page.wait_for_load_state('networkidle')
    return page


def screenshot(page, tmp_path, name):
    folder = Path(os.environ.get('FITCLUB_PREVIEW_DIR', str(tmp_path)))
    folder.mkdir(parents=True, exist_ok=True)
    page.locator('img').evaluate_all("""async images => {
        await Promise.all(images.map(image => {
            image.loading = 'eager';
            return image.decode().catch(() => {});
        }));
    }""")
    page.evaluate('window.scrollTo(0, 0)')
    page.screenshot(path=str(folder / name), full_page=True)


def test_student_navigation_and_mobile_ticket(api, monkeypatch, browser, tmp_path):
    _, _, _, student, _, _, _ = setup_clubs(api, monkeypatch)
    student = auth(api, monkeypatch, '10000003', name='Nguyễn Minh Anh')
    page = signed_page(browser, student, 375)
    try:
        pw.expect(page.locator('#workspace')).to_be_visible()
        pw.expect(page.get_by_role('button', name='Vé của tôi', exact=True)).to_be_visible()
        pw.expect(page.get_by_role('button', name='Người tham gia', exact=True)).to_be_hidden()
        pw.expect(page.get_by_role('button', name='Quét điểm danh', exact=True)).to_be_hidden()
        page.get_by_role('button', name='Vé của tôi', exact=True).click()
        page.get_by_role('button', name='Hiển thị mã QR', exact=True).click()
        pw.expect(page.get_by_alt_text('QR điểm danh cá nhân')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        screenshot(page, tmp_path, 'student-mobile.png')
    finally:
        page.close()


def test_manager_search_and_navigation(api, monkeypatch, browser, tmp_path):
    _, admin, _, _, eid, cid, _ = setup_clubs(api, monkeypatch)
    admin = auth(api, monkeypatch, '10000002', name='Lê Hoàng Nam')
    base = f'/events/{eid}/clubs/{cid}'
    names = ['Trần Gia Bảo', 'Nguyễn Thảo Vy', 'Lê Minh Khang', 'Phạm Khánh Linh', 'Võ Đức Huy', 'Bùi Ngọc Anh']
    for index in range(51):
        response = api.post(base + '/students', headers=admin,
                            json={'email': f'{21000000 + index}@student.hcmute.edu.vn', 'name': names[index % len(names)]})
        assert response.status_code == 201
        if index < 32:
            token = m.token({'sub': str(response.json()['id']), 'kind': 'club_checkin', 'event_id': eid, 'club_id': cid}, 120)
            assert api.post(base + '/attendance/scan', headers=admin, json={'token': token}).status_code == 200
    page = signed_page(browser, admin)
    try:
        pw.expect(page.locator('#workspace')).to_be_visible()
        page.get_by_role('button', name='Người tham gia', exact=True).click()
        pw.expect(page.locator('#students tr')).to_have_count(25)
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.get_by_role('button', name='Tổng quan', exact=True).click()
        pw.expect(page.locator('#stat-registered')).to_have_text('52')
        assert page.evaluate('window.scrollY') == 0, 'Navigation should open the new view from its beginning'
        page.get_by_role('button', name='Người tham gia', exact=True).click()
        page.get_by_role('searchbox', name='Tìm người tham gia').fill('10000003')
        page.get_by_role('button', name='Tìm kiếm', exact=True).click()
        pw.expect(page.locator('#students tr')).to_have_count(1)
        pw.expect(page.locator('#students')).to_contain_text('10000003')
        page.get_by_role('button', name='Tổng quan', exact=True).click()
        pw.expect(page.locator('#stat-registered')).to_have_text('52')
        pw.expect(page.locator('#stat-attended')).to_have_text('32')
        screenshot(page, tmp_path, 'manager-desktop.png')
    finally:
        page.close()


def test_ticket_refreshes_expired_qr_without_manual_action(api, monkeypatch, browser):
    monkeypatch.setattr(m.settings, 'qr_seconds', 3)
    _, _, _, student, _, _, _ = setup_clubs(api, monkeypatch)
    page = signed_page(browser, student)
    try:
        page.get_by_role('button', name='Vé của tôi', exact=True).click()
        page.get_by_role('button', name='Hiển thị mã QR', exact=True).click()
        qr = page.get_by_alt_text('QR điểm danh cá nhân')
        pw.expect(qr).to_be_visible()
        first = qr.get_attribute('src')
        pw.expect(qr).not_to_have_attribute('src', first, timeout=8000)
    finally:
        page.close()


def test_qr_image_upload_records_attendance_only_at_selected_booth(api, monkeypatch, browser, tmp_path):
    _, admin, other_admin, student, eid, first, second = setup_clubs(api, monkeypatch)
    qr = api.get(f'/events/{eid}/clubs/{first}/qr', headers=student).json()
    qr_file = tmp_path / 'ticket.png'
    qr_file.write_bytes(base64.b64decode(qr['image_data_url'].split(',')[1]))
    page = signed_page(browser, admin)
    try:
        page.get_by_role('button', name='Quét điểm danh', exact=True).click()
        page.locator('#qr-file').set_input_files(str(qr_file))
        pw.expect(page.locator('#scan-result')).to_contain_text('Điểm danh thành công')
        assert api.get(f'/events/{eid}/clubs/{first}/summary', headers=admin).json()['attended'] == 1
        assert api.get(f'/events/{eid}/clubs/{second}/summary', headers=other_admin).json()['attended'] == 0
    finally:
        page.close()


def test_superadmin_can_create_club_and_assign_club_admin(api, monkeypatch, browser):
    root, _, _, _, _, _, _ = setup_clubs(api, monkeypatch)
    page = signed_page(browser, root, 375)
    try:
        page.get_by_role('button', name='Thêm CLB', exact=True).first.click()
        dialog = page.locator('#club-dialog')
        dialog.get_by_label('Tên câu lạc bộ').fill('CLB ATTT')
        dialog.get_by_role('button', name='Tạo gian hàng', exact=True).click()
        pw.expect(dialog).not_to_be_visible()
        pw.expect(page.locator('#clubs')).to_have_value('3')
        page.get_by_role('button', name='Thêm admin', exact=True).click()
        person = page.locator('#person-dialog')
        person.get_by_label('Họ và tên').fill('Admin ATTT')
        person.get_by_label('Email Google').fill('10000009@student.hcmute.edu.vn')
        person.get_by_role('button', name='Thêm tài khoản', exact=True).click()
        pw.expect(page.locator('#admins')).to_contain_text('Admin ATTT')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    finally:
        page.close()


def test_student_club_branding_changes_with_selected_ticket(api, monkeypatch, browser):
    _, _, _, student, _, first, second = setup_clubs(api, monkeypatch)
    page = signed_page(browser, student, 375)
    try:
        page.get_by_role('button', name='Vé của tôi', exact=True).click()
        page.locator('#clubs').select_option(str(second))
        logo = page.locator('#ticket-club-brand img')
        pw.expect(logo).to_have_attribute('alt', 'Logo DSC')
        page.wait_for_function("document.querySelector('#ticket-club-brand img')?.naturalWidth > 0")
        page.locator('#clubs').select_option(str(first))
        pw.expect(logo).to_have_attribute('alt', 'Logo RTIC')
        page.wait_for_function("document.querySelector('#ticket-club-brand img')?.naturalWidth > 0")
        pw.expect(page.locator('#ticket-club-name')).to_have_text('RTIC')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    finally:
        page.close()


def test_superadmin_grants_gmail_access_by_email_without_event(api, monkeypatch, browser):
    root = auth(api, monkeypatch)
    page = signed_page(browser, root)
    try:
        page.locator('#grant-access').click()
        dialog = page.locator('#person-dialog')
        dialog.get_by_label('Email Google').fill('staff@gmail.com')
        dialog.get_by_label('Vai trò').select_option('superadmin')
        dialog.get_by_role('button', name='Thêm tài khoản', exact=True).click()
        pw.expect(dialog).not_to_be_visible()
        users = api.get('/superadmins', headers=root).json()['users']
        assert any(user['email'] == 'staff@gmail.com' for user in users)
    finally:
        page.close()


@pytest.mark.parametrize('width', [360, 390, 768, 1024, 1440])
def test_new_student_discovers_and_joins_club_on_mobile(api, monkeypatch, browser, width, tmp_path):
    root = auth(api, monkeypatch)
    eid = event(api, root, 'FIT Club Day')
    cid = club(api, root, eid, 'RTIC', opened=False)
    for name in ['ISC', 'SBG', 'DSC', 'SV5T']:
        club(api, root, eid, name, opened=False)
    student = auth(api, monkeypatch, '10000003', name='Nguyễn Minh Anh')
    page = signed_page(browser, student, width)
    try:
        pw.expect(page.locator('#event-title')).to_have_text('FIT Club Day')
        pw.expect(page.locator('#event-title')).to_be_visible()
        pw.expect(page.locator('.student-club-card')).to_have_count(5)
        if width < 768:
            first_join = page.get_by_role('button', name='Tham gia DSC', exact=True)
            first_bounds = first_join.bounding_box()
            nav_bounds = page.get_by_role('navigation', name='Điều hướng chính').bounding_box()
            assert first_bounds['y'] + first_bounds['height'] <= nav_bounds['y'], 'The first join action must be reachable before scrolling'
        join = page.get_by_role('button', name='Tham gia RTIC', exact=True)
        pw.expect(join).to_be_visible()
        assert join.bounding_box()['height'] >= 44
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if width == 390:
            screenshot(page, tmp_path, 'student-overview-mobile.png')
        elif width == 1440:
            screenshot(page, tmp_path, 'student-overview-desktop.png')
        join.click()
        pw.expect(page.locator('#ticket-status')).to_contain_text('Đã tham gia')
        assert api.get(f'/events/{eid}/clubs/{cid}/students', headers=root).json()['total'] == 1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if width == 390:
            screenshot(page, tmp_path, 'student-registration-mobile.png')
        page.get_by_role('button', name='Tài khoản', exact=True).click()
        pw.expect(page.locator('#account-email')).to_have_text('10000003@student.hcmute.edu.vn')
    finally:
        page.close()


def test_student_page_updates_when_organizer_opens_event(api, monkeypatch, browser):
    root = auth(api, monkeypatch)
    eid = event(api, root, 'FIT Club Day')
    body = {'title': 'FIT Club Day', 'starts_at': '2026-10-17T08:00:00+07:00', 'checkin_open': False}
    api.put(f'/events/{eid}', headers=root, json=body)
    student = auth(api, monkeypatch, '10000003')
    page = signed_page(browser, student, 390)
    try:
        pw.expect(page.locator('#empty-state')).to_be_visible()
        pw.expect(page.locator('#events')).to_be_disabled()
        body['checkin_open'] = True
        assert api.put(f'/events/{eid}', headers=root, json=body).status_code == 200
        pw.expect(page.locator('#event-title')).to_be_visible(timeout=15000)
        cid = club(api, root, eid, 'RTIC', opened=False)
        join = page.get_by_role('button', name='Tham gia RTIC', exact=True)
        pw.expect(join).to_be_visible(timeout=15000)
        join.click()
        pw.expect(page.locator('#ticket-status')).to_contain_text('Đã tham gia')
        assert api.get(f'/events/{eid}/clubs/{cid}/students', headers=root).json()['total'] == 1
    finally:
        page.close()


def test_manager_can_add_participant_and_open_scanner_on_phone(api, monkeypatch, browser, tmp_path):
    _, admin, _, _, eid, cid, _ = setup_clubs(api, monkeypatch)
    page = signed_page(browser, admin, 375)
    try:
        screenshot(page, tmp_path, 'manager-mobile.png')
        page.get_by_role('button', name='Người tham gia', exact=True).click()
        page.get_by_role('button', name='Thêm người', exact=True).click()
        form = page.locator('#person-dialog')
        form.get_by_label('Họ và tên').fill('Nguyễn Thị Minh Anh - Sinh viên khoa Công nghệ Thông tin')
        form.get_by_label('Email Google').fill('10000005@student.hcmute.edu.vn')
        form.get_by_role('button', name='Thêm tài khoản', exact=True).click()
        pw.expect(form).not_to_be_visible()
        pw.expect(page.locator('#students tr')).to_have_count(2)
        assert page.locator('#students .person-cell').first.bounding_box()['width'] >= 220, 'Names and emails must remain readable on a phone'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        screenshot(page, tmp_path, 'participants-mobile.png')
        page.get_by_role('button', name='Quét điểm danh', exact=True).click()
        pw.expect(page.get_by_role('button', name='Bật camera', exact=True)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert api.get(f'/events/{eid}/clubs/{cid}/students', headers=admin).json()['total'] == 2
    finally:
        page.close()
