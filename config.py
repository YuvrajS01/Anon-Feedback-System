"""
Configuration settings for the Anonymous Feedback System.
Edit this file to customize teachers, subjects, and questions.
"""

import os

# Flask secret key for session management (fixed for consistent sessions)
# In production, set this via environment variable
SECRET_KEY = os.environ.get('SECRET_KEY', 'feedback-system-local-secret-key-2024')

# Admin password (can be set via environment variable)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# List of teachers (edit as needed)
TEACHERS = [
    "Dr. Sharma",
    "Prof. Gupta",
    "Dr. Patel",
    "Prof. Singh",
    "Dr. Kumar",
    "Prof. Verma",
    "Dr. Joshi",
    "Prof. Agarwal",
]

# List of subjects (edit as needed)
SUBJECTS = [
    "Mathematics",
    "Physics",
    "Chemistry",
    "Computer Science",
    "Electronics",
    "Data Structures",
    "Database Management",
    "Operating Systems",
]

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
