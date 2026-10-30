import json
import os
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix='feedback-test-')
os.environ['FEEDBACK_DB'] = os.path.join(_tmp, 'test.db')
os.environ['FEEDBACK_CONFIG'] = os.path.join(_tmp, 'config.json')
os.environ['SECRET_KEY'] = 'test-secret'
os.environ.pop('ADMIN_PASSWORD', None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database  # noqa: E402
from app import app as flask_app, _login_failures  # noqa: E402

COMBOS = [
    {'teacher': 'Prof. A', 'subject': 'DSA'},
    {'teacher': 'Prof. B', 'subject': 'ML'},
]


@pytest.fixture(autouse=True)
def fresh_state():
    with open(config.CONFIG_FILE, 'w') as f:
        json.dump({'semester': 7, 'session': '2022-26', 'branch': 'CSE',
                   'teacher_subject_combos': COMBOS}, f)
    database.init_db()
    database.reset_database()
    _login_failures.clear()
    yield


@pytest.fixture
def app():
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(client):
    client.post('/admin/login', data={'password': 'admin123'})
    return client


def ratings(value=8, **overrides):
    data = {f'q{i}': str(value) for i in range(1, 11)}
    data.update(overrides)
    return data
