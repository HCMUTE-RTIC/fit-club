"""Club booths inside an event, with independent rosters, staff and attendance.

The legacy app registers this extension after defining its shared authentication
and Excel helpers, before lifespan creates tables. Existing event data is untouched.
"""
import base64
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator
import qrcode
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import main as core


class Club(core.Base):
    __tablename__ = 'event_clubs'
    __table_args__ = (UniqueConstraint('event_id', 'name'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(default='')
    checkin_open: Mapped[bool] = mapped_column(Boolean, default=False)


class ClubAdmin(core.Base):
    __tablename__ = 'club_admins'
    club_id: Mapped[int] = mapped_column(ForeignKey('event_clubs.id'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)


class ClubRegistration(core.Base):
    __tablename__ = 'club_registrations'
    club_id: Mapped[int] = mapped_column(ForeignKey('event_clubs.id'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ClubAttendance(core.Base):
    __tablename__ = 'club_attendance'
    __table_args__ = (UniqueConstraint('club_id', 'user_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey('event_clubs.id'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    checked_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


router = APIRouter(tags=['Gian hàng CLB'])


@router.get('/events/discover')
def discover_events(user=Depends(core.current), session: Session = Depends(core.db)):
    """Expose open-event metadata, without granting access to any participant list."""
    query = select(core.Event).where(core.Event.checkin_open.is_(True)).order_by(core.Event.starts_at.desc())
    return [core.event_data(item) for item in session.scalars(query)]


def get_club(session, event_id, club_id):
    core.get_event(session, event_id)
    item = session.get(Club, club_id)
    if not item or item.event_id != event_id:
        raise HTTPException(404, 'Không tìm thấy CLB trong sự kiện này')
    return item


def can_manage(session, user, club_id):
    return core.is_super(user) or session.get(ClubAdmin, (club_id, user.id)) is not None


def manage_club(session, user, event_id, club_id):
    item = get_club(session, event_id, club_id)
    if not can_manage(session, user, club_id):
        raise HTTPException(403, 'Bạn không phải admin của CLB này')
    return item


def club_data(item):
    return {'id': item.id, 'event_id': item.event_id, 'name': item.name,
            'description': item.description, 'checkin_open': item.checkin_open}


class ClubInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=5000)
    checkin_open: bool = False

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError('Tên CLB không được trống')
        return value.strip()


class CheckinState(BaseModel):
    checkin_open: bool


@router.post('/events/{event_id}/clubs', status_code=201)
def create_club(event_id: int, body: ClubInput, user=Depends(core.superuser), session: Session = Depends(core.db)):
    core.get_event(session, event_id)
    item = Club(event_id=event_id, **body.model_dump())
    session.add(item)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, 'Tên CLB đã có trong sự kiện')
    return club_data(item)


@router.get('/events/{event_id}/clubs')
def list_clubs(event_id: int, user=Depends(core.current), session: Session = Depends(core.db)):
    core.get_event(session, event_id)
    query = select(Club).where(Club.event_id == event_id).order_by(Club.name)
    if not core.is_super(user):
        query = query.where(or_(Club.id.in_(select(ClubAdmin.club_id).where(ClubAdmin.user_id == user.id)),
                                Club.id.in_(select(ClubRegistration.club_id).where(ClubRegistration.user_id == user.id))))
    return [{**club_data(item), 'can_manage': can_manage(session, user, item.id),
             'registered': session.get(ClubRegistration, (item.id, user.id)) is not None}
            for item in session.scalars(query)]


@router.get('/events/{event_id}/clubs/discover')
def discover_clubs(event_id: int, user=Depends(core.current), session: Session = Depends(core.db)):
    if not core.get_event(session, event_id).checkin_open:
        return []
    clubs = session.scalars(select(Club).where(Club.event_id == event_id).order_by(Club.name))
    result = []
    for item in clubs:
        attended = session.scalar(select(ClubAttendance.id).where(ClubAttendance.club_id == item.id, ClubAttendance.user_id == user.id)) is not None
        result.append({**club_data(item), 'can_manage': can_manage(session, user, item.id),
                       'registered': session.get(ClubRegistration, (item.id, user.id)) is not None,
                       'attended': attended})
    return result


@router.post('/events/{event_id}/clubs/{club_id}/join')
def join_club(event_id: int, club_id: int, user=Depends(core.current), session: Session = Depends(core.db)):
    item = get_club(session, event_id, club_id)
    if not core.get_event(session, event_id).checkin_open:
        raise HTTPException(409, 'Sự kiện đang đóng đăng ký tham gia')
    core.student_email(user.email)
    register_student(session, event_id, club_id, user.email, user.name)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if not session.get(ClubRegistration, (club_id, user.id)):
            raise HTTPException(409, 'Có thay đổi đồng thời; hãy thử tham gia lại')
    return {**core.profile(user), 'registered': True, 'club': club_data(item)}


@router.patch('/events/{event_id}/clubs/{club_id}/checkin')
def set_checkin(event_id: int, club_id: int, body: CheckinState, user=Depends(core.current), session: Session = Depends(core.db)):
    item = manage_club(session, user, event_id, club_id)
    item.checkin_open = body.checkin_open
    session.commit()
    return club_data(item)


@router.post('/events/{event_id}/clubs/{club_id}/admins', status_code=201)
def add_admin(event_id: int, club_id: int, body: core.Person, user=Depends(core.superuser), session: Session = Depends(core.db)):
    get_club(session, event_id, club_id)
    person = core.ensure_user(session, body.email, body.name, allow_external=True)
    if session.get(ClubAdmin, (club_id, person.id)):
        raise HTTPException(409, 'Admin đã được gán cho CLB')
    session.add(ClubAdmin(club_id=club_id, user_id=person.id))
    session.commit()
    return core.profile(person)


@router.get('/events/{event_id}/clubs/{club_id}/admins')
def admins(event_id: int, club_id: int, user=Depends(core.current), session: Session = Depends(core.db)):
    manage_club(session, user, event_id, club_id)
    return [core.profile(person) for person in session.scalars(select(core.User).join(ClubAdmin).where(ClubAdmin.club_id == club_id))]


@router.delete('/events/{event_id}/clubs/{club_id}/admins/{user_id}', status_code=204)
def remove_admin(event_id: int, club_id: int, user_id: int, user=Depends(core.superuser), session: Session = Depends(core.db)):
    get_club(session, event_id, club_id)
    record = session.get(ClubAdmin, (club_id, user_id))
    if not record:
        raise HTTPException(404, 'Không tìm thấy admin CLB')
    session.delete(record)
    session.commit()


def register_student(session, event_id, club_id, email, name):
    person = core.ensure_user(session, email, name)
    if session.get(ClubRegistration, (club_id, person.id)):
        return person, False
    if not session.get(core.Registration, (event_id, person.id)):
        session.add(core.Registration(event_id=event_id, user_id=person.id))
    session.add(ClubRegistration(club_id=club_id, user_id=person.id))
    return person, True


@router.post('/events/{event_id}/clubs/{club_id}/students', status_code=201)
def add_student(event_id: int, club_id: int, body: core.Person, user=Depends(core.current), session: Session = Depends(core.db)):
    manage_club(session, user, event_id, club_id)
    person, added = register_student(session, event_id, club_id, body.email, body.name)
    if not added:
        raise HTTPException(409, 'Sinh viên đã có trong danh sách CLB')
    session.commit()
    return core.profile(person)


def student_query(club_id, search='', attended=None):
    query = (select(core.User, ClubAttendance).join(ClubRegistration, ClubRegistration.user_id == core.User.id)
             .outerjoin(ClubAttendance, (ClubAttendance.user_id == core.User.id) & (ClubAttendance.club_id == club_id))
             .where(ClubRegistration.club_id == club_id))
    if search.strip():
        search = search.strip()
        query = query.where(or_(core.User.student_id.contains(search, autoescape=True),
                                core.User.name.icontains(search, autoescape=True),
                                core.User.email.icontains(search, autoescape=True)))
    if attended is not None:
        query = query.where(ClubAttendance.id.is_not(None) if attended else ClubAttendance.id.is_(None))
    return query.order_by(core.User.student_id)


@router.get('/events/{event_id}/clubs/{club_id}/students')
def students(event_id: int, club_id: int, search: str = Query('', max_length=200), attended: bool | None = None,
             offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=500),
             user=Depends(core.current), session: Session = Depends(core.db)):
    manage_club(session, user, event_id, club_id)
    query = student_query(club_id, search, attended)
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return {'items': [core.attendance_data(person, record) for person, record in session.execute(query.offset(offset).limit(limit))],
            'total': total, 'offset': offset, 'limit': limit}


@router.get('/events/{event_id}/clubs/{club_id}/students/template')
def template(event_id: int, club_id: int, user=Depends(core.current), session: Session = Depends(core.db)):
    manage_club(session, user, event_id, club_id)
    return core.workbook_response(['student_id', 'full_name', 'email'], [], 'club-students-template.xlsx')


@router.post('/events/{event_id}/clubs/{club_id}/students/import')
def import_students(event_id: int, club_id: int, file: UploadFile = File(...), user=Depends(core.current), session: Session = Depends(core.db)):
    manage_club(session, user, event_id, club_id)
    content = file.file.read(5 * 1024 * 1024 + 1)
    valid, errors, duplicates = core.parse_student_excel(content)
    if errors:
        return {'imported': 0, 'errors': errors, 'duplicates': duplicates}
    imported = 0
    for row_number, email, name in valid:
        person, added = register_student(session, event_id, club_id, email, name)
        if added:
            imported += 1
        else:
            duplicates.append({'row': row_number, 'student_id': person.student_id, 'reason': 'Đã có trong CLB'})
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, 'Có thay đổi đồng thời; hãy tải lại file')
    return {'imported': imported, 'errors': [], 'duplicates': duplicates}


@router.get('/events/{event_id}/clubs/{club_id}/attendance/export')
def export(event_id: int, club_id: int, search: str = Query('', max_length=200), attended: bool | None = None,
           user=Depends(core.current), session: Session = Depends(core.db)):
    manage_club(session, user, event_id, club_id)
    rows = []
    for person, record in session.execute(student_query(club_id, search, attended)):
        scanner = session.get(core.User, record.checked_by) if record else None
        rows.append([person.student_id, person.name, person.email, 'Có mặt' if record else 'Chưa điểm danh',
                     core.attendance_data(person, record)['checked_at'].isoformat() if record else '', scanner.email if scanner else ''])
    return core.workbook_response(['student_id', 'full_name', 'email', 'status', 'checked_at_utc', 'checked_by'], rows, f'club-{club_id}-attendance.xlsx')


def counts(session, club_id):
    registered = session.scalar(select(func.count()).select_from(ClubRegistration).where(ClubRegistration.club_id == club_id))
    attended = session.scalar(select(func.count()).select_from(ClubAttendance).where(ClubAttendance.club_id == club_id))
    return {'registered': registered, 'attended': attended, 'pending': max(0, registered - attended),
            'rate': round(attended * 100 / registered, 1) if registered else 0}


@router.get('/events/{event_id}/clubs/{club_id}/summary')
def summary(event_id: int, club_id: int, user=Depends(core.current), session: Session = Depends(core.db)):
    item = manage_club(session, user, event_id, club_id)
    recent = session.execute(select(core.User, ClubAttendance).join(ClubAttendance, ClubAttendance.user_id == core.User.id)
                             .where(ClubAttendance.club_id == club_id).order_by(ClubAttendance.checked_at.desc(), ClubAttendance.id.desc()).limit(6))
    return {**club_data(item), **counts(session, club_id),
            'recent': [core.attendance_data(person, record) for person, record in recent]}


@router.get('/events/{event_id}/summary')
def event_summary(event_id: int, user=Depends(core.superuser), session: Session = Depends(core.db)):
    core.get_event(session, event_id)
    clubs = list(session.scalars(select(Club).where(Club.event_id == event_id).order_by(Club.name)))
    rows = [{**club_data(item), **counts(session, item.id)} for item in clubs]
    registered, attended = sum(row['registered'] for row in rows), sum(row['attended'] for row in rows)
    unique = session.scalar(select(func.count(func.distinct(ClubAttendance.user_id))).join(Club, Club.id == ClubAttendance.club_id).where(Club.event_id == event_id))
    return {'registered': registered, 'attended': attended, 'pending': max(0, registered - attended),
            'rate': round(attended * 100 / registered, 1) if registered else 0, 'clubs': len(rows),
            'unique_attendees': unique, 'club_summaries': rows, 'recent': []}


@router.get('/events/{event_id}/clubs/{club_id}/me')
def my_status(event_id: int, club_id: int, user=Depends(core.current), session: Session = Depends(core.db)):
    item = get_club(session, event_id, club_id)
    registered = session.get(ClubRegistration, (club_id, user.id)) is not None
    if not registered and not can_manage(session, user, club_id) and not core.get_event(session, event_id).checkin_open:
        raise HTTPException(403, 'Bạn chưa được thêm vào CLB này')
    attendance = session.scalar(select(ClubAttendance).where(ClubAttendance.club_id == club_id, ClubAttendance.user_id == user.id))
    return {**core.attendance_data(user, attendance), 'registered': registered, 'club': club_data(item)}


def require_open(session, item):
    if not core.get_event(session, item.event_id).checkin_open:
        raise HTTPException(409, 'Sự kiện đang đóng điểm danh; liên hệ ban tổ chức')
    if not item.checkin_open:
        raise HTTPException(409, 'Gian hàng CLB đang đóng điểm danh')


@router.get('/events/{event_id}/clubs/{club_id}/qr')
def my_qr(event_id: int, club_id: int, user=Depends(core.current), session: Session = Depends(core.db)):
    item = get_club(session, event_id, club_id)
    if not session.get(ClubRegistration, (club_id, user.id)):
        raise HTTPException(403, 'Bạn chưa có tên trong danh sách CLB này')
    require_open(session, item)
    value = core.token({'sub': str(user.id), 'kind': 'club_checkin', 'event_id': event_id, 'club_id': club_id}, core.settings.qr_seconds)
    buffer = BytesIO()
    qrcode.make(value).save(buffer, format='PNG')
    return {'token': value, 'expires_in': core.settings.qr_seconds,
            'image_data_url': 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()}


@router.post('/events/{event_id}/clubs/{club_id}/attendance/scan')
def scan(event_id: int, club_id: int, body: core.Scan, user=Depends(core.current), session: Session = Depends(core.db)):
    item = manage_club(session, user, event_id, club_id)
    require_open(session, item)
    claims = core.decode(body.token, 'club_checkin')
    if claims.get('event_id') != event_id or claims.get('club_id') != club_id:
        raise HTTPException(403, 'QR thuộc sự kiện hoặc gian hàng CLB khác')
    try:
        uid = int(claims['sub'])
    except (ValueError, TypeError):
        raise HTTPException(401, 'QR không hợp lệ')
    if not session.get(ClubRegistration, (club_id, uid)):
        raise HTTPException(403, 'Sinh viên không thuộc danh sách CLB này')
    person = session.get(core.User, uid)
    existing = session.scalar(select(ClubAttendance).where(ClubAttendance.club_id == club_id, ClubAttendance.user_id == uid))
    if existing:
        return {'already_checked_in': True, **core.attendance_data(person, existing)}
    record = ClubAttendance(club_id=club_id, user_id=uid, checked_by=user.id)
    session.add(record)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(select(ClubAttendance).where(ClubAttendance.club_id == club_id, ClubAttendance.user_id == uid))
        if not existing:
            raise HTTPException(409, 'Xung đột ghi dữ liệu; hãy quét lại')
        return {'already_checked_in': True, **core.attendance_data(person, existing)}
    return {'already_checked_in': False, **core.attendance_data(person, record)}
