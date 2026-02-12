# Model Integration Guide

## Overview

Your trained Alzheimer's Disease detection model has been integrated into the DementiaNext web application. The integration uses a Django REST API backend to serve the model and a Next.js frontend to provide the user interface.

## Architecture

```
Frontend (Next.js) ←→ Backend (Django) ←→ ML Model (PyTorch)
                       Detection API
```

## Backend Setup

### 1. Copy Your Model File

Copy your trained model file to the backend:

```powershell
# Create models directory
New-Item -ItemType Directory -Force -Path "E:\FYP\DementiaNext\backend\models"

# Copy your trained model
# Replace the path with your actual model file location
Copy-Item "E:\FYP\best_model.pth" "E:\FYP\DementiaNext\backend\models\alzheimers_detector.pth"
```

### 2. Update requirements.txt (if needed)

The backend already includes PyTorch dependencies. If you need additional packages, add them to `backend/requirements.txt` and run:

```powershell
cd backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Run Migrations

```powershell
cd backend
python manage.py makemigrations detection
python manage.py migrate
python manage.py runserver 8000
```

### 4. Create Admin User (Optional)

```powershell
python manage.py createsuperuser
```

## Frontend Setup

The detection page is already configured to use the backend API. No additional setup needed!

## API Endpoints

### Upload and Detect
**POST** `/api/detections/upload_and_detect/`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Body:**
```
- uploaded_file: (File) - MRI image
- patient_age: (integer, optional) - Patient age
- patient_gender: (string, optional) - M or F
- notes: (string, optional) - Clinical notes
```

**Response:**
```json
{
  "id": 1,
  "status": "completed",
  "predicted_class": "Alzheimer's Disease (AD)",
  "confidence_score": 0.9707,
  "prediction_probability": {
    "Alzheimer's Disease (AD)": 0.9707,
    "Control (CN)": 0.0293
  },
  "processing_time": 2.345,
  "analysis_details": {
    "raw_output": 3.456,
    "sigmoid_probability": 0.9707,
    "threshold_used": 0.5,
    "model_version": "ResNet-34-v1.0"
  },
  "created_at": "2025-12-07T15:30:00Z",
  "patient_age": 72,
  "patient_gender": "M",
  "notes": "Memory difficulties reported"
}
```

### Get Detection History
**GET** `/api/detections/`

Returns list of all detections for the current user.

### Get Detection Statistics
**GET** `/api/detections/stats/`

Returns user statistics:
```json
{
  "total_detections": 10,
  "completed": 9,
  "alzheimers_cases": 3,
  "control_cases": 6,
  "ad_percentage": 33.33
}
```

### Get Active Models
**GET** `/api/models/`

Returns metadata about available models.

## Model Details

### ResNet-34 Architecture
- **Input**: 224×224 RGB images
- **Backbone**: ResNet-34 (pretrained on ImageNet)
- **Head**: Linear layer (512 → 1)
- **Output**: Sigmoid probability (0-1)
- **Threshold**: 0.5 (default)

### Performance Metrics
- **AUC**: 0.9707
- **Accuracy**: 91.84%
- **Sensitivity**: 88.46%
- **Specificity**: 95.65%
- **F1 Score**: 0.92

### Model Weights
- File: `backend/models/alzheimers_detector.pth`
- Format: PyTorch state_dict
- Size: ~100-200 MB (approx)

## Testing the Integration

### 1. Start Backend
```powershell
cd E:\FYP\DementiaNext\backend
.venv\Scripts\Activate.ps1
python manage.py runserver 8000
```

### 2. Start Frontend
```powershell
cd E:\FYP\DementiaNext\frontend
npm run dev
```

### 3. Test Detection
1. Navigate to `http://localhost:3000/detection`
2. Create an account or log in
3. Upload an MRI image
4. Click "Analyze MRI Image"
5. View results and download report

## Database Models

### DetectionResult
Stores information about each detection:
- `user`: User who ran the detection
- `uploaded_file`: Path to uploaded image
- `status`: pending/processing/completed/failed
- `predicted_class`: AD or CN
- `confidence_score`: 0-1
- `prediction_probability`: JSON with class probabilities
- `patient_age`: Optional age
- `patient_gender`: Optional gender
- `notes`: Optional clinical notes
- `processing_time`: Time taken for inference
- `created_at`: Timestamp

### ModelMetadata
Stores model version information:
- `name`: Model name
- `version`: Version string
- `architecture`: e.g., "ResNet-34"
- `accuracy`: Overall accuracy
- `auc_score`: AUC-ROC score
- `sensitivity`: Recall for AD class
- `specificity`: Recall for CN class
- `trained_on`: Training date
- `is_active`: Whether model is deployed

## Admin Interface

Access the Django admin at `http://127.0.0.1:8000/admin/`

### Detection Results
- View all user detections
- Filter by status, class, date
- Review clinical notes
- Add clinician notes
- Track reviewers

### Model Metadata
- View deployed models
- Check performance metrics
- Manage active versions

## Troubleshooting

### "Model file not found" error
1. Check if `backend/models/alzheimers_detector.pth` exists
2. Ensure the file path in `detection/views.py` matches your location
3. Verify file permissions

### Authentication errors
1. Ensure user is logged in
2. Check access token is valid
3. Verify CORS settings in `settings.py`

### Image processing errors
1. Ensure image is RGB (not grayscale)
2. Check image size (224×224 or larger is fine)
3. Verify image format (JPG, PNG supported)

### Model inference fails
1. Check GPU availability
2. Verify PyTorch installation
3. Ensure model weights are compatible

## Production Deployment

### Security Considerations
1. Set `DEBUG = False` in settings.py
2. Update `ALLOWED_HOSTS` with your domain
3. Use environment variables for sensitive data
4. Enable HTTPS only
5. Set proper CORS origins

### Performance Optimization
1. Add caching for model inference
2. Use async task queues (Celery) for long uploads
3. Implement rate limiting
4. Add model quantization for faster inference

### Scalability
1. Use Docker containerization
2. Deploy to cloud platforms (AWS, Azure, Google Cloud)
3. Set up load balancing
4. Use object storage (S3, Azure Blob) for uploaded files
5. Implement proper logging and monitoring

## Next Steps

1. **Add more models**: Implement endpoints for other diseases
2. **Explainability**: Add Grad-CAM visualizations
3. **Multi-view analysis**: Support 3D volumes
4. **Clinical integration**: Connect to EHR systems
5. **Analytics**: Add user engagement metrics
6. **ML Ops**: Implement model versioning and A/B testing

## Support

For issues or questions:
1. Check logs: `backend/logs/` and browser console
2. Review API documentation
3. Test endpoints with Postman or curl
4. Check Django admin for data consistency
