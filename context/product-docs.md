# CloudSync Pro — Product Documentation

## 1. Getting Started

### Creating Your Account
1. Go to app.cloudsyncpro.com and click **Sign Up**
2. Enter your work email and create a password (min 8 chars, 1 uppercase, 1 number)
3. Verify your email — check spam if not received within 2 minutes
4. Create or join a team workspace

### Resetting Your Password
1. On the login page, click **Forgot Password**
2. Enter your registered email address
3. Check your inbox for a reset link (valid for 30 minutes)
4. Click the link and enter a new password
5. If the link expires, repeat from step 1
**Note**: Password reset emails come from noreply@cloudsyncpro.com

### Logging In with SSO
Enterprise plan customers can use Google Workspace or Microsoft 365 SSO.
Contact your workspace admin to enable SSO. Individual SSO setup is not supported.

---

## 2. Task Manager

### Creating a Task
1. Click **+ New Task** in any project view
2. Enter a task title (required)
3. Optionally add: description, assignee, due date, priority (Low/Medium/High/Critical), labels
4. Press **Enter** or click **Create**

### Assigning Tasks
- Click the task, then click the **Assignee** field
- Search by name or email
- Multiple assignees are supported on Growth and Enterprise plans

### Task Statuses
Tasks move through: **To Do → In Progress → Review → Done**
Custom statuses available on Growth/Enterprise plans.

### Subtasks
Click a task → **Add Subtask** button. Subtasks inherit the parent's project but can have independent assignees and due dates.

### Bulk Actions
Select multiple tasks using the checkbox, then use the bulk action bar to: assign, set due date, move, archive, or delete.

---

## 3. File Sync

### Uploading Files
- Drag and drop files into any project or task
- Use the **Upload** button in the Files tab
- Max file size: **500 MB** per file
- Supported formats: All common formats; executables (.exe, .bat) are blocked

### File Version History
- Click any file → **Version History** tab
- Up to 30 days of history retained on all plans
- Click any version to **preview** or **restore**
- Restoring creates a new version (does not overwrite)

### Storage Limits
| Plan | Storage |
|------|---------|
| Starter | 10 GB per workspace |
| Growth | 100 GB per workspace |
| Enterprise | 1 TB+ (custom) |
If you exceed your limit, uploads are blocked. Delete files or upgrade your plan.

### Sharing Files
- Click a file → **Share** → copy link or enter email addresses
- Shared links can be set to: view only, comment, or edit
- Links expire after 30 days by default (configurable in Enterprise)

---

## 4. Team Chat

### Creating a Channel
1. Click **+ New Channel** in the sidebar
2. Enter a channel name (no spaces; use hyphens)
3. Set visibility: Public (all team members) or Private (invited members only)
4. Add members (optional at creation)

### Direct Messages
Click **+ New DM** → search for a team member → start messaging.
Group DMs support up to 9 members.

### Notifications
Go to **Settings → Notifications** to configure:
- Desktop/mobile push notifications
- Email digest (daily/weekly)
- @mention alerts (always on by default)

### Search
Use `Ctrl+K` (Windows/Linux) or `Cmd+K` (Mac) to search messages, tasks, and files.
Search supports filters: `from:name`, `in:#channel`, `before:date`, `after:date`

---

## 5. Analytics Dashboard

### Accessing Analytics
Go to **Workspace → Analytics** (Growth and Enterprise plans only).

### Available Reports
- **Sprint Velocity**: Average tasks completed per sprint over last 8 sprints
- **Team Activity**: Daily active contributors and task update frequency
- **Task Completion Rate**: Percentage of tasks completed by due date
- **Overdue Report**: Tasks past their due date, grouped by assignee

### Exporting Data
Click **Export** on any report → choose CSV or PDF.
CSV exports include all data fields. PDF exports match the on-screen view.
If the **Export** button is greyed out, check your plan — CSV export requires Growth+.

---

## 6. API Access

### Getting Your API Key
1. Go to **Settings → Developer → API Keys**
2. Click **Generate New Key**
3. Name your key and set an expiry date (optional; default: never)
4. Copy the key immediately — it is shown only once

### Authentication
All API requests require the header: `Authorization: Bearer YOUR_API_KEY`

### Rate Limits
| Plan | Rate Limit |
|------|-----------|
| Starter | 100 requests/minute |
| Growth | 500 requests/minute |
| Enterprise | 2,000 requests/minute |
If you exceed the rate limit, you receive a `429 Too Many Requests` response.
Wait 60 seconds and retry. Consider implementing exponential backoff.

### Webhooks
1. Go to **Settings → Developer → Webhooks**
2. Click **Add Webhook**
3. Enter your endpoint URL (must be HTTPS)
4. Select events to subscribe to: `task.created`, `task.updated`, `file.uploaded`, etc.
5. We send a POST request with a JSON payload and an `X-CloudSync-Signature` header

### API Documentation
Full reference: docs.cloudsyncpro.com/api

---

## 7. Account and Workspace Settings

### Changing Your Email Address
1. Go to **Profile → Account Settings**
2. Click **Change Email**
3. Enter new email and your current password
4. Verify the new email (link sent to the new address)

### Two-Factor Authentication (2FA)
1. Go to **Profile → Security**
2. Click **Enable 2FA**
3. Scan the QR code with an authenticator app (Google Authenticator, Authy)
4. Enter the 6-digit code to confirm
5. Save your backup codes in a safe place

### Workspace Roles
| Role | Permissions |
|------|------------|
| Owner | Full access; billing; delete workspace |
| Admin | Manage members, projects, settings |
| Member | Create/edit tasks; upload files; chat |
| Guest | View only; can comment on shared items |

### Removing a Team Member
Go to **Workspace Settings → Members** → find the member → **Remove**.
Their tasks are reassigned to Unassigned. Their files remain.

---

## 8. Troubleshooting

### Sync Issues (files not updating)
1. Check your internet connection
2. Log out and back in
3. Clear browser cache (Ctrl+Shift+Delete)
4. Try a different browser
5. If issue persists, contact support with your workspace ID

### App Not Loading
1. Check status.cloudsyncpro.com for outages
2. Disable browser extensions (especially ad blockers)
3. Try incognito/private mode
4. Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

### Can't Find a Task
- Check the project's **Archive** section (tasks are archived, not deleted, when marked Done for 30+ days)
- Use global search (Ctrl+K)
- Check if you have project access — ask your workspace admin

### Email Notifications Not Arriving
1. Check spam/junk folder (whitelist noreply@cloudsyncpro.com)
2. Verify notification settings in **Profile → Notifications**
3. Check if your email provider is blocking our domain
