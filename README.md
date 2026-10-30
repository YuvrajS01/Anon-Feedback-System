# Anonymous Student Feedback System

A local-only, token-based feedback system for colleges. It runs on one laptop and students connect over the same Wi-Fi or hotspot. No internet is needed.

Each student gets a one-time token. They rate every teacher-subject pair for the current semester on 10 questions (1–10) and can add a comment. Administrators see live results, per-teacher reports and Excel exports.

## Quick start

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python control_panel.py           # GUI: start server, set up subjects, make tokens
# or, without the GUI:
python generate_tokens.py 60      # create 60 tokens
python app.py                     # start the server on port 5000
```

The server prints the address students should open, for example `http://192.168.1.20:5000`.

## Running a feedback round

1. **Set the period.** In the Control Panel, choose the semester, session and branch, then add the teacher-subject pairs. Save the setup as a template to reuse it next term.
2. **Set an admin password.** Use the *Admin Password* card. Until you do, the password is `admin123` and the dashboard shows a warning.
3. **Make tokens.** Generate one per student, then click **Print Slips (QR)**. This opens a printable sheet of cut-out slips, each with a QR code that opens the form with the token already filled in.
4. **Collect.** Students scan or type the URL, enter their token and rate each subject. If they close the tab they can resume with the same token. A token stops working once every subject is done.
5. **Review.** Open `/admin` to see response counts, average ratings by question, and a report for each teacher with score distributions and comments. Results are filtered by academic period and you can switch periods from the dropdown.
6. **Export.** Download Excel files for everything, one teacher or one subject. Each workbook has a *Summary* sheet (averages) and a *Responses* sheet (one row per submission).

## Privacy

- Feedback rows contain **no token and no session link**. Progress is tracked on the token itself, and token rows have no timestamps, so a response can't be matched to the student who gave it.
- No IP addresses, user agents or access logs are recorded. Login throttling is global on purpose, so it doesn't track who is connecting.
- Students are asked not to put their name in comments. Comments are shown to admins exactly as written.

## Configuration

| Setting | Where |
|---|---|
| Teacher-subject pairs, semester, session, branch, templates | Control Panel (saved to `system_config.json`) |
| Admin password | Control Panel, or the `ADMIN_PASSWORD` env var (overrides the saved one) |
| Questions | `QUESTIONS` in `config.py` (must stay at exactly 10) |
| Port | `PORT` env var (default `5000`) |
| Session secret | Generated automatically into `.secret_key`, or set `SECRET_KEY` |
| Database / config paths | `FEEDBACK_DB`, `FEEDBACK_CONFIG` env vars |

`system_config.example.json` shows the config format. The live `system_config.json`, `feedback.db` and token files are git-ignored because they contain real responses and valid tokens.

## Project layout

```
app.py               Flask routes: student flow, admin dashboard/reports, exports
database.py          SQLite schema, migrations and queries
config.py            Settings, config-file helpers, admin password, LAN IP
control_panel.py     Tkinter GUI for running a feedback round
generate_tokens.py   Command-line token generator
templates/           Jinja templates (student, admin, printable slips)
static/              style.css, app.js and bundled fonts (Atkinson Hyperlegible Next/Mono, OFL)
tests/               pytest suite
```

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Tests use a temporary database and config file. They never touch your real data.

### Upgrading from an older version

On first start, `init_db()` migrates older databases automatically. It moves in-progress state onto the token rows, removes the `session_id` link from feedback, and drops the `feedback_sessions` table. **This permanently removes the link between tokens and responses.** Make a copy of `feedback.db` first if you need to keep the old file.

## Troubleshooting

- **Students can't connect.** Make sure they're on the same network and that your firewall allows the port (Linux: `sudo ufw allow 5000`; on Windows, allow Python when prompted).
- **Port already in use.** The Control Panel checks this and tells you. From a terminal: `lsof -ti:5000 | xargs kill`.
- **The server stopped right after starting.** The Control Panel shows the error. The full output is in `server.log`.
- **Start a fresh term.** Use *Reset Database* in the Control Panel. It deletes all tokens and feedback, so export first.
