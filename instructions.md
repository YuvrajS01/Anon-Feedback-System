📌 DETAILED PROJECT PROMPT
Flask-Based Local Anonymous Student Feedback System (Token-Based)
🔹 PROJECT OVERVIEW

Build a local-only, token-based anonymous feedback system for a college environment using Python Flask.
The system will run on one local server (PC / laptop) and be accessible only within the local network (LAN / hotspot).
Students will submit feedback anonymously using one-time tokens, and admins will be able to view analytics and export reports in Excel format.

No internet connectivity should be required.

🎯 CORE OBJECTIVES

Ensure complete student anonymity

Allow one feedback per student using tokens

Collect structured, quantitative feedback

Generate clean Excel reports

Provide admin-only analytics dashboard

🧱 SYSTEM ARCHITECTURE

Backend: Python (Flask)

Database: SQLite

Frontend: HTML, CSS (mobile-first)

File Export: Excel (.xlsx)

Hosting: Local machine only

🔐 AUTHENTICATION & ANONYMITY

Students authenticate only via one-time tokens

Tokens must:

Be randomly generated (5–6 characters)

Be usable only once

NOT be linked to any identity

Do NOT store:

IP address

User-Agent

Cookies

Session identifiers

Disable Flask access logs

🔁 USER FLOW
👨‍🎓 STUDENT FLOW

Student opens local URL
http://<local-ip>:5000

Enters token

System validates token

Student selects:

Teacher name (dropdown)

Subject name (dropdown)

Feedback form loads:

10 questions

Each question rated 1–10

One open comment box

Student submits feedback

Token is immediately marked as used

Student sees a thank-you confirmation page

👩‍💼 ADMIN FLOW

Admin accesses /admin

Admin logs in using admin password

Admin dashboard displays:

Total tokens generated

Tokens used vs unused

Teacher-wise feedback summary

Average rating per question

Admin can:

View detailed feedback per teacher

Download reports as Excel files

Download:

Teacher-wise report

Subject-wise report

Overall summary report

🗄️ DATABASE DESIGN
🔹 Tokens Table
tokens (
  token TEXT PRIMARY KEY,
  is_used INTEGER DEFAULT 0
)

🔹 Feedback Table
feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  teacher TEXT,
  subject TEXT,
  q1 INTEGER,
  q2 INTEGER,
  q3 INTEGER,
  q4 INTEGER,
  q5 INTEGER,
  q6 INTEGER,
  q7 INTEGER,
  q8 INTEGER,
  q9 INTEGER,
  q10 INTEGER,
  comment TEXT,
  submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
)


⚠️ Do not store token inside feedback table.

📊 FEEDBACK QUESTIONS

Use placeholder text such as:

Clarity of explanation

Subject knowledge

Teaching pace

Student engagement

Doubt handling

Use of examples

Classroom interaction

Fairness in evaluation

Availability outside class

Overall effectiveness

Each question must accept a rating from 1 to 10.

📁 EXCEL EXPORT REQUIREMENTS

Use .xlsx format

One row per feedback entry

Column headers:

Teacher | Subject | Q1 | Q2 | ... | Q10 | Comment | Submitted At


Separate Excel files for:

Each teacher

Overall feedback

Automatically format:

Bold headers

Auto column width

🧩 ROUTES TO IMPLEMENT
Route	Purpose
/	Token entry page
/verify-token	Token validation
/feedback	Feedback form
/submit	Save feedback
/admin	Admin dashboard
/export/<type>	Excel export
🎨 UI REQUIREMENTS

Mobile-first design

Clean, distraction-free UI

Large buttons & sliders for ratings

Clear privacy notice displayed

🛡️ SECURITY REQUIREMENTS

Admin routes password-protected

Token reuse must be impossible

Input validation on all fields

CSRF protection (optional but preferred)

🧪 TESTING REQUIREMENTS

Attempt reuse of token → must fail

Submit incomplete form → validation error

Export Excel → correct formatting

Admin dashboard loads without errors

🚀 OPTIONAL ENHANCEMENTS (If Time Permits)

QR code linking to feedback page

Time-limited feedback window

Teacher comparison charts

Local sentiment analysis on comments

🧾 FINAL DELIVERABLES

Complete Flask project structure

app.py

HTML templates

SQLite database

Token generation script

Excel export functionality

Setup & run instructions

📌 DEVELOPMENT CONSTRAINTS

Must work offline

Must run on low-end hardware

Must be easy to deploy by non-technical staff

✅ OUTPUT EXPECTATION

Generate fully working Flask code that meets all requirements above, with clear comments and clean structure.
