# Zoho Books Integration Setup Guide

This guide walks you through setting up the Zoho Books integration for timesheets in the opero app.

## Prerequisites

- A Zoho Books account with Projects enabled
- Administrator access to your Frappe/ERPNext instance
- Basic understanding of OAuth2 authentication

## Step 1: Create a Zoho Books OAuth App

1. Log in to your Zoho Books account
2. Go to **Settings** → **Setup** → **API & Auth** → **OAuth**
3. Click **Create** to create a new OAuth application
4. Fill in the following details:
   - **Client Name**: Enter a name (e.g., "Frappe ERPNext")
   - **Client Type**: Select "Web-based"
   - **Authorized Redirect URIs**: Enter the callback URL from your Frappe instance
     - Format: `https://your-frappe-domain.com/api/method/opero.zoho_books.oauth_callback`
     - Add one URI per environment if you reuse the same Zoho client for dev and production

5. Click **Create**
6. Copy the following information (you'll need it in the next step):
   - **Client ID**
   - **Client Secret**

## Step 2: Get Your Organization ID

1. In Zoho Books, go to **Settings** → **Organization**
2. Note the **Organization ID** displayed at the top

## Step 3: Configure Zoho Books Settings in Frappe

1. In your Frappe instance, go to **Zoho Books Settings** (search in the awesome bar)
2. Fill in the following fields:

### OAuth Configuration Section
- **Enabled**: Check this box to enable the integration
- **Client ID**: Paste the Client ID from Step 1
- **Client Secret**: Paste the Client Secret from Step 1
- **Authorization URI**: `https://accounts.zoho.com/oauth/v2/auth` (default)
- **Token URI**: `https://accounts.zoho.com/oauth/v2/token` (default)
- **Redirect URI**: Auto-generated from the current site as `https://your-frappe-domain.com/api/method/opero.zoho_books.oauth_callback`
- **Scope**: `projects` (default)

### Token Storage Section
- **Organization ID**: Paste your Organization ID from Step 2
- Other fields will be auto-populated after authentication

### Sync Settings Section
- **Fallback Project ID**: (Optional) Enter a default Zoho Books project ID to use for time logs without a project assignment. You can find project IDs in Zoho Books under Projects.

3. Click **Save** (you won't authenticate yet if you haven't configured the OAuth callback)

## Step 4: Personnel Mapping

Before syncing timesheets, you need to map each personnel (staff or consultant) to their corresponding Zoho Books user ID.

1. In the Zoho Books Settings form, scroll to the **Personnel Mapping** table
2. For each person that will have timesheets synced:
   - Click **Add Row**
   - **Personnel ID**: Enter the identifier used in your system (Employee ID, Consultant ID, Email, User ID, etc.)
   - **Zoho User ID**: Enter the user's ID from Zoho Books
     - To find user IDs, go to Zoho Books → **Settings** → **Users & Roles** → **Users**
     - The user ID is typically visible in the user list or can be found in the user details

3. Click **Save** to save the settings

Example mapping:
| Personnel ID | Zoho User ID | Notes |
|------------|------------|-------|
| EMP-001 | 123456789 | Staff member |
| CONS-042 | 987654321 | Consultant |
| john@company.com | 111222333 | Email-based ID |

## Step 5: OAuth Authentication (Advanced)

If you want to implement full OAuth2 authentication instead of manual token entry:

1. Register this exact callback URI in Zoho Books: `https://your-frappe-domain.com/api/method/opero.zoho_books.oauth_callback`
2. If you use the same Zoho client across multiple environments, add each environment's callback URI in Zoho
3. The Opero integration exchanges the authorization code for tokens automatically after redirect

Alternatively, use Zoho Books' token generation tool:
1. Go to Zoho Books → **Settings** → **API & Auth** → **Self-Signed Tokens**
2. Generate a token for your account
3. This token acts as an access token (though it doesn't expire like normal OAuth tokens)

## Step 6: Testing the Integration

1. Create a new Timesheet in your Frappe instance
2. Add Time Log entries with:
   - **Activity Type**: Required
   - **Project**: Recommended (or ensure a fallback project is configured)
   - **Task**: Optional
   - **Hours**: Required
   - **Description**: Optional
   - **Is Billable**: Optional (defaults to billable)

3. **Submit** the timesheet
4. Check your Zoho Books account:
   - Go to **Projects** → **Projects** → Open the project
   - Check the **Time Entries** tab to verify the time entries were synced

## Troubleshooting

### "No Zoho user ID mapping found for employee"
- **Issue**: A personnel entry has no mapping in the Personnel Mapping table
- **Solution**: Add the personnel to the Personnel Mapping table with their Zoho user ID

### "No project ID available for time log"
- **Issue**: A time log has no project and no fallback project is configured
- **Solution**: Either assign a project to the time log, or configure a fallback project ID in settings

### "Failed to refresh access token"
- **Issue**: The refresh token has expired or is invalid
- **Solution**: Re-authenticate with Zoho Books to get a new refresh token

### Sync appears to work but entries don't show in Zoho Books
- **Verify** the organization ID is correct
- **Verify** the project IDs are correct (especially the fallback)
- **Check** that the employee's Zoho user ID matches their actual ID in Zoho Books
- **Check** Frappe error logs for detailed error messages: `frappe logs show -n 100`

## Manual Testing Steps

1. Open browser console on the Timesheet form after submit
2. Check for any JavaScript errors
3. In Frappe, go to **Setup** → **System Settings** → **Developer Mode** if you want to see detailed debug info
4. Check the Frappe error log: `/app/error-log`

## Sync Behavior

- **On Submit**: Creates a new time entry in Zoho Books
- **On Amendment** (after cancel + resubmit): Updates the existing time entry in Zoho Books
- **On Cancel**: Deletes the time entry from Zoho Books

## API Endpoint Reference

The integration uses the Zoho Books v3 API:
- **Create Time Entry**: `POST /projects/timeentries`
- **Update Time Entry**: `PUT /projects/timeentries/{time_entry_id}`
- **Delete Time Entry**: `DELETE /projects/timeentries/{time_entry_id}`

For more details, see: https://www.zoho.com/books/api/v3/
