"""
Configuration settings for the Anonymous Feedback System.
Edit this file to customize teacher-subject combos and questions.
"""

import os
import json

# Flask secret key for session management (fixed for consistent sessions)
# In production, set this via environment variable
SECRET_KEY = os.environ.get('SECRET_KEY', 'feedback-system-local-secret-key-2024')

# Admin password (can be set via environment variable)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Configuration file path for dynamic updates from GUI
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'system_config.json')

# Default Teacher-Subject Combos (Admin configurable)
# Each combo represents one feedback the student must give
DEFAULT_TEACHER_SUBJECT_COMBOS = [
    {"teacher": "Dr. Sharma", "subject": "Mathematics"},
    {"teacher": "Prof. Gupta", "subject": "Physics"},
    {"teacher": "Dr. Patel", "subject": "Chemistry"},
]

def load_combos():
    """Load teacher-subject combos from config file or use defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('teacher_subject_combos', DEFAULT_TEACHER_SUBJECT_COMBOS)
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_TEACHER_SUBJECT_COMBOS

def save_combos(combos):
    """Save teacher-subject combos to config file."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    config['teacher_subject_combos'] = combos
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Dynamic property to get current combos
TEACHER_SUBJECT_COMBOS = load_combos()

# Feedback questions (10 questions, each rated 1-10)
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

# Database file path
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'feedback.db')
