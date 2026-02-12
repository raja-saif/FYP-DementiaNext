# 📋 SETUP CHECKLIST - Print This!

Print this page and check off items as you complete them.

---

## ✅ BEFORE YOU START

### System Requirements
- [ ] Python 3.8+ installed (check: `python --version`)
- [ ] Node.js 16+ installed (check: `node --version`)
- [ ] 2GB free disk space
- [ ] Modern web browser (Chrome, Firefox, Safari, or Edge)
- [ ] Best_model.pth file from training available in E:\FYP\

### Documentation
- [ ] Read START_HERE.md
- [ ] Bookmarked QUICKSTART.md
- [ ] Have COMMANDS_REFERENCE.md open in another tab

---

## 🔧 STEP 1: COPY MODEL FILE (30 seconds)

### Copy Your Trained Model
```
Time: ~30 seconds
```

**In PowerShell:**
```powershell
# Create folder
[ ] New-Item -ItemType Directory -Force -Path "E:\FYP\DementiaNext\backend\models"

# Copy file
[ ] Copy-Item "E:\FYP\best_model.pth" "E:\FYP\DementiaNext\backend\models\alzheimers_detector.pth" -Force

# Verify
[ ] Get-Item "E:\FYP\DementiaNext\backend\models\alzheimers_detector.pth"
```

**Verification:**
- [ ] File exists at `backend\models\alzheimers_detector.pth`
- [ ] File size is 100-200 MB (not too small)
- [ ] Readable permissions confirmed

---

## 🚀 STEP 2: SETUP BACKEND (2 minutes)

### Navigate to Backend
```
Time: ~1 minute
```

**In PowerShell:**
```powershell
[ ] cd E:\FYP\DementiaNext\backend
```

### Activate Virtual Environment
**If .venv exists:**
```powershell
[ ] .venv\Scripts\Activate.ps1
```

**If .venv doesn't exist:**
```powershell
[ ] python -m venv .venv
[ ] .venv\Scripts\Activate.ps1
```

### Install Dependencies
```
Time: ~1 minute
```

```powershell
[ ] pip install -r requirements.txt
```

**Watch for:**
- [ ] No error messages during installation
- [ ] "Successfully installed" message at end
- [ ] All packages listed (Django, PyTorch, etc.)

### Run Database Migrations
```
Time: ~1 minute
```

```powershell
[ ] python manage.py makemigrations detection
[ ] python manage.py migrate
```

**Expected output:**
- [ ] "Operations to perform" message
- [ ] "Running migrations" message
- [ ] "Applying" messages for database changes
- [ ] No error messages

### Verify Setup (Optional)
```powershell
[ ] python backend/verify_setup.py
```

**Check Results:**
- [ ] All checks pass (✓)
- [ ] Green checkmarks for each item
- [ ] Model file found
- [ ] Dependencies installed

---

## 🌐 STEP 3: START BACKEND SERVER (1 minute)

### Start Django Development Server

**Still in backend folder, in PowerShell:**
```
Time: ~1 minute
```

```powershell
[ ] python manage.py runserver 8000
```

**Expected output:**
```
Starting development server at http://127.0.0.1:8000/
Type 'quit' to exit
```

**Verify Backend Running:**
- [ ] "Starting development server" message appears
- [ ] No "Address already in use" error
  - If port 8000 is in use: `python manage.py runserver 8001`
- [ ] No "ModuleNotFoundError" or "ImportError"
- [ ] No connection errors
- [ ] Server running on port 8000 (or 8001 if changed)

**Keep this terminal open!**

---

## ⚛️ STEP 4: START FRONTEND SERVER (2 minutes)

### Navigate to Frontend (NEW TERMINAL!)

```
Time: ~1 minute
```

**Open a NEW PowerShell window:**
```powershell
[ ] cd E:\FYP\DementiaNext\frontend
```

### Install Dependencies (if needed)
```powershell
[ ] npm install
```

**This may take a minute or two. Expected output:**
- [ ] "added X packages" message
- [ ] No error messages
- [ ] "up to date" if already installed

### Start Frontend Server
```
Time: ~1 minute
```

```powershell
[ ] npm run dev
```

**Expected output:**
```
> Local:        http://localhost:3000
```

**Verify Frontend Running:**
- [ ] "Local: http://localhost:3000" appears
- [ ] "Ready in X.Xs" message
- [ ] No "Address already in use" error
- [ ] No "Cannot find module" errors

**Keep this terminal open!**

---

## 🧪 STEP 5: TEST THE INTEGRATION (5-10 minutes)

### Open Browser
```
Time: ~1 minute
```

- [ ] Open browser (Chrome, Firefox, Safari, or Edge)
- [ ] Navigate to `http://localhost:3000`
- [ ] DementiaNext homepage should load

**If blank page:**
- [ ] Wait 5-10 seconds (Next.js compiling)
- [ ] Refresh the page (Ctrl+R or Cmd+R)
- [ ] Check browser console (F12) for errors

### Create Account
```
Time: ~2 minutes
```

- [ ] Click "Register" button
- [ ] Enter email address
- [ ] Create password
- [ ] Click "Create Account" button
- [ ] You should be logged in automatically

**If registration fails:**
- [ ] Check backend is running (terminal 1)
- [ ] Check browser console for errors (F12)
- [ ] Make sure email format is valid

### Navigate to Detection
```
Time: ~1 minute
```

- [ ] Click "Detection" tab/link in navigation
- [ ] Page should load with upload form
- [ ] You should see:
  - [ ] File upload field
  - [ ] Optional patient age field
  - [ ] Optional gender field
  - [ ] Optional notes field
  - [ ] "Analyze MRI Image" button

**If Detection page doesn't load:**
- [ ] Check frontend console (F12)
- [ ] Check that backend is running
- [ ] Wait a few seconds and refresh

### Upload Test Image
```
Time: ~2 minutes
```

- [ ] Click "Select File" button
- [ ] Choose an MRI image (JPG or PNG)
- [ ] Image should appear in file input
- [ ] (Optional) Enter patient age
- [ ] (Optional) Enter gender (M or F)
- [ ] (Optional) Enter notes

**If file won't select:**
- [ ] Ensure it's a JPG or PNG file
- [ ] File size should be under 10MB
- [ ] Check browser permissions

### Analyze Image
```
Time: ~3 seconds for processing
```

- [ ] Click "Analyze MRI Image" button
- [ ] You should see a loading spinner
- [ ] Wait 1-3 seconds for inference
- [ ] Results should appear:
  - [ ] Classification (AD or CN)
  - [ ] Confidence score (0.0-1.0 or percentage)
  - [ ] Probability distribution
  - [ ] Timestamps

**Expected Result Format:**
```
Classification: Alzheimer's Disease (AD)
Confidence: 97.07%
Probability: AD 97.07%, CN 2.93%
```

**If no results appear:**
- [ ] Check browser console (F12) for errors
- [ ] Look for error message on page
- [ ] Check backend terminal for errors
- [ ] See COMMANDS_REFERENCE.md Troubleshooting section

---

## ✅ SUCCESS VERIFICATION

### Green Lights (Everything Working!)

Check all that apply:
- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Homepage loads at localhost:3000
- [ ] Can create account and log in
- [ ] Detection page loads with form
- [ ] Can upload MRI image
- [ ] Model predicts with confidence
- [ ] Results display with scores
- [ ] Prediction appears in history

### If You See All Checkmarks Above

## 🎉 CONGRATULATIONS! 🎉

**Your integration is working!**

Your Alzheimer's detection model is successfully:
- ✅ Running on the backend
- ✅ Connected to the frontend
- ✅ Processing images
- ✅ Making predictions
- ✅ Storing results

---

## 📊 NEXT STEPS

### Immediate
- [ ] Test with a few more images
- [ ] Verify predictions look reasonable
- [ ] Check detection history is growing
- [ ] Try different patient metadata

### Short Term
- [ ] Visit admin at http://127.0.0.1:8000/admin/
  - [ ] Username: admin
  - [ ] Password: (what you set up)
- [ ] Review stored detections in admin
- [ ] View model metadata
- [ ] Check statistics

### Medium Term
- [ ] Read full documentation (MODEL_INTEGRATION_GUIDE.md)
- [ ] Experiment with threshold changes
- [ ] Add more test images
- [ ] Monitor inference times
- [ ] Test with team members

### Production
- [ ] Follow production deployment guide
- [ ] Set up PostgreSQL (not SQLite)
- [ ] Configure ALLOWED_HOSTS
- [ ] Enable HTTPS
- [ ] Set up monitoring and logging

---

## 🆘 TROUBLESHOOTING QUICK REFERENCE

### Problem: Port Already in Use

**Error:** "Address already in use"

**Solution:**
```powershell
# Kill existing process on port 8000
taskkill /PID <PID> /F

# OR use different port
python manage.py runserver 8001
npm run dev -- -p 3001
```

### Problem: "Cannot find module"

**Error:** Various module not found errors

**Solution:**
```powershell
cd backend
pip install -r requirements.txt

cd ../frontend
npm install
```

### Problem: Database errors

**Error:** "Database locked" or migration errors

**Solution:**
```powershell
cd backend
Remove-Item db.sqlite3
python manage.py migrate
```

### Problem: Model not loading

**Error:** "Model file not found"

**Solution:**
```powershell
# Verify file exists
Get-Item "backend\models\alzheimers_detector.pth"

# If not, copy it
Copy-Item "..\best_model.pth" "backend\models\alzheimers_detector.pth" -Force
```

### Problem: API connection fails

**Error:** "Failed to fetch" or CORS errors

**Solution:**
- [ ] Ensure backend is running
- [ ] Check Network tab in browser (F12)
- [ ] Verify URL is correct (http://127.0.0.1:8000)
- [ ] Look for errors in backend terminal

---

## 📞 NEED HELP?

| Resource | Location |
|----------|----------|
| Quick Commands | COMMANDS_REFERENCE.md |
| Architecture | VISUAL_GUIDE.md |
| Technical Details | MODEL_INTEGRATION_GUIDE.md |
| Code Examples | CODE_SNIPPETS.md |
| File Inventory | FILE_MANIFEST.md |
| Status Report | INTEGRATION_COMPLETE.md |

---

## 🎯 FINAL CHECKLIST

Before declaring success, verify:

```
BACKEND
- [ ] Virtual environment activated
- [ ] Dependencies installed
- [ ] Database migrations complete
- [ ] Server running on port 8000
- [ ] No errors in terminal

FRONTEND
- [ ] Dependencies installed
- [ ] Server running on port 3000
- [ ] No build errors
- [ ] Page loads at localhost:3000

MODEL
- [ ] File at backend/models/alzheimers_detector.pth
- [ ] File size reasonable (100-200 MB)
- [ ] Model loads without errors

FUNCTIONALITY
- [ ] Can create account
- [ ] Can log in
- [ ] Detection page loads
- [ ] Can upload image
- [ ] Results display
- [ ] Confidence score shown

INTEGRATION
- [ ] Frontend connects to backend
- [ ] API calls succeed (check Network tab F12)
- [ ] Results saved to database
- [ ] Detection history shows results
- [ ] Admin interface accessible
```

---

## ⏱️ TIME SUMMARY

| Task | Time | Status |
|------|------|--------|
| Copy model | 30 sec | ⏳ |
| Backend setup | 2 min | ⏳ |
| Start servers | 2 min | ⏳ |
| Testing | 5 min | ⏳ |
| **TOTAL** | **~10 minutes** | ⏳ |

---

## 🎊 COMPLETION CERTIFICATE

When you see your first successful detection result:

```
┌─────────────────────────────────────────────┐
│  🎉 INTEGRATION SUCCESSFUL 🎉              │
│                                             │
│  Model: ResNet-34                           │
│  AUC: 0.9707                                │
│  Status: ✅ WORKING                         │
│                                             │
│  Date: ____________                         │
│  User: ____________                         │
│                                             │
│  Ready for deployment!                      │
└─────────────────────────────────────────────┘
```

---

**Print this page, check off items as you complete them, and celebrate when you're done!** 🎉

**You've integrated a state-of-the-art AI model into a professional web application!** 🚀

