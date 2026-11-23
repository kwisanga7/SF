# SafetyFund Workspace

A Django workspace starter for SafetyFund team management and communication. It includes a responsive dashboard, sign-in, task tracking, announcements, Django admin, and an installable progressive web app shell for phones and desktop browsers.

## Start locally

1. Install Python 3.11 or newer and PostgreSQL 15 or newer.
2. Create and activate a virtual environment, then install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`, set a private `DJANGO_SECRET_KEY`, and enter your PostgreSQL database credentials. Create a database named `safetyfund` (or use the name configured in `.env`).
4. Apply database migrations and create the first administrator:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

5. Open http://127.0.0.1:8000 for the public SafetyFund page. Use the navigation for About, Contact, Announcements, Meet The Team, Register, and Login. Signed-in members reach the private workspace at http://127.0.0.1:8000/workspace/. Manage public team profiles and announcements, and review contact form submissions, at http://127.0.0.1:8000/admin/.

For a quick local preview before PostgreSQL is set up, leave `DB_NAME` unset in `.env`; Django will use a local SQLite database. PostgreSQL is selected automatically when `DB_NAME` is configured.

## Mobile and desktop

The responsive web app can be installed from a supported browser using its **Install app** or **Add to Home Screen** action. This gives it an app-style window on desktop and a home-screen icon on mobile. The current PWA caches its static interface files; sign-in and live workspace data still require a connection. A store-distributed native mobile app or a separately packaged desktop executable can be added after the workflows and branding are finalized.

## Current scope

- Authenticated team dashboard with member and task summaries.
- Task status updates and due dates.
- Company announcements.
- Django admin for managing tasks, announcements, and team accounts.
- Responsive layout and installable PWA shell.

This is a starter foundation; role-based permissions, direct messaging, richer task creation, notifications, and deployment configuration are natural next features.
