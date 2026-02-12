# DementiaNext Model Integration - Command Reference

## Windows PowerShell Commands

### Prerequisites
Ensure you have:
- Python 3.8+ installed
- Node.js 16+ installed
- Your trained model file: `best_model.pth`

---

## 1. COPY MODEL FILE

Copy your trained model to the backend:

```powershell
# Create models directory if it doesn't exist
New-Item -ItemType Directory -Force -Path "E:\FYP\DementiaNext\backend\models"

# Copy your trained model
Copy-Item "E:\FYP\best_model.pth" "E:\FYP\DementiaNext\backend\models\alzheimers_detector.pth" -Force
```

**Verify it worked:**
```powershell
Get-Item "E:\FYP\DementiaNext\backend\models\alzheimers_detector.pth"
```

---

## 2. SETUP BACKEND

### Activate Virtual Environment
```powershell
cd E:\FYP\DementiaNext\backend
.venv\Scripts\Activate.ps1
```

If `.venv` doesn't exist, create it:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install Dependencies
```powershell
pip install -r requirements.txt
```

### Run Database Migrations
```powershell
python manage.py makemigrations detection
python manage.py migrate
```

### Create Admin User (Optional)
```powershell
python manage.py createsuperuser
# Follow prompts to set username, email, password
```

### Run Development Server
```powershell
python manage.py runserver 8000
```

**Expected output:**
```
Starting development server at http://127.0.0.1:8000/
Type 'quit' to exit
```

---

## 3. SETUP FRONTEND

### Navigate to Frontend Directory
```powershell
cd E:\FYP\DementiaNext\frontend
```

### Install Dependencies (if not already done)
```powershell
npm install
```

### Run Development Server
```powershell
npm run dev
```

**Expected output:**
```
> Local:        http://localhost:3000
> Ready in 2s
```

---

## 4. TEST THE INTEGRATION

### Open Your Browser
- Frontend: `http://localhost:3000`
- Backend Admin: `http://127.0.0.1:8000/admin`
- API: `http://127.0.0.1:8000/api/detections/`

### Test Steps
1. Go to `http://localhost:3000`
2. Click "Register" and create an account
3. Navigate to "Detection" tab
4. Upload an MRI image (JPG or PNG)
5. (Optional) Add patient age/gender/notes
6. Click "Analyze MRI Image"
7. View results with confidence score
8. (Optional) Download report

---

## 5. VERIFY SETUP

Run the verification script:

```powershell
cd E:\FYP\DementiaNext\backend
python verify_setup.py
```

This checks:
- Python version
- Backend structure
- Model file exists
- Required packages installed
- Database setup

---

## USEFUL COMMANDS

### Stop Development Servers
```powershell
# Backend: Ctrl+C in the terminal
# Frontend: Ctrl+C in the terminal
```

### Database Reset (if needed)
```powershell
cd E:\FYP\DementiaNext\backend
# Delete database
Remove-Item db.sqlite3
# Recreate
python manage.py migrate
```

### View Database Contents
```powershell
cd E:\FYP\DementiaNext\backend
python manage.py shell
```

```python
from detection.models import DetectionResult
DetectionResult.objects.all().count()  # Show number of detections
exit()
```

### Check Installed Packages
```powershell
cd E:\FYP\DementiaNext\backend
pip list
```

### Run Specific Test
```powershell
python manage.py test detection.tests
```

### Create Superuser from Command Line
```powershell
python manage.py createsuperuser --username admin --email admin@test.com
# Then enter password when prompted
```

---

## TROUBLESHOOTING COMMANDS

### Check if Port is in Use
```powershell
# Port 8000
netstat -ano | findstr :8000

# Port 3000
netstat -ano | findstr :3000
```

### Kill Process on Port
```powershell
# Replace PID with the process ID from above
taskkill /PID <PID> /F

# Or use different port
python manage.py runserver 8001
npm run dev -- -p 3001
```

### Check Django Settings
```powershell
cd E:\FYP\DementiaNext\backend
python manage.py shell
from django.conf import settings
print(settings.INSTALLED_APPS)
exit()
```

### View Migration Status
```powershell
python manage.py showmigrations
```

### Fake Migration (if needed)
```powershell
python manage.py migrate detection --fake
```

---

## ENVIRONMENT VARIABLES

If using `.env` file, ensure `backend/.env` contains:

```
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,localhost:3000

# Database
DATABASE_URL=sqlite:///./db.sqlite3

# Model
MODEL_PATH=models/alzheimers_detector.pth

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Upload
MAX_UPLOAD_SIZE=10485760  # 10MB in bytes
```

Load in `settings.py` with `python-dotenv`:
```python
from dotenv import load_dotenv
import os
load_dotenv()
```

---

## MONITORING LOGS

### Django Debug Toolbar (Optional)
```powershell
pip install django-debug-toolbar
```

Add to `backend/core/settings.py`:
```python
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = ["127.0.0.1"]
```

### Browser DevTools
- Open Developer Tools (F12)
- Network tab: See API calls
- Console: Check for errors
- Application: View localStorage tokens

---

## NEXT STEPS AFTER SETUP

1. ✅ Test with different image sizes
2. ✅ Test with multiple users
3. ✅ Review admin interface
4. ✅ Check database for stored results
5. ✅ Test report download functionality
6. ✅ Monitor inference time and accuracy
7. ✅ Set up logging for production
8. ✅ Configure ALLOWED_HOSTS for deployment

---

## QUICK START (One-Go)

Copy and paste to run everything:

```powershell
# Setup backend
cd E:\FYP\DementiaNext\backend
.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 8000 &

# Setup frontend (new terminal)
cd E:\FYP\DementiaNext\frontend
npm run dev
```

Then open:
- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000/admin`

