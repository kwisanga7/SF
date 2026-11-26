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

5. Open http://127.0.0.1:8000 for the public SafetyFund page. Guests can browse without an account. Registration creates a regular user account; users can apply for membership from **My Account**. Staff review applications from http://127.0.0.1:8000/management/applications/. Only approved members and staff administrators can enter the private workspace at http://127.0.0.1:8000/workspace/.

The central staff dashboard is http://127.0.0.1:8000/management/ and links to membership review, people and roles, share deposit verification, loans, repayments, announcements, team profiles, contact messages, tasks, user accounts, and the full Django admin. The dashboard also summarizes approved fund balances, monthly share progress, recent activity, members needing contribution follow-up, and overdue tasks. The separate membership queue is http://127.0.0.1:8000/management/applications/; staff can inspect applicant details and payment proof, then approve, reject, or request more information. Applicants see requests in **My Account** and can reply; each submission, request, reply, decision, role change, and profile update is retained in the application history. Use **People & roles** at http://127.0.0.1:8000/management/members/ to update account details and assign User, Member, Finance, Secretary, Developer, Marketing, or Admin roles. Member and staff roles require approved membership; changing someone to User revokes their member access. Assigning Admin grants the staff dashboard and SafetyFund workspace management permissions. The primary superuser cannot be changed from this page. Finance-role members and admins receive in-app notifications for monthly share deposits and can review the private proof on the workspace page. Applicants provide their full name, ID number, phone, email, payment method, and proof of payment. The form accepts PDF, JPG, or PNG files up to 5 MB. Proof files are stored under `private_media/` and can be downloaded only through a staff or Finance review page; this directory is excluded from version control. The form lists MoMoPay `050456` and Equity Bank `4004201431267`, and records the selected method and receipt; it does not process payments. For payment help, the form lists Secretary `0792448389` and Finance `0783038052`. Announcements and team profiles must be marked public/published before they appear on the public pages.

The public site uses the supplied SafetyFund logo and team photograph from `workspace/static/workspace/`; the Django app serves them through `/brand-logo.jpg` and `/team-photo.jpeg`.

For a quick local preview before PostgreSQL is set up, leave `DB_NAME` unset in `.env`; Django will use a local SQLite database. PostgreSQL is selected automatically when `DB_NAME` is configured.

## Mobile and desktop

The responsive web app can be installed from a supported browser using its **Install app** or **Add to Home Screen** action. This gives it an app-style window on desktop and a home-screen icon on mobile. The current PWA caches its static interface files; sign-in and live workspace data still require a connection. A store-distributed native mobile app or a separately packaged desktop executable can be added after the workflows and branding are finalized.

## Current scope

- Authenticated team dashboard with member and task summaries.
- Member finance dashboard with monthly share purchases (1–4 shares), loan requests, repayment submissions, and a personal summary of approved share capital, management/development fees, and outstanding approved loan principal. Each financial submission remains pending until reviewed by an admin; proof is kept private.
- Finance-role members and admins receive an in-app notification when a monthly share payment is submitted and can privately inspect its proof, then approve or reject it with a review note. Members are notified in-app of the decision; no email or SMS delivery is configured.
- Task status updates and due dates.
- Company announcements.
- Django admin for managing tasks, announcements, and team accounts.
- Responsive layout and installable PWA shell.

All deposit, loan, repayment, and membership-fee amounts are displayed in Rwandan francs (RWF). One share costs RWF 6,000 per month, split into RWF 5,000 share capital and RWF 1,000 management/development fees. Loan balances currently track approved principal and approved repayments; the dashboard does not calculate loan interest or repayment schedules. Direct member-to-member messaging, richer task creation, and deployment configuration remain future features.
