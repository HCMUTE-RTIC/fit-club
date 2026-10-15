"""Student and anonymous actor acceptance/security tests, isolated SQLite only."""
import base64
import json
import pytest
from test_api import api, auth, event, excel, setup_event
from app import main as m

@pytest.mark.parametrize('override', [
    {'email':'10000003@gmail.com'}, {'hd':'hcmute.edu.vn'}, {'hd':None},
    {'email_verified':False}, {'email_verified':'true'}, {'email_verified':None},
    {'name':None}, {'name':'   '}, {'sub':None}, {'sub':''},
    {'email':'10000003@student.hcmute.edu.vn.evil.com'},
    {'email':'notnumber@student.hcmute.edu.vn'},
])
def test_student_google_rejects_invalid_identity(api, monkeypatch, override):
    claims={'sub':'actor-student','email':'10000003@student.hcmute.edu.vn','hd':m.DOMAIN,'email_verified':True,'name':'Student',**override}
    monkeypatch.setattr(m,'verify_google',lambda _:claims)
    assert api.post('/auth/google',json={'credential':'test-credential'}).status_code in (403,422)

@pytest.mark.parametrize('method,path,body', [
    ('get','/auth/me',None), ('get','/events',None), ('get','/superadmins',None),
    ('post','/events',{'title':'Denied','starts_at':'2026-10-17T08:00:00+07:00'}),
    ('get','/events/1/qr',None), ('get','/events/1/students',None),
    ('get','/events/1/attendance/export',None),
])
def test_anonymous_denied(api,method,path,body):
    assert api.request(method,path,json=body).status_code in (401,403)

@pytest.mark.parametrize('method,suffix,body', [
    ('get','students',None), ('get','students/template',None), ('get','attendance/export',None),
    ('get','admins',None), ('post','students',{'email':'10000007@student.hcmute.edu.vn','name':'Other'}),
    ('post','admins',{'email':'10000003@student.hcmute.edu.vn','name':'Me'}),
    ('delete','admins/1',None), ('post','attendance/scan',{'token':'test-token-12345'}),
])
def test_student_denial_matrix(api,monkeypatch,method,suffix,body):
    _,_,student,eid,_=setup_event(api,monkeypatch)
    response=api.request(method,f'/events/{eid}/{suffix}',headers=student,json=body)
    assert response.status_code==403,response.text


def test_student_import_and_superadmin_and_event_mutation_denied(api,monkeypatch):
    _,_,student,eid,_=setup_event(api,monkeypatch)
    assert api.post(f'/events/{eid}/students/import',headers=student,files=excel([('10000007','Other','')])).status_code==403
    for method,path,body in [('get','/superadmins',None),('post','/superadmins',{'email':'10000003@student.hcmute.edu.vn','name':'Me'}),('delete','/superadmins/1',None),('post','/events',{'title':'No','starts_at':'2026-10-17T08:00:00+07:00'}),('put',f'/events/{eid}',{'title':'No','starts_at':'2026-10-17T08:00:00+07:00'})]:
        assert api.request(method,path,headers=student,json=body).status_code==403


def test_student_qr_is_self_scoped_and_event_visibility(api,monkeypatch):
    root,admin,student,eid,other=setup_event(api,monkeypatch)
    uid=api.get('/auth/me',headers=student).json()['id']
    assert [r['id'] for r in api.get('/events',headers=student).json()]==[eid]
    assert api.get(f'/events/{other}/qr',headers=student).status_code==403
    qr=api.get(f'/events/{eid}/qr',headers=student,params={'user_id':1,'student_id':'10000001'}).json()
    claims=m.decode(qr['token'],'checkin')
    assert claims['sub']==str(uid) and claims['event_id']==eid
    assert api.get('/auth/me',headers={'Authorization':'Bearer '+qr['token']}).status_code==401
    assert api.post(f'/events/{other}/attendance/scan',headers=root,json={'token':qr['token']}).status_code==403
    assert api.post(f'/events/{eid}/attendance/scan',headers=admin,json={'token':student['Authorization'][7:]}).status_code==401
    assert api.put(f'/events/{eid}',headers=root,json={'title':'Closed','starts_at':'2026-10-17T08:00:00+07:00','checkin_open':False}).status_code==200
    assert api.get(f'/events/{eid}/qr',headers=student).status_code==409
    assert api.post(f'/events/{eid}/attendance/scan',headers=admin,json={'token':qr['token']}).status_code==409


def test_student_expired_tampered_tokens_and_unknown_subject(api,monkeypatch):
    _,admin,student,eid,_=setup_event(api,monkeypatch)
    uid=api.get('/auth/me',headers=student).json()['id']
    expired=m.token({'sub':str(uid),'kind':'access'},-1)
    assert api.get('/auth/me',headers={'Authorization':'Bearer '+expired}).status_code==401
    valid=student['Authorization'][7:]
    head,payload,sig=valid.split('.')
    claims=json.loads(base64.urlsafe_b64decode(payload+'='*((-len(payload))%4)))
    claims['sub']='1'
    altered=base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    assert api.get('/auth/me',headers={'Authorization':f'Bearer {head}.{altered}.{sig}'}).status_code==401
    for subject,expiry,expected in [(str(uid),-1,401),('999999',120,403),('invalid',120,401)]:
        qr=m.token({'sub':subject,'kind':'checkin','event_id':eid},expiry)
        assert api.post(f'/events/{eid}/attendance/scan',headers=admin,json={'token':qr}).status_code==expected


def test_google_cannot_rebind_subject_or_email(api,monkeypatch):
    auth(api,monkeypatch,'10000003')
    base={'sub':'google-10000003','email':'10000004@student.hcmute.edu.vn','hd':m.DOMAIN,'email_verified':True,'name':'Other'}
    monkeypatch.setattr(m,'verify_google',lambda _:base)
    assert api.post('/auth/google',json={'credential':'test-credential'}).status_code==403
    base.update(sub='different-sub',email='10000003@student.hcmute.edu.vn')
    assert api.post('/auth/google',json={'credential':'test-credential'}).status_code==403
