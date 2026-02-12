# Quick Start: Model Integration

## 🚀 5-Minute Setup

### Step 1: Copy Model File (1 min)
```powershell
# Copy trained model to backend
Copy-Item "E:\FYP\best_model.pth" "E:\FYP\DementiaNext\backend\models\alzheimers_detector.pth" -Force
```

### Step 2: Setup Backend (2 min)
```powershell
cd E:\FYP\DementiaNext\backend
.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 8000
```

### Step 3: Setup Frontend (1 min)
```powershell
cd E:\FYP\DementiaNext\frontend
npm run dev
```

### Step 4: Test
1. Open `http://localhost:3000`
2. Create account
3. Navigate to Detection tab
4. Upload MRI image
5. View results!

---

## 📋 Complete Checklist

- [ ] **Model File**
  - [ ] Located at: `backend/models/alzheimers_detector.pth`
  - [ ] File size verified (should be ~100-200 MB)
  - [ ] Readable permissions confirmed

- [ ] **Backend**
  - [ ] Virtual environment activated
  - [ ] `pip install -r requirements.txt` completed
  - [ ] Database migrations applied (`python manage.py migrate`)
  - [ ] Server running on port 8000
  - [ ] Admin user created (optional)

- [ ] **Frontend**
  - [ ] Node modules installed (`npm install`)
  - [ ] Development server running on port 3000
  - [ ] Detection page accessible at `/detection`
  - [ ] Form UI displays correctly

- [ ] **Integration**
  - [ ] Authentication working (login/register)
  - [ ] File upload accepts images
  - [ ] API calls reach backend (check network tab)
  - [ ] Results display with confidence scores
  - [ ] Report download works (optional)

- [ ] **Testing**
  - [ ] Test with sample MRI image
  - [ ] Verify output confidence is >0.5 for AD
  - [ ] Check database stores results
  - [ ] View admin interface at `/admin`
  - [ ] Test with different image sizes

---

## 🔧 Essential Folders

```
backend/
├── models/
│   └── alzheimers_detector.pth  ← Your trained model here
├── detection/                     ← New API app
│   ├── models.py                  (DetectionResult, ModelMetadata)
│   ├── views.py                   (Upload & inference logic)
│   ├── serializers.py             (API serializers)
│   └── urls.py                    (Endpoints)
└── core/
    └── settings.py                (Detection app added to INSTALLED_APPS)

frontend/
└── app/
    └── detection/
        └── page.tsx               ← Updated with real API integration
```

---

## 📊 Expected Behavior

### Upload Image
**Request:**
```
POST /api/detections/upload_and_detect/
Content-Type: multipart/form-data
Authorization: Bearer <token>

Body: {file: <image>, patient_age: 72}
```

**Response:**
```json
{
  "predicted_class": "Alzheimer's Disease (AD)",
  "confidence_score": 0.9707,
  "status": "completed"
}
```

### View History
- User sees all their past detections
- Sortable by date, confidence, class
- Option to download original reports

---

## 🐛 Troubleshooting Quick Links

| Problem | Solution |
|---------|----------|
| Model not found | Verify file at `backend/models/alzheimers_detector.pth` |
| 401 Unauthorized | Check localStorage has `access_token` |
| CORS error | Verify frontend origin in `settings.CORS_ALLOWED_ORIGINS` |
| Image processing fails | Check image is RGB (not grayscale) |
| Database locked | Stop all servers, delete `db.sqlite3`, run `migrate` |
| Port 8000/3000 in use | Change port: `runserver 8001` or `PORT=3001 npm run dev` |

---

## 📚 Full Documentation

See `MODEL_INTEGRATION_GUIDE.md` for:
- ✅ Complete setup instructions
- ✅ API endpoint reference
- ✅ Database schema
- ✅ Model architecture details
- ✅ Production deployment guide

---

## ✨ Key Features

✅ **Real-time Detection**
- Upload MRI image
- Get instant AI prediction
- See confidence scores

✅ **Patient Data**
- Optional age/gender/notes
- Stored with results
- Searchable history

✅ **Results Management**
- View all past detections
- Download reports
- Track statistics

✅ **Admin Interface**
- Review detections
- Manage models
- View metrics

---

## 🎯 Success Criteria

You'll know it's working when:
1. ✅ Backend starts without errors
2. ✅ Frontend connects to backend (Network tab shows `/api/detections/upload_and_detect/`)
3. ✅ Upload page appears
4. ✅ Can select and upload an image
5. ✅ Results display with correct model output (>0.9 confidence for AD)
6. ✅ Prediction appears in detection history

**If any step fails**, check `MODEL_INTEGRATION_GUIDE.md` Troubleshooting section.

