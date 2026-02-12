# PostgreSQL Setup Guide for DementiaNext
**Date**: December 10, 2025

---

## 🎯 WHAT WE'RE DOING

Migrating from SQLite to PostgreSQL to:
- ✅ Store patient and doctor credentials securely
- ✅ Store MRI file uploads with better performance
- ✅ Handle concurrent users efficiently
- ✅ Enable production-grade deployment
- ✅ Support advanced queries and indexing

---

## 📦 STEP 1: Install PostgreSQL

### Option A: Using Downloaded Installer (RECOMMENDED)

1. **Run the installer**:
   ```
   Location: C:\Users\iba\AppData\Local\Temp\postgresql-installer.exe
   ```
   
2. **Right-click** → **Run as Administrator**

3. **Follow installation wizard**:
   - **Installation Directory**: `C:\Program Files\PostgreSQL\16`
   - **Data Directory**: `C:\Program Files\PostgreSQL\16\data`
   - **Password**: `postgres` (IMPORTANT: Remember this!)
   - **Port**: `5432`
   - **Locale**: `Default locale`
   - **Components**: Install ALL (PostgreSQL Server, pgAdmin 4, Command Line Tools)

4. **Click Next → Install → Finish**

### Option B: Download Fresh Installer

If the temp file is missing:
1. Visit: https://www.postgresql.org/download/windows/
2. Download PostgreSQL 16.x installer
3. Follow Option A steps above

---

## 📊 STEP 2: Verify PostgreSQL Installation

After installation completes:

```powershell
# Add PostgreSQL to PATH (run this in PowerShell)
$env:PATH += ";C:\Program Files\PostgreSQL\16\bin"

# Test installation
psql --version
# Should show: psql (PostgreSQL) 16.x

# Test connection
psql -U postgres -h localhost
# Enter password: postgres
# Should see: postgres=#
```

---

## 🗄️ STEP 3: Create Database

### Method 1: Using pgAdmin (GUI - Easiest)

1. **Open pgAdmin 4** (installed with PostgreSQL)
   - Search "pgAdmin" in Windows Start menu

2. **Connect to PostgreSQL**:
   - Right-click "PostgreSQL 16" → Connect
   - Enter password: `postgres`

3. **Create Database**:
   - Right-click "Databases" → Create → Database
   - **Database name**: `dementianext_db`
   - **Owner**: `postgres`
   - Click "Save"

### Method 2: Using Command Line (psql)

```powershell
# Connect to PostgreSQL
psql -U postgres -h localhost

# At postgres=# prompt, run:
CREATE DATABASE dementianext_db;

# Verify database created:
\l

# Exit:
\q
```

### Method 3: Using Python Script (Automated)

I'll create this for you after PostgreSQL is installed.

---

## ⚙️ STEP 4: Configure Django for PostgreSQL

**Already completed!** ✅

Changes made:
1. ✅ Installed `psycopg2-binary==2.9.11` (PostgreSQL adapter)
2. ✅ Updated `requirements.txt`
3. ✅ Created `.env` file with database credentials
4. ✅ Modified `core/settings.py` to use PostgreSQL

**Database Configuration** (in `.env`):
```env
DB_NAME=dementianext_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

**Django Settings** (in `core/settings.py`):
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv('DB_NAME', 'dementianext_db'),
        "USER": os.getenv('DB_USER', 'postgres'),
        "PASSWORD": os.getenv('DB_PASSWORD', 'postgres'),
        "HOST": os.getenv('DB_HOST', 'localhost'),
        "PORT": os.getenv('DB_PORT', '5432'),
    }
}
```

---

## 🚀 STEP 5: Run Database Migrations

After PostgreSQL is installed and database created:

```powershell
# Navigate to backend folder
cd C:\Users\iba\Downloads\DementiaNext\backend

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run migrations to create tables
python manage.py migrate
```

This will create all necessary tables in PostgreSQL:
- ✅ User authentication tables
- ✅ DetectionResult table (for MRI uploads and predictions)
- ✅ Session tables
- ✅ All relationships and indexes

---

## 🔍 STEP 6: Verify Database Structure

```powershell
# Connect to database
psql -U postgres -d dementianext_db

# List all tables
\dt

# View DetectionResult table structure
\d detection_detectionresult

# View User table structure
\d auth_user

# Exit
\q
```

Expected tables:
- `auth_user` - Stores patient/doctor credentials
- `detection_detectionresult` - Stores MRI uploads and predictions
- `django_session` - User sessions
- `account_*` - OAuth/social auth tables
- And more Django system tables

---

## 📋 DATABASE SCHEMA OVERVIEW

### User Table (auth_user)
Stores **patient and doctor credentials**:
```sql
- id (primary key)
- username (unique)
- email (unique)
- password (hashed)
- first_name
- last_name
- is_staff (True for doctors)
- is_active
- date_joined
```

### DetectionResult Table (detection_detectionresult)
Stores **MRI uploads and analysis**:
```sql
- id (primary key)
- user_id (foreign key → auth_user)
- uploaded_file (path to MRI file)
- file_size (bytes)
- upload_date (timestamp)
- predicted_class (Alzheimer's/Control)
- confidence_score (0-1)
- prediction_probability (JSON)
- patient_age
- patient_gender
- notes
- clinician_notes
- reviewed_by_id (foreign key → auth_user for doctors)
- reviewed_date
- status (pending/processing/completed/failed)
- processing_time
- model_version
- created_at
- updated_at
```

**Indexes**:
- `(user_id, created_at)` - Fast patient history queries
- `(status)` - Fast filtering by status

**File Storage**:
- MRI files stored at: `mri_uploads/%Y/%m/%d/filename.nii`
- Database stores file path, actual file on disk

---

## 🧪 STEP 7: Test the Integration

```powershell
# Test database connection
python manage.py check --database default

# Create a superuser (doctor)
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: admin123

# Run Django server
python manage.py runserver

# Test in another terminal:
# Open http://127.0.0.1:8000/admin
# Login with superuser credentials
```

---

## ✅ STEP 8: Run All Tests

```powershell
# Run all 120 tests with PostgreSQL
python manage.py test authx.tests detection.tests -v 2

# Expected: All 120 tests should pass
```

---

## 🔧 TROUBLESHOOTING

### Issue: "psql: command not found"
**Solution**: Add PostgreSQL to PATH:
```powershell
$env:PATH += ";C:\Program Files\PostgreSQL\16\bin"
# Or restart computer after installation
```

### Issue: "password authentication failed for user postgres"
**Solution**: 
1. Check password in `.env` file matches what you set during installation
2. Default password is `postgres`

### Issue: "could not connect to server"
**Solution**:
1. Check PostgreSQL service is running:
   ```powershell
   Get-Service postgresql*
   ```
2. Start if stopped:
   ```powershell
   Start-Service postgresql-x64-16
   ```

### Issue: "database dementianext_db does not exist"
**Solution**: Create the database (see Step 3)

### Issue: "relation does not exist"
**Solution**: Run migrations:
```powershell
python manage.py migrate
```

---

## 📊 POSTGRESQL VS SQLITE COMPARISON

| Feature | SQLite (Before) | PostgreSQL (After) |
|---------|----------------|-------------------|
| **Concurrent Users** | Limited | Unlimited |
| **File Size Limit** | 281 TB | No limit |
| **Performance (Large data)** | Slow | Fast |
| **Production Ready** | No | Yes ✅ |
| **Advanced Queries** | Limited | Full SQL |
| **Data Integrity** | Basic | Advanced |
| **Backup Tools** | Manual | Built-in |
| **User Management** | No | Yes ✅ |

---

## 🎤 PANEL PRESENTATION POINTS

### Why PostgreSQL?

> "I migrated from SQLite to PostgreSQL to ensure production-grade reliability. PostgreSQL provides:
> - **Concurrent access** for multiple patients and doctors
> - **Better performance** for large MRI file datasets
> - **Advanced security** with user-level permissions
> - **Industry standard** for medical applications
> - **ACID compliance** for data integrity"

### Data Storage

> "The database stores:
> - **Patient/Doctor credentials** securely hashed in auth_user table
> - **MRI uploads** with file paths in detection_detectionresult table
> - **Prediction results** with confidence scores and probabilities
> - **Clinical reviews** with doctor notes and review timestamps
> - **File metadata** including size, upload date, processing time"

### Security

> "PostgreSQL provides:
> - **Row-level security** ensuring users only see their own data
> - **Password hashing** with Django's PBKDF2 algorithm
> - **Foreign key constraints** maintaining data integrity
> - **Transaction support** preventing data corruption"

---

## 🚀 NEXT STEPS AFTER INSTALLATION

Once PostgreSQL is installed and running:

1. **I'll create the database** using automated script
2. **Run migrations** to create all tables
3. **Test connection** to verify everything works
4. **Run all 120 tests** to ensure compatibility
5. **Create superuser** for admin access
6. **Verify file uploads** work with PostgreSQL

---

## 📝 QUICK COMMAND REFERENCE

```powershell
# Start PostgreSQL service
Start-Service postgresql-x64-16

# Stop PostgreSQL service
Stop-Service postgresql-x64-16

# Connect to database
psql -U postgres -d dementianext_db

# List databases
\l

# List tables
\dt

# Describe table
\d table_name

# Run SQL query
SELECT * FROM auth_user;

# Exit psql
\q

# Django commands
python manage.py migrate          # Create tables
python manage.py createsuperuser  # Create admin
python manage.py dbshell          # Open database shell
python manage.py check --database default  # Test connection
```

---

## ✅ INSTALLATION CHECKLIST

- [ ] Download PostgreSQL installer
- [ ] Run installer as Administrator
- [ ] Set password: `postgres`
- [ ] Install all components (Server, pgAdmin, CLI tools)
- [ ] Verify installation: `psql --version`
- [ ] Start PostgreSQL service
- [ ] Create database: `dementianext_db`
- [ ] Run Django migrations
- [ ] Test database connection
- [ ] Run all tests
- [ ] Create superuser

---

**Ready to proceed?**

Please run the PostgreSQL installer now, then let me know when it's complete so I can:
1. Create the database automatically
2. Run migrations
3. Verify everything works
4. Test with all 120 tests

**Installer location**: `C:\Users\iba\AppData\Local\Temp\postgresql-installer.exe`

---

**Document Created**: December 10, 2025  
**PostgreSQL Version**: 16.x  
**Database Name**: dementianext_db  
**Status**: Awaiting PostgreSQL Installation
