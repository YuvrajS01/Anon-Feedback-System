"""
Flask-Based Local Anonymous Student Feedback System.

This application provides:
- Token-based anonymous feedback submission
- Multi-teacher feedback per token (admin configurable combos)
- Admin dashboard with analytics and per-teacher reports
- Excel report exports and printable token slips

Run with: python app.py
Access at: http://<local-ip>:5000
"""

import logging
import re
import time
from datetime import datetime
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, abort
)
from flask_wtf.csrf import CSRFProtect
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

import config
from database import (
    init_db, get_token, submit_feedback, AlreadySubmitted, combo_key,
    get_token_stats, get_feedback, get_teacher_summary, get_question_averages,
    get_periods, get_unused_tokens, QUESTION_COLUMNS
)

try:
    import segno
except ImportError:  # QR codes are optional
    segno = None


# Disable Flask access logs for anonymity
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
app.secret_key = config.get_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    MAX_CONTENT_LENGTH=64 * 1024,
)
csrf = CSRFProtect(app)

init_db()

COMMENT_MAX_LENGTH = 2000
LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT_SECONDS = 60
# Not keyed by IP on purpose: we never record who is connecting.
_login_failures: list[float] = []


@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
    )
    if request.path.startswith(('/admin', '/export', '/feedback')):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.context_processor
def inject_globals():
    return {'is_admin': session.get('admin_logged_in', False)}


def admin_required(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login', next=request.full_path))
        return f(*args, **kwargs)
    return decorated_function


def normalize_token(raw: str) -> str:
    return re.sub(r'[\s-]', '', raw or '').upper()


def pending_combos(completed: set) -> list:
    """(index, combo) pairs from the current config not yet rated by this token."""
    return [(i, c) for i, c in enumerate(config.load_combos())
            if combo_key(c['teacher'], c['subject']) not in completed]


def end_student_session():
    session.pop('valid_token', None)


def finish():
    """Clear the student's session and show the thank-you page."""
    end_student_session()
    session['just_finished'] = True
    return redirect(url_for('thankyou'))


# =============================================================================
# Student Routes
# =============================================================================

@app.route('/')
def index():
    """Token entry page (?t=TOKEN pre-fills it, used by QR codes)."""
    return render_template('index.html', prefill=normalize_token(request.args.get('t', ''))[:12])


@app.route('/verify-token', methods=['POST'])
def verify_token():
    """Validate the submitted token and start or resume its session."""
    token = normalize_token(request.form.get('token', ''))
    if not token:
        flash('Enter the code from your slip to start.', 'error')
        return redirect(url_for('index'))

    if not config.load_combos():
        flash("Feedback isn't open yet. Ask your class coordinator when it starts.", 'error')
        return redirect(url_for('index'))

    state = get_token(token)
    if state is None:
        flash("That code wasn't recognised. Check it against your slip and try again.", 'error')
        return redirect(url_for('index'))
    if state['is_used']:
        flash('This code has already been used. Each code works for one set of ratings.', 'error')
        return redirect(url_for('index'))

    pending = pending_combos(state['completed'])
    if not pending:
        flash('This code has already been used. Each code works for one set of ratings.', 'error')
        return redirect(url_for('index'))

    session['valid_token'] = token
    if state['completed']:
        flash('Welcome back. Your earlier ratings are saved, so carry on from here.', 'success')
    return redirect(url_for('feedback_step', index=pending[0][0]))


def render_feedback_form(index: int, combos: list, completed: set,
                         values: dict | None = None, errors: set | None = None, status=200):
    steps = [{**c, 'done': combo_key(c['teacher'], c['subject']) in completed} for c in combos]
    done = sum(s['done'] for s in steps)
    return render_template(
        'feedback_step.html',
        combo=combos[index],
        combos=steps,
        combo_index=index,
        step=done + 1,
        total_combos=len(combos),
        questions=config.QUESTIONS,
        period=config.load_semester_session(),
        values=values or {},
        errors=errors or set(),
        comment_max=COMMENT_MAX_LENGTH,
    ), status


def load_student_step(index: int):
    """Shared checks for the feedback GET/POST routes. Returns (token state, combos)."""
    token = session.get('valid_token')
    state = get_token(token) if token else None
    if not state or state['is_used']:
        end_student_session()
        flash('Your session ended. Enter your code again to carry on.', 'error')
        abort(redirect(url_for('index')))

    combos = config.load_combos()
    if index < 0 or index >= len(combos):
        abort(404)
    return state, combos


@app.route('/feedback/<int:index>')
def feedback_step(index):
    """Feedback form for one teacher-subject combo."""
    state, combos = load_student_step(index)
    pending = pending_combos(state['completed'])
    if not pending:
        return finish()
    if index not in [i for i, _ in pending]:
        return redirect(url_for('feedback_step', index=pending[0][0]))

    return render_feedback_form(index, combos, state['completed'])


@app.route('/submit/<int:index>', methods=['POST'])
def submit_step(index):
    """Validate and save feedback for one combo, then move to the next."""
    state, combos = load_student_step(index)
    combo = combos[index]
    values = {q: request.form.get(q, '') for q in QUESTION_COLUMNS}
    comment = request.form.get('comment', '').strip()[:COMMENT_MAX_LENGTH]
    values['comment'] = comment

    ratings, errors = [], set()
    for q in QUESTION_COLUMNS:
        try:
            rating = int(values[q])
            if not 1 <= rating <= 10:
                raise ValueError
            ratings.append(rating)
        except ValueError:
            errors.add(q)

    if errors:
        missing = len(errors)
        flash(f"{missing} {'question needs' if missing == 1 else 'questions need'} a rating before you can continue.", 'error')
        return render_feedback_form(index, combos, state['completed'], values, errors, status=400)

    try:
        finished = submit_feedback(
            session['valid_token'], combo, combos, ratings, comment,
            config.load_semester_session()
        )
    except AlreadySubmitted:
        finished = False
    except ValueError:
        end_student_session()
        flash('This code has already been used. Each code works for one set of ratings.', 'error')
        return redirect(url_for('index'))

    if finished:
        return finish()

    pending = pending_combos(get_token(session['valid_token'])['completed'])
    if not pending:
        return finish()
    return redirect(url_for('feedback_step', index=pending[0][0]))


@app.route('/thankyou')
def thankyou():
    """Thank you confirmation page."""
    if not session.pop('just_finished', False):
        return redirect(url_for('index'))
    return render_template('thankyou.html')


# =============================================================================
# Admin Routes
# =============================================================================

def parse_period_arg() -> tuple[dict | None, str]:
    """Read ?period= (\"all\" or \"sem|session|branch\"). Defaults to the current period."""
    raw = request.args.get('period')
    if raw == 'all':
        return None, 'all'
    if raw:
        parts = raw.split('|')
        if len(parts) == 3:
            sem = int(parts[0]) if parts[0].isdigit() else None
            return {'semester': sem, 'session': parts[1] or None, 'branch': parts[2] or None}, raw
    current = config.load_semester_session()
    return current, period_value(current)


def period_value(p: dict) -> str:
    return f"{p['semester'] or ''}|{p['session'] or ''}|{p['branch'] or ''}"


def period_label(p: dict | None) -> str:
    if p is None:
        return 'All periods'
    sem = f"Semester {p['semester']}" if p['semester'] else 'Unknown semester'
    return ', '.join([sem, *(v for v in (p['branch'], p['session']) if v)])


app.jinja_env.globals.update(period_value=period_value, period_label=period_label)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        now = time.monotonic()
        _login_failures[:] = [t for t in _login_failures if now - t < LOGIN_LOCKOUT_SECONDS]
        if len(_login_failures) >= LOGIN_MAX_FAILURES:
            flash('Too many wrong passwords. Wait one minute, then try again.', 'error')
        elif config.check_admin_password(request.form.get('password', '')):
            _login_failures.clear()
            session.clear()
            session['admin_logged_in'] = True
            target = request.args.get('next', '')
            if not target.startswith('/') or target.startswith('//'):
                target = url_for('admin_dashboard')
            return redirect(target)
        else:
            _login_failures.append(now)
            flash("That password isn't right.", 'error')

    return render_template('admin_login.html',
                           default_password=config.is_default_admin_password())


@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout."""
    session.pop('admin_logged_in', None)
    flash('Signed out.', 'success')
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard with statistics and analytics."""
    period, selected = parse_period_arg()
    periods = get_periods()
    current = config.load_semester_session()
    if period_value(current) not in [period_value(p) for p in periods]:
        periods.insert(0, {**current, 'responses': 0})

    return render_template(
        'admin_dashboard.html',
        token_stats=get_token_stats(),
        teacher_summary=get_teacher_summary(period),
        averages=get_question_averages(period),
        questions=config.QUESTIONS,
        combos=config.load_combos(),
        current_period=current,
        periods=periods,
        period=period,
        selected_period=selected,
        default_password=config.is_default_admin_password(),
        local_url=f'http://{config.get_local_ip()}:{config.PORT}',
    )


@app.route('/admin/report')
@admin_required
def admin_report():
    """Detailed report for one teacher-subject pair."""
    teacher = request.args.get('teacher')
    subject = request.args.get('subject')
    if not teacher or not subject:
        abort(404)
    period, selected = parse_period_arg()
    averages = get_question_averages(period, teacher, subject)
    entries = get_feedback(period, teacher, subject)

    # Rating distribution per question (count of each 1-10 score)
    distribution = {q: [0] * 10 for q in QUESTION_COLUMNS}
    for e in entries:
        for q in QUESTION_COLUMNS:
            distribution[q][e[q] - 1] += 1

    ranked = sorted(zip(QUESTION_COLUMNS, config.QUESTIONS), key=lambda qc: averages[qc[0]] or 0)

    return render_template(
        'admin_report.html',
        strongest=ranked[-1][1],
        weakest=ranked[0][1],
        periods=get_periods(),
        teacher=teacher,
        subject=subject,
        averages=averages,
        distribution=distribution,
        comments=[e['comment'] for e in entries if e['comment'] and e['comment'].strip()],
        questions=config.QUESTIONS,
        period=period,
        selected_period=selected,
    )


@app.route('/admin/tokens/print')
@admin_required
def print_tokens():
    """Printable slips (with QR codes) for tokens that haven't been started."""
    try:
        limit = max(1, min(int(request.args.get('limit', 60)), 1000))
    except ValueError:
        limit = 60
    base_url = f'http://{config.get_local_ip()}:{config.PORT}/'
    slips = []
    for token in get_unused_tokens(limit):
        qr = None
        if segno:
            qr = segno.make(f'{base_url}?t={token}', error='m').svg_inline(scale=3, border=1)
        slips.append({'token': token, 'qr': qr})
    return render_template('print_tokens.html', slips=slips, base_url=base_url,
                           period=config.load_semester_session())


# =============================================================================
# Excel Export Routes
# =============================================================================

HEADER_FONT = Font(bold=True, color='FFFFFF')
HEADER_FILL = PatternFill('solid', fgColor='334155')


def excel_safe(value):
    """Neutralise spreadsheet formula injection in user-supplied text."""
    if isinstance(value, str) and value[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


def write_sheet(ws, headers: list, rows: list):
    ws.append(headers)
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for row in rows:
        ws.append([excel_safe(v) for v in row])
    ws.freeze_panes = 'A2'
    for col in range(1, len(headers) + 1):
        longest = max((len(str(c.value or '')) for c in ws[get_column_letter(col)]), default=10)
        ws.column_dimensions[get_column_letter(col)].width = min(max(longest + 2, 8), 50)


def create_excel_workbook(feedback_data: list, period: dict | None) -> BytesIO:
    """Workbook with a summary sheet and one row per feedback entry."""
    wb = Workbook()
    q_headers = [f'Q{i}. {q}' for i, q in enumerate(config.QUESTIONS, 1)]

    summary = wb.active
    summary.title = 'Summary'
    groups = {}
    for e in feedback_data:
        groups.setdefault((e['teacher'], e['subject']), []).append(e)
    summary_rows = []
    for (teacher, subject), entries in sorted(groups.items()):
        avgs = [round(sum(e[q] for e in entries) / len(entries), 2) for q in QUESTION_COLUMNS]
        summary_rows.append([teacher, subject, len(entries), round(sum(avgs) / len(avgs), 2), *avgs])
    write_sheet(summary, ['Teacher', 'Subject', 'Responses', 'Overall Avg', *q_headers], summary_rows)

    detail = wb.create_sheet('Responses')
    write_sheet(
        detail,
        ['Teacher', 'Subject', 'Semester', 'Session', 'Branch', *q_headers, 'Comment', 'Submitted At'],
        [[e['teacher'], e['subject'], e['semester'], e['academic_session'], e['branch'],
          *(e[q] for q in QUESTION_COLUMNS), e['comment'] or '', e['submitted_at']]
         for e in feedback_data]
    )

    info = wb.create_sheet('About')
    info.append(['Period', period_label(period)])
    info.append(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M')])
    info.append(['Scale', '1 (poor) – 10 (excellent)'])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def excel_response(feedback: list, name: str, period: dict | None):
    if not feedback:
        flash(f'There are no responses for {name} in {period_label(period)} to download.', 'error')
        return redirect(request.referrer or url_for('admin_dashboard'))
    safe_name = re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_') or 'report'
    filename = f'feedback_{safe_name}_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    return send_file(
        create_excel_workbook(feedback, period),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


@app.route('/export/all')
@admin_required
def export_all():
    period, _ = parse_period_arg()
    return excel_response(get_feedback(period), 'all', period)


@app.route('/export/teacher/<teacher_name>')
@admin_required
def export_teacher(teacher_name: str):
    period, _ = parse_period_arg()
    return excel_response(get_feedback(period, teacher=teacher_name), teacher_name, period)


@app.route('/export/subject/<subject_name>')
@admin_required
def export_subject(subject_name: str):
    period, _ = parse_period_arg()
    return excel_response(get_feedback(period, subject=subject_name), subject_name, period)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    local_ip = config.get_local_ip()
    combos = config.load_combos()

    print("=" * 60)
    print("  Anonymous Student Feedback System")
    print("=" * 60)
    print(f"  Student URL:  http://{local_ip}:{config.PORT}")
    print(f"  Admin Panel:  http://{local_ip}:{config.PORT}/admin")
    print(f"  Combos:       {len(combos)} teacher-subject pairs")
    if config.is_default_admin_password():
        print("  WARNING:      admin password is still the default 'admin123'")
    print("=" * 60)
    print("  Press Ctrl+C to stop the server")
    print("=" * 60, flush=True)

    app.run(host='0.0.0.0', port=config.PORT, debug=False)
