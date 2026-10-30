import sqlite3
from io import BytesIO

from openpyxl import load_workbook

import config
import database
from conftest import ratings, COMBOS


def start(client, token):
    return client.post('/verify-token', data={'token': token})


def complete_all(client, token):
    start(client, token)
    for i in range(len(COMBOS)):
        resp = client.post(f'/submit/{i}', data=ratings(comment=f'note {i}'))
    return resp


# ---------- Student flow ----------

def test_full_flow_marks_token_used(client):
    [token] = database.create_tokens(1)
    assert start(client, token).headers['Location'].endswith('/feedback/0')
    r = client.post('/submit/0', data=ratings())
    assert r.headers['Location'].endswith('/feedback/1')
    r = client.post('/submit/1', data=ratings())
    assert r.headers['Location'].endswith('/thankyou')
    assert client.get('/thankyou').status_code == 200
    assert database.get_token(token)['is_used'] is True
    assert len(database.get_feedback()) == 2


def test_token_reuse_fails(client):
    [token] = database.create_tokens(1)
    complete_all(client, token)
    r = start(client, token)
    assert r.headers['Location'].endswith('/')
    assert b'already been used' in client.get('/').data


def test_invalid_token_rejected(client):
    start(client, 'NOPE99')
    assert b"recognised" in client.get('/').data


def test_token_is_normalised(client):
    [token] = database.create_tokens(1)
    r = start(client, f' {token[:3].lower()}-{token[3:].lower()} ')
    assert '/feedback/0' in r.headers['Location']


def test_incomplete_form_rejected_and_answers_kept(client):
    [token] = database.create_tokens(1)
    start(client, token)
    data = ratings()
    del data['q4']
    data['q2'] = '11'
    r = client.post('/submit/0', data=data)
    assert r.status_code == 400
    assert b'2 questions need a rating' in r.data
    assert r.data.count(b'checked>') == 8  # previous answers are preserved
    assert database.get_feedback() == []


def test_double_submit_does_not_duplicate(client):
    [token] = database.create_tokens(1)
    start(client, token)
    client.post('/submit/0', data=ratings())
    client.post('/submit/0', data=ratings())
    assert len(database.get_feedback()) == 1


def test_resume_session_with_same_token(client, app):
    [token] = database.create_tokens(1)
    start(client, token)
    client.post('/submit/0', data=ratings())
    other = app.test_client()  # e.g. a different browser / after closing the tab
    r = start(other, token)
    assert r.headers['Location'].endswith('/feedback/1')


def test_feedback_requires_token(client):
    assert client.get('/feedback/0').headers['Location'].endswith('/')
    assert client.post('/submit/0', data=ratings()).headers['Location'].endswith('/')


def test_thankyou_requires_completion(client):
    assert client.get('/thankyou').status_code == 302


# ---------- Anonymity ----------

def test_feedback_table_has_no_link_to_tokens():
    with database.get_db() as conn:
        cols = {r['name'] for r in conn.execute('PRAGMA table_info(feedback)')}
        token_cols = {r['name'] for r in conn.execute('PRAGMA table_info(tokens)')}
    assert not cols & {'token', 'session_id'}
    assert not token_cols & {'created_at', 'used_at', 'submitted_at'}


def test_migration_from_v1_unlinks_feedback(tmp_path, monkeypatch):
    db = tmp_path / 'old.db'
    conn = sqlite3.connect(db)
    conn.executescript('''
        CREATE TABLE tokens (token TEXT PRIMARY KEY, is_used INTEGER DEFAULT 0);
        CREATE TABLE feedback_sessions (id INTEGER PRIMARY KEY, token TEXT UNIQUE, total_combos INT,
            completed_combos INT, is_complete INT, created_at DATETIME);
        CREATE TABLE feedback (id INTEGER PRIMARY KEY, session_id INT, combo_index INT,
            teacher TEXT, subject TEXT, semester INT, academic_session TEXT, branch TEXT,
            q1 INT, q2 INT, q3 INT, q4 INT, q5 INT, q6 INT, q7 INT, q8 INT, q9 INT, q10 INT,
            comment TEXT, submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO tokens VALUES ('AAAAAA', 0), ('BBBBBB', 1);
        INSERT INTO feedback_sessions VALUES (1, 'AAAAAA', 2, 1, 0, '2026-01-01');
        INSERT INTO feedback (session_id, combo_index, teacher, subject, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10)
            VALUES (1, 0, 'Prof. A', 'DSA', 1,2,3,4,5,6,7,8,9,10);
    ''')
    conn.close()
    monkeypatch.setattr(database, 'DATABASE_PATH', str(db))
    database.init_db()

    with database.get_db() as conn:
        cols = {r['name'] for r in conn.execute('PRAGMA table_info(feedback)')}
        tables = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert 'session_id' not in cols and 'feedback_sessions' not in tables
    assert len(database.get_feedback()) == 1
    state = database.get_token('AAAAAA')
    assert state['completed'] == {database.combo_key('Prof. A', 'DSA')} and not state['is_used']
    assert database.get_token('BBBBBB')['is_used']


# ---------- Tokens ----------

def test_create_tokens_are_unique_and_readable():
    tokens = database.create_tokens(200)
    assert len(set(tokens)) == 200
    assert all(len(t) == 6 and not set(t) & set('0O1IL') for t in tokens)
    assert database.get_token_stats() == {'total': 200, 'used': 0, 'in_progress': 0, 'unused': 200}


# ---------- Admin ----------

def test_admin_requires_login(client):
    for url in ('/admin', '/export/all', '/admin/tokens/print', '/admin/report?teacher=x&subject=y'):
        assert '/admin/login' in client.get(url).headers['Location']


def test_wrong_password_and_lockout(client):
    for _ in range(5):
        assert b'password isn' in client.post('/admin/login', data={'password': 'x'}).data
    r = client.post('/admin/login', data={'password': 'admin123'})
    assert b'Too many wrong passwords' in r.data


def test_custom_password():
    config.set_admin_password('s3cret-pass')
    assert config.check_admin_password('s3cret-pass')
    assert not config.check_admin_password('admin123')
    assert not config.is_default_admin_password()


def test_dashboard_and_report_load(admin, client):
    [token] = database.create_tokens(1)
    complete_all(client, token)
    r = admin.get('/admin')
    assert r.status_code == 200 and b'Prof. A' in r.data
    r = admin.get('/admin/report', query_string={'teacher': 'Prof. A', 'subject': 'DSA'})
    assert r.status_code == 200 and b'note 0' in r.data
    assert admin.get('/admin?period=all').status_code == 200
    assert admin.get('/admin/tokens/print').status_code == 200


def test_period_filter(admin, client):
    [t1, t2] = database.create_tokens(2)
    complete_all(client, t1)
    config.save_semester_session(8, '2022-26', 'CSE')
    complete_all(client.application.test_client(), t2)
    assert database.get_question_averages({'semester': 7, 'session': '2022-26', 'branch': 'CSE'})['responses'] == 2
    assert database.get_question_averages()['responses'] == 4
    r = admin.get('/admin?period=7|2022-26|CSE')
    assert b'Semester 7, CSE, 2022-26' in r.data


def test_excel_export(admin, client):
    [token] = database.create_tokens(1)
    start(client, token)
    client.post('/submit/0', data=ratings(comment='=HYPERLINK("http://evil")'))
    client.post('/submit/1', data=ratings(value=6))

    r = admin.get('/export/all?period=all')
    assert r.status_code == 200
    wb = load_workbook(BytesIO(r.data))
    assert wb.sheetnames == ['Summary', 'Responses', 'About']
    resp = wb['Responses']
    headers = [c.value for c in resp[1]]
    assert headers[0] == 'Teacher' and headers[5] == 'Q1. Clarity of explanation'
    assert resp[1][0].font.bold
    comments = [row[15].value for row in resp.iter_rows(min_row=2)]
    assert "'=HYPERLINK(\"http://evil\")" in comments

    r = admin.get('/export/teacher/Prof. B?period=all')
    rows = list(load_workbook(BytesIO(r.data))['Responses'].iter_rows(min_row=2, values_only=True))
    assert len(rows) == 1 and rows[0][0] == 'Prof. B'


def test_export_with_no_data_redirects(admin):
    r = admin.get('/export/all')
    assert r.status_code == 302
