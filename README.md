# DementiaNext

A clean two-tier setup:
- `backend/` — Django REST API (DRF + SimpleJWT + CORS)
- `frontend/` — Next.js (React 18 + Tailwind CSS)

This is the only README. Follow it to run everything.

## Prerequisites
- Python 3.10+
- Node.js 18+

## 1) Start the Backend (Django)

### Windows (PowerShell)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

### Linux/macOS
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

Backend will run on http://127.0.0.1:8000

### API endpoints used by the frontend
- POST `/api/register`  → `{ token, user }`
- POST `/api/login`     → `{ token, user }`
- POST `/api/auth/verify` → `{ user }`
- POST `/api/auth/google` → `{ token, user }` (Google OAuth)

## 2) Start the Frontend (Next.js)
Open a new terminal:

### Windows (PowerShell)
```powershell
cd frontend
@"
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
"@ | Out-File -Encoding UTF8 .env.local
npm install
npm run dev
```

### Linux/macOS
```bash
cd frontend
echo "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000" > .env.local
npm install
npm run dev
```

Frontend will run on http://localhost:3000

## 3) Google OAuth Setup (Optional)

Google Sign-In is integrated but requires configuration. Follow these steps to enable it:

### Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth 2.0 Client ID**
5. Configure the OAuth consent screen if prompted
6. For **Application type**, select **Web application**
7. Add authorized JavaScript origins:
   - `http://localhost:3000`
   - `http://127.0.0.1:3000`
8. Under **Authorized redirect URIs**, add entries that match how you run the app:
   - Same host you use in the browser, e.g. `http://localhost:3000` **and** `http://127.0.0.1:3000` if you switch between them.
   - If you use **NextAuth** in this repo (`/api/auth/[...nextauth]`), also add:
     - `http://localhost:3000/api/auth/callback/google`
     - `http://127.0.0.1:3000/api/auth/callback/google`
     - Plus your production callback URL when you deploy.
9. Click **Create** and copy your **Client ID** and **Client Secret**

### Configure Backend (Django)

Add these environment variables before starting the Django server:

#### Windows (PowerShell)
```powershell
cd backend
.venv\Scripts\Activate.ps1

# Set Google OAuth credentials
$env:GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET = "your-client-secret"

# Run migrations for social auth tables
python manage.py migrate

# Start server
python manage.py runserver 8000
```

#### Linux/macOS
```bash
cd backend
source .venv/bin/activate

# Set Google OAuth credentials
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"

# Run migrations for social auth tables
python manage.py migrate

# Start server
python manage.py runserver 8000
```

### Configure Frontend (Next.js)

Update your `frontend/.env.local` file:

#### Windows (PowerShell)
```powershell
cd frontend
@"
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
"@ | Out-File -Encoding UTF8 .env.local
```

#### Linux/macOS
```bash
cd frontend
cat > .env.local << EOF
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
EOF
```

### Test Google Login

1. Start both backend and frontend servers
2. Open the app using the **same origin** you added in Google Console (e.g. `http://localhost:3000/login`, not `127.0.0.1`, unless that origin is also listed).
3. Use the **Sign in with Google** button (Google-hosted widget on the login page).
4. Complete Google authentication; you should land on the patient or doctor dashboard.

**Note**: If Google OAuth is not configured, users can still use email/password authentication.

## Troubleshooting

### Port Issues

#### Windows (PowerShell)
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process by PID (replace 1234 with actual PID)
taskkill /PID 1234 /F
```

#### Linux/macOS
```bash
lsof -ti:8000,3000,3001,3002 | xargs -r kill -9
```

### Backend Health Check
Verify backend quickly:

#### Windows (PowerShell)
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/auth/verify" `
  -Method POST `
  -Headers @{'Content-Type'='application/json'} `
  -Body '{"token":"invalid"}'
```

#### Linux/macOS
```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/verify \
  -H 'Content-Type: application/json' -d '{"token":"invalid"}'
```

### Google OAuth Issues

**Error 400: `redirect_uri_mismatch`**

Google compares the **exact** redirect URL and **JavaScript origins** to your OAuth client settings.

- Add **Authorized JavaScript origins** for every origin you use: `http://localhost:3000`, `http://127.0.0.1:3000`, and your production `https://` origin (scheme + host + port, no path).
- If you sign in with **NextAuth** (`signIn('google')` or the NextAuth callback route), add the matching **Authorized redirect URIs** (see step 8 above). The login page uses **Google Identity Services** (JWT) and normally only needs correct **JavaScript origins**; older OAuth token flows required extra redirect URIs.
- After changing Google Console settings, wait a minute and hard-refresh the app.

**"Google OAuth not configured" error:**
- Ensure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in backend environment
- Ensure `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set in `frontend/.env.local`
- Restart both backend and frontend after setting environment variables

**Google Sign-In button not appearing:**
- Check browser console for JavaScript errors
- Ensure Google Identity Services script is loading (check Network tab)
- Clear browser cache and reload

**"Invalid Google token" error:**
- Verify your Client ID matches exactly between frontend and backend
- Check that your domain (localhost:3000) is authorized in Google Cloud Console
- Try creating a new OAuth 2.0 Client ID

**Database errors after adding Google OAuth:**

#### Windows (PowerShell)
```powershell
cd backend
.venv\Scripts\Activate.ps1
python manage.py migrate
```

#### Linux/macOS
```bash
cd backend
source .venv/bin/activate
python manage.py migrate
```

## Project Layout
```
backend/        # Django project (core/, authx/)
frontend/       # Next.js app (app/, components/, contexts/, lib/)
README.md       # This file
```
