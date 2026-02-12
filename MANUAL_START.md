# Manual Server Startup Guide

## 📋 Prerequisites - Add Google OAuth Credentials FIRST

### Step 1: Edit Backend .env File

```bash
cd /home/owais/DementiaNext/backend
nano .env
```

Replace the empty values with your actual credentials:

```
DEBUG=True
SECRET_KEY=django-insecure-uj9sdorsusp)9^a^=&gi$4il%$ew7ue7sp69mfa4ldatz-k=h*

# Google OAuth Configuration - Add your credentials here
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
```

**Save**: Ctrl+O, Enter, Ctrl+X

### Step 2: Edit Frontend .env.local File

```bash
cd /home/owais/DementiaNext/frontend
nano .env.local
```

Make sure it has:

```
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com
```

**Save**: Ctrl+O, Enter, Ctrl+X

---

## 🚀 Starting Servers Manually

### Terminal 1: Backend (Django)

```bash
# Navigate to backend
cd /home/owais/DementiaNext/backend

# Activate virtual environment (IMPORTANT!)
source .venv/bin/activate

# You should see (.venv) in your prompt, NOT (preprocessing)

# Start Django server
python manage.py runserver 8000
```

**Keep this terminal open!** Don't close it.

You should see:
```
Watching for file changes with StatReloader
Performing system checks...
System check identified no issues (0 silenced).
...
Django version X.X.X, using settings 'core.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

---

### Terminal 2: Frontend (Next.js)

Open a **NEW terminal** and run:

```bash
# Navigate to frontend
cd /home/owais/DementiaNext/frontend

# Start Next.js dev server
npm run dev
```

**Keep this terminal open too!**

You should see:
```
  ▲ Next.js 14.2.33
  - Local:        http://localhost:3000
  
 ✓ Ready in 3.2s
```

---

## 🌐 Access Your Application

Open browser: **http://localhost:3000/login**

Google Sign-In should now work!

---

## 🛑 Stopping Servers

In each terminal, press: **Ctrl+C**

Or from another terminal:
```bash
lsof -ti:8000 | xargs kill -9  # Stop backend
lsof -ti:3000 | xargs kill -9  # Stop frontend
```

---

## ⚠️ IMPORTANT NOTES

### Always Use `.venv` NOT conda!

**WRONG:**
```bash
conda activate preprocessing  # ❌ NO!
python manage.py runserver
```

**CORRECT:**
```bash
source .venv/bin/activate  # ✅ YES!
python manage.py runserver 8000
```

Check your prompt:
- ✅ Good: `(.venv) owais@computer:~/DementiaNext/backend$`
- ❌ Bad: `(preprocessing) owais@computer:~/DementiaNext/backend$`

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'allauth'"
**Problem**: You're using conda environment instead of .venv

**Solution**: 
```bash
# Make sure you see (.venv) not (preprocessing)
source .venv/bin/activate
python manage.py runserver 8000
```

### Google OAuth "Something went wrong"
**Problem**: Credentials not set in .env files

**Solution**: 
1. Make sure you edited `backend/.env` with your actual credentials
2. Make sure you edited `frontend/.env.local` with your actual Client ID
3. Restart both servers (Ctrl+C and start again)

### "Port already in use"
**Problem**: Server is already running

**Solution**:
```bash
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

### Google OAuth "Invalid client"
**Problem**: Client ID doesn't match or has typos

**Solution**:
1. Double-check your Client ID in both files
2. Make sure there are no extra spaces
3. Make sure you copied the FULL Client ID (ends with .apps.googleusercontent.com)

---

## ✅ Quick Checklist

Before starting servers:
- [ ] Edited `backend/.env` with Google credentials
- [ ] Edited `frontend/.env.local` with Google Client ID
- [ ] Using `source .venv/bin/activate` (NOT conda)
- [ ] Seeing `(.venv)` in terminal prompt

After starting:
- [ ] Backend running on http://127.0.0.1:8000
- [ ] Frontend running on http://localhost:3000
- [ ] Both terminals still open
- [ ] Login page loads in browser




