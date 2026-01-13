"""
Flask-Based Local Anonymous Student Feedback System.

This application provides:
- Token-based anonymous feedback submission
- Admin dashboard with analytics
- Excel report exports

Run with: python app.py
Access at: http://<local-ip>:5000
"""

import os
import logging
from io import BytesIO
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, abort
)
from flask_wtf.csrf import CSRFProtect
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

import config
from database import (
    init_db, validate_token, mark_token_used, save_feedback,
    get_token_stats, get_all_feedback, get_feedback_by_teacher,
    get_feedback_by_subject, get_teacher_summary, get_question_averages
)


# Disable Flask access logs for anonymity
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['WTF_CSRF_ENABLED'] = True

# Enable CSRF protection
csrf = CSRFProtect(app)


def admin_required(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# Student Routes
# =============================================================================

@app.route('/')
def index():
    """Token entry page."""
    return render_template('index.html')


@app.route('/verify-token', methods=['POST'])
def verify_token():
    """Validate the submitted token."""
    token = request.form.get('token', '').strip().upper()
    
    if not token:
        flash('Please enter a token.', 'error')
        return redirect(url_for('index'))
    
    if not validate_token(token):
        flash('Invalid or already used token.', 'error')
        return redirect(url_for('index'))
    
    # Store token in session temporarily (will be cleared after submission)
    session['valid_token'] = token
    return redirect(url_for('feedback'))


@app.route('/feedback')
def feedback():
    """Feedback form page."""
    if 'valid_token' not in session:
        flash('Please enter a valid token first.', 'error')
        return redirect(url_for('index'))
    
    return render_template(
        'feedback.html',
        teachers=config.TEACHERS,
        subjects=config.SUBJECTS,
        questions=config.QUESTIONS
    )


@app.route('/submit', methods=['POST'])
def submit():
    """Process and save feedback submission."""
    if 'valid_token' not in session:
        flash('Session expired. Please enter your token again.', 'error')
        return redirect(url_for('index'))
    
    token = session['valid_token']
    
    # Validate form data
    teacher = request.form.get('teacher', '').strip()
    subject = request.form.get('subject', '').strip()
    comment = request.form.get('comment', '').strip()
    
    if not teacher or teacher not in config.TEACHERS:
        flash('Please select a valid teacher.', 'error')
        return redirect(url_for('feedback'))
    
    if not subject or subject not in config.SUBJECTS:
        flash('Please select a valid subject.', 'error')
        return redirect(url_for('feedback'))
    
    # Collect ratings (q1 to q10)
    ratings = []
    for i in range(1, 11):
        try:
            rating = int(request.form.get(f'q{i}', 0))
            if rating < 1 or rating > 10:
                raise ValueError()
            ratings.append(rating)
        except (ValueError, TypeError):
            flash(f'Please provide a valid rating (1-10) for all questions.', 'error')
            return redirect(url_for('feedback'))
    
    # Mark token as used FIRST (prevents race conditions)
    if not mark_token_used(token):
        flash('Token has already been used.', 'error')
        session.pop('valid_token', None)
        return redirect(url_for('index'))
    
    # Save feedback
    save_feedback(teacher, subject, ratings, comment)
    
    # Clear session
    session.pop('valid_token', None)
    
    return redirect(url_for('thankyou'))


@app.route('/thankyou')
def thankyou():
    """Thank you confirmation page."""
    return render_template('thankyou.html')


# =============================================================================
# Admin Routes
# =============================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == config.ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid password.', 'error')
    
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin logout."""
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard with statistics and analytics."""
    token_stats = get_token_stats()
    teacher_summary = get_teacher_summary()
    question_averages = get_question_averages()
    
    return render_template(
        'admin_dashboard.html',
        token_stats=token_stats,
        teacher_summary=teacher_summary,
        question_averages=question_averages,
        questions=config.QUESTIONS,
        teachers=config.TEACHERS,
        subjects=config.SUBJECTS
    )


# =============================================================================
# Excel Export Routes
# =============================================================================

def create_excel_workbook(feedback_data: list, title: str) -> BytesIO:
    """Create an Excel workbook from feedback data."""
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]  # Excel sheet name limit
    
    # Headers
    headers = [
        'Teacher', 'Subject',
        'Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9', 'Q10',
        'Comment', 'Submitted At'
    ]
    
    # Write headers with bold font
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # Write data
    for row_idx, entry in enumerate(feedback_data, 2):
        ws.cell(row=row_idx, column=1, value=entry['teacher'])
        ws.cell(row=row_idx, column=2, value=entry['subject'])
        for q in range(1, 11):
            ws.cell(row=row_idx, column=q + 2, value=entry[f'q{q}'])
        ws.cell(row=row_idx, column=13, value=entry.get('comment', ''))
        ws.cell(row=row_idx, column=14, value=entry.get('submitted_at', ''))
    
    # Auto-adjust column widths
    for col in range(1, len(headers) + 1):
        max_length = max(
            len(str(ws.cell(row=row, column=col).value or ''))
            for row in range(1, len(feedback_data) + 2)
        )
        ws.column_dimensions[get_column_letter(col)].width = min(max_length + 2, 50)
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


@app.route('/export/all')
@admin_required
def export_all():
    """Export all feedback as Excel."""
    feedback = get_all_feedback()
    if not feedback:
        flash('No feedback data to export.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    excel_file = create_excel_workbook(feedback, 'All Feedback')
    filename = f'feedback_all_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@app.route('/export/teacher/<teacher_name>')
@admin_required
def export_teacher(teacher_name: str):
    """Export feedback for a specific teacher."""
    if teacher_name not in config.TEACHERS:
        abort(404)
    
    feedback = get_feedback_by_teacher(teacher_name)
    if not feedback:
        flash(f'No feedback data for {teacher_name}.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    excel_file = create_excel_workbook(feedback, teacher_name)
    safe_name = teacher_name.replace(' ', '_').replace('.', '')
    filename = f'feedback_{safe_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@app.route('/export/subject/<subject_name>')
@admin_required
def export_subject(subject_name: str):
    """Export feedback for a specific subject."""
    if subject_name not in config.SUBJECTS:
        abort(404)
    
    feedback = get_feedback_by_subject(subject_name)
    if not feedback:
        flash(f'No feedback data for {subject_name}.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    excel_file = create_excel_workbook(feedback, subject_name)
    safe_name = subject_name.replace(' ', '_')
    filename = f'feedback_{safe_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Get local IP for display
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = '127.0.0.1'
    
    print("=" * 60)
    print("  Anonymous Student Feedback System")
    print("=" * 60)
    print(f"  Local URL:    http://127.0.0.1:5000")
    print(f"  Network URL:  http://{local_ip}:5000")
    print(f"  Admin Panel:  http://127.0.0.1:5000/admin")
    print("=" * 60)
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Run Flask app on all interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)
