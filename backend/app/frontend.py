from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def register_frontend(app):
    root = Path(__file__).resolve().parents[2] / 'frontend'
    app.mount('/ui', StaticFiles(directory=root), name='frontend')

    project_root = Path(__file__).resolve().parents[2]

    @app.get('/', include_in_schema=False)
    def index():
        return FileResponse(root / 'index.html', headers={'Cache-Control': 'no-store'})

    @app.get('/landingpage', include_in_schema=False)
    @app.get('/landingpage.html', include_in_schema=False)
    def landing_page():
        return FileResponse(project_root / 'landingpage.html', headers={'Cache-Control': 'no-store'})

    @app.get('/auth/config')
    def config():
        from .main import settings
        return {'client_id': settings.google_client_id, 'student_email_only': settings.student_email_only}
