# System Redesign - FHIR Integration & Role Separation

## ⚠️ CRITICAL: Database Reset Required

The system has been completely redesigned with:
1. Custom User model (email-based authentication)
2. Separate Patient/Doctor profiles  
3. Appointment workflow
4. FHIR DiagnosticReport generation

**This requires dropping the existing database and creating a fresh one.**

---

## 🔄 Step 1: Reset PostgreSQL Database

```powershell
# Connect to PostgreSQL
$env:PATH += ";C:\Program Files\PostgreSQL\16\bin"
psql -U postgres -h localhost -p 5433

# At postgres=# prompt:
DROP DATABASE dementianext_db;
CREATE DATABASE dementianext_db;
\q
```

---

## 🔄 Step 2: Delete Old Migrations

```powershell
cd C:\Users\iba\Downloads\DementiaNext\backend

# Delete migration files (keep __init__.py)
Remove-Item authx\migrations\*.py -Exclude __init__.py
Remove-Item detection\migrations\*.py -Exclude __init__.py
```

---

## 🔄 Step 3: Create New Migrations

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Create new migrations
python manage.py makemigrations authx
python manage.py makemigrations detection

# Apply migrations
python manage.py migrate
```

---

## 🔄 Step 4: Create Superuser

```powershell
python manage.py createsuperuser
# Email: admin@dementianext.com
# Password: admin123
# This creates an admin user automatically
```

---

## ✅ What's Changed

### Authentication:
- ❌ **Before**: Username-based login, same credentials for patient/doctor
- ✅ **After**: Email-based login, role-based separation

### Registration:
- ❌ **Before**: Simple user creation
- ✅ **After**: Creates User + PatientProfile or User + DoctorProfile based on role

### Detection Flow:
- ❌ **Before**: Patient uploads → immediate detection
- ✅ **After**: Patient books appointment → Doctor approves → Doctor runs detection → FHIR report generated

### Patient ID:
- ❌ **Before**: No patient tracking across visits
- ✅ **After**: Unique patient_id (e.g., P1733857856123), all records grouped

### Reports:
- ❌ **Before**: Simple JSON results
- ✅ **After**: HL7 FHIR R4 compliant DiagnosticReport for hospital integration

---

## 📊 New Database Tables

1. **authx_user**: Email-based auth with role field
2. **authx_patientprofile**: Patient demographics, medical history
3. **authx_doctorprofile**: Doctor credentials, specialization, availability
4. **detection_appointment**: Appointment bookings
5. **detection_detectionresult**: MRI analysis results (linked to appointments)
6. **detection_fhirdiagnosticreport**: Hospital-compatible reports

---

## 🚀 Ready to Proceed?

Once migrations are complete, I'll:
1. Update admin.py for new models
2. Create serializers and APIs
3. Update authentication endpoints
4. Create appointment management APIs
5. Implement FHIR report generation
6. Update frontend for new flow

**Shall I proceed with resetting the database?**
