"""Public test UI remains usable without exposing backend configuration/files."""
from test_api import api
from app import main as m


def test_public_login_shell_and_static_assets(api):
    response = api.get('/')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert 'id="google-button"' in response.text
    assert 'id="workspace" hidden' in response.text
    for path, content_type in [('/ui/app.js', 'javascript'), ('/ui/style.css', 'text/css')]:
        asset = api.get(path)
        assert asset.status_code == 200
        assert content_type in asset.headers['content-type']


def test_public_config_reports_active_policy_without_secrets(api, monkeypatch):
    monkeypatch.setattr(m.settings, 'google_client_id', 'public-test.apps.googleusercontent.com')
    for policy in (True, False):
        monkeypatch.setattr(m.settings, 'student_email_only', policy)
        response = api.get('/auth/config')
        assert response.status_code == 200
        assert response.json() == {'client_id': 'public-test.apps.googleusercontent.com', 'student_email_only': policy}


def test_static_mount_cannot_expose_backend_files(api):
    for path in ['/ui/.env', '/ui/..%2fbackend/.env', '/ui/%2e%2e/backend/app/main.py', '/ui/fitclub.db']:
        assert api.get(path).status_code == 404
