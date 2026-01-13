# 📝 Anonymous Student Feedback System

A local-only, token-based anonymous feedback system for college environments. Students submit feedback using one-time tokens, and administrators can view analytics and export reports.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Generate Tokens

Generate one-time tokens for students:

```bash
# Generate 50 tokens
python generate_tokens.py 50

# Generate 100 tokens and export to file
python generate_tokens.py 100 --export tokens.txt
```

### 3. Run the Server

```bash
python app.py
```

The server will start on `http://0.0.0.0:5000`. You'll see:
- **Local URL**: `http://127.0.0.1:5000`
- **Network URL**: `http://<your-ip>:5000` (share with students)
- **Admin Panel**: `http://127.0.0.1:5000/admin`

## 📁 Project Structure

```
Local-Feedback-System/
├── app.py              # Main Flask application
├── config.py           # Configuration (teachers, subjects, questions)
├── database.py         # SQLite database operations
├── generate_tokens.py  # Token generation script
├── requirements.txt    # Python dependencies
├── feedback.db         # SQLite database (auto-created)
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── feedback.html
│   ├── thankyou.html
│   ├── admin_login.html
│   └── admin_dashboard.html
└── static/
    └── style.css       # Mobile-first CSS
```

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Admin password (or set ADMIN_PASSWORD env var)
ADMIN_PASSWORD = 'admin123'

# List of teachers
TEACHERS = [
    "Dr. Sharma",
    "Prof. Gupta",
    # Add more...
]

# List of subjects
SUBJECTS = [
    "Mathematics",
    "Physics",
    # Add more...
]

# Feedback questions (10 questions)
QUESTIONS = [
    "Clarity of explanation",
    "Subject knowledge",
    # Edit as needed...
]
```

## 👨‍🎓 Student Flow

1. Visit `http://<server-ip>:5000`
2. Enter the one-time token
3. Select teacher and subject
4. Rate 10 questions (1-10 scale)
5. Add optional comments
6. Submit → See thank you page

## 👩‍💼 Admin Flow

1. Visit `http://<server-ip>:5000/admin`
2. Enter admin password (default: `admin123`)
3. View dashboard:
   - Token statistics (total, used, unused)
   - Teacher-wise feedback summary
   - Average ratings per question
4. Export reports as Excel:
   - All feedback
   - Per teacher
   - Per subject

## 🔒 Privacy Features

- ✅ One-time tokens (cannot be reused)
- ✅ No IP address logging
- ✅ No cookies/session tracking for students
- ✅ Tokens not stored with feedback
- ✅ Flask access logs disabled

## 🛠️ Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_PASSWORD` | Admin login password | `admin123` |
| `SECRET_KEY` | Flask session secret | Random (auto-generated) |

## 📊 Excel Reports

Exported Excel files include:
- Bold headers
- Auto-adjusted column widths
- Columns: Teacher | Subject | Q1-Q10 | Comment | Submitted At

## 🧪 Testing

```bash
# Generate test tokens
python generate_tokens.py 5

# Run the server
python app.py

# Test endpoints:
# - Submit feedback with a token
# - Try reusing the same token (should fail)
# - Login to admin and export Excel
```

## 🔧 Troubleshooting

**Port already in use:**
```bash
# Kill process on port 5000
kill -9 $(lsof -t -i:5000)
```

**Reset database:**
```bash
rm feedback.db
python app.py  # Will create fresh database
```

---

Made with ❤️ for anonymous student feedback
