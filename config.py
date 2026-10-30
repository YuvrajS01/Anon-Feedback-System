"""
Configuration settings for the Anonymous Feedback System.

Runtime settings (combos, academic period, templates, admin password) live in
system_config.json and are edited through the Control Panel. The server
re-reads the file on every request, so changes apply immediately.
"""

import os
import json
import secrets
import socket
import tempfile

from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.environ.get('FEEDBACK_CONFIG', os.path.join(BASE_DIR, 'system_config.json'))
SECRET_KEY_FILE = os.path.join(BASE_DIR, '.secret_key')
DATABASE_PATH = os.environ.get('FEEDBACK_DB', os.path.join(BASE_DIR, 'feedback.db'))

PORT = int(os.environ.get('PORT', 5000))

DEFAULT_ADMIN_PASSWORD = 'admin123'

# Default Teacher-Subject Combos. Each combo is one feedback the student gives.
DEFAULT_TEACHER_SUBJECT_COMBOS = [
    {"teacher": "Dr. Sharma", "subject": "Mathematics"},
    {"teacher": "Prof. Gupta", "subject": "Physics"},
    {"teacher": "Dr. Patel", "subject": "Chemistry"},
]

DEFAULT_SEMESTER = 1
DEFAULT_SESSION = "2024-28"
DEFAULT_BRANCH = "CSE"

AVAILABLE_BRANCHES = ["CSE", "EEE", "ME", "CE", "B.Arch", "M.Tech"]

# Feedback questions (exactly 10, each rated 1-10)
QUESTIONS = [
    "Clarity of explanation",
    "Subject knowledge",
    "Teaching pace",
    "Student engagement",
    "Doubt handling",
    "Use of examples",
    "Classroom interaction",
    "Fairness in evaluation",
    "Availability outside class",
    "Overall effectiveness",
]


# =============================================================================
# Config file helpers
# =============================================================================

def _read_config() -> dict:
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _write_config(data: dict):
    """Write atomically so the server never reads a half-written file."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(CONFIG_FILE), prefix='.config-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, CONFIG_FILE)
    except BaseException:
        os.unlink(tmp)
        raise


def _update_config(**changes):
    data = _read_config()
    data.update(changes)
    _write_config(data)


# =============================================================================
# Combos and academic period
# =============================================================================

def load_combos() -> list:
    """Load teacher-subject combos from config file or use defaults."""
    return _read_config().get('teacher_subject_combos', DEFAULT_TEACHER_SUBJECT_COMBOS)


def save_combos(combos: list):
    _update_config(teacher_subject_combos=combos)


def load_semester_session() -> dict:
    """Current academic period: {'semester', 'session', 'branch'}."""
    data = _read_config()
    return {
        'semester': data.get('semester', DEFAULT_SEMESTER),
        'session': data.get('session', DEFAULT_SESSION),
        'branch': data.get('branch', DEFAULT_BRANCH),
    }


def save_semester_session(semester: int, session: str, branch: str | None = None):
    changes = {'semester': semester, 'session': session}
    if branch:
        changes['branch'] = branch
    _update_config(**changes)


# =============================================================================
# Templates (saved period + combo presets)
# =============================================================================

def load_templates() -> dict:
    return _read_config().get('templates', {})


def get_template(name: str):
    return load_templates().get(name)


def save_template(name: str, semester: int, session: str, branch: str, combos: list):
    templates = load_templates()
    templates[name] = {
        'semester': semester,
        'session': session,
        'branch': branch,
        'teacher_subject_combos': combos,
    }
    _update_config(templates=templates)


def delete_template(name: str) -> bool:
    templates = load_templates()
    if name not in templates:
        return False
    del templates[name]
    _update_config(templates=templates)
    return True


def apply_template(name: str) -> bool:
    """Make a template's period and combos the current configuration."""
    template = get_template(name)
    if not template:
        return False
    _update_config(
        semester=template['semester'],
        session=template['session'],
        branch=template['branch'],
        teacher_subject_combos=template['teacher_subject_combos'],
    )
    return True


# =============================================================================
# Security
# =============================================================================

def get_secret_key() -> str:
    """SECRET_KEY env var, or a random key generated once and kept on disk."""
    if os.environ.get('SECRET_KEY'):
        return os.environ['SECRET_KEY']
    try:
        with open(SECRET_KEY_FILE, 'r') as f:
            key = f.read().strip()
            if key:
                return key
    except FileNotFoundError:
        pass
    key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(key)
    os.chmod(SECRET_KEY_FILE, 0o600)
    return key


def check_admin_password(password: str) -> bool:
    """Check against ADMIN_PASSWORD env var, the saved hash, or the default."""
    env_password = os.environ.get('ADMIN_PASSWORD')
    if env_password:
        return secrets.compare_digest(password.encode(), env_password.encode())
    stored = _read_config().get('admin_password_hash')
    if stored:
        return check_password_hash(stored, password)
    return secrets.compare_digest(password.encode(), DEFAULT_ADMIN_PASSWORD.encode())


def set_admin_password(password: str):
    _update_config(admin_password_hash=generate_password_hash(password))


def is_default_admin_password() -> bool:
    return not os.environ.get('ADMIN_PASSWORD') and not _read_config().get('admin_password_hash')


# =============================================================================
# Network
# =============================================================================

def get_local_ip() -> str:
    """LAN IP of this machine (what students should type). No traffic is sent."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))
            return s.getsockname()[0]
    except OSError:
        return '127.0.0.1'
