# 💾 Key Code Snippets - Model Integration

**Reference Guide for Understanding the Implementation**

---

## 1. ModelLoader (Singleton Pattern)

**File:** `backend/detection/views.py`

```python
import torch
from torchvision.models import resnet34
from django.conf import settings

class ModelLoader:
    """Singleton pattern for loading and caching the trained model"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self._model = None
        self._load_model()
        self._initialized = True
    
    def _load_model(self):
        """Load trained model from file"""
        model_path = os.path.join(settings.BASE_DIR, 'models', 'alzheimers_detector.pth')
        
        # Create model architecture
        self._model = resnet34(pretrained=False)
        self._model.fc = torch.nn.Linear(512, 1)  # Binary classification
        
        # Load weights if file exists
        if os.path.exists(model_path):
            checkpoint = torch.load(model_path, map_location=self.device)
            self._model.load_state_dict(checkpoint['model_state_dict'])
        
        self._model.to(self.device)
        self._model.eval()
    
    def predict(self, image_tensor):
        """Run inference on image tensor"""
        with torch.no_grad():
            raw_output = self._model(image_tensor)
            probability = torch.sigmoid(raw_output)
        return probability.item()

# Usage
loader = ModelLoader()
prob = loader.predict(preprocessed_image)
```

---

## 2. Image Preprocessing Pipeline

**File:** `backend/detection/views.py`

```python
from PIL import Image
import torch
from torchvision import transforms

def preprocess_image(image_file):
    """Preprocess MRI image for model input"""
    
    # Load image with PIL
    image = Image.open(image_file).convert('RGB')
    
    # Define transforms
    transform = transforms.Compose([
        transforms.Resize((224, 224), interpolation=Image.BILINEAR),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],  # ImageNet normalization
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    # Apply transforms
    image_tensor = transform(image)
    
    # Add batch dimension
    image_tensor = image_tensor.unsqueeze(0)
    
    return image_tensor

# Usage
image_tensor = preprocess_image(request.FILES['uploaded_file'])
```

---

## 3. Detection API Endpoint

**File:** `backend/detection/views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import time

class DetectionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def upload_and_detect(self, request):
        """Upload MRI image and get AI prediction"""
        
        try:
            # Get uploaded file
            uploaded_file = request.FILES.get('uploaded_file')
            if not uploaded_file:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate file
            if not uploaded_file.content_type.startswith('image/'):
                return Response(
                    {'error': 'File must be an image'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Preprocess image
            image_tensor = preprocess_image(uploaded_file)
            
            # Get model and run inference
            start_time = time.time()
            loader = ModelLoader()
            confidence_score = loader.predict(image_tensor)
            processing_time = time.time() - start_time
            
            # Classify
            threshold = 0.5
            predicted_class = "Alzheimer's Disease (AD)" if confidence_score > threshold else "Control (CN)"
            
            # Save to database
            detection_result = DetectionResult.objects.create(
                user=request.user,
                uploaded_file=uploaded_file,
                status='completed',
                predicted_class=predicted_class,
                confidence_score=confidence_score,
                prediction_probability={
                    "Alzheimer's Disease (AD)": float(confidence_score),
                    "Control (CN)": float(1 - confidence_score)
                },
                patient_age=request.data.get('patient_age'),
                patient_gender=request.data.get('patient_gender'),
                notes=request.data.get('notes'),
                processing_time=processing_time,
                analysis_details={
                    'raw_output': float(raw_output),
                    'sigmoid_probability': float(confidence_score),
                    'threshold_used': threshold,
                    'model_version': 'ResNet-34-v1.0'
                }
            )
            
            # Serialize and return
            serializer = DetectionResultSerializer(detection_result)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

---

## 4. Database Models

**File:** `backend/detection/models.py`

```python
from django.db import models
from django.contrib.auth.models import User

class DetectionResult(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_file = models.ImageField(upload_to='detections/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    predicted_class = models.CharField(max_length=50)  # 'AD' or 'CN'
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4)
    prediction_probability = models.JSONField()  # {AD: 0.97, CN: 0.03}
    patient_age = models.IntegerField(null=True, blank=True)
    patient_gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')], null=True)
    notes = models.TextField(null=True, blank=True)
    processing_time = models.DecimalField(max_digits=10, decimal_places=3)
    analysis_details = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.predicted_class} ({self.confidence_score})"
    
    class Meta:
        ordering = ['-created_at']

class ModelMetadata(models.Model):
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    architecture = models.CharField(max_length=255)
    accuracy = models.DecimalField(max_digits=5, decimal_places=4)
    auc_score = models.DecimalField(max_digits=5, decimal_places=4)
    sensitivity = models.DecimalField(max_digits=5, decimal_places=4)
    specificity = models.DecimalField(max_digits=5, decimal_places=4)
    trained_on = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} v{self.version}"
```

---

## 5. API Serializers

**File:** `backend/detection/serializers.py`

```python
from rest_framework import serializers
from .models import DetectionResult, ModelMetadata

class DetectionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectionResult
        fields = [
            'id', 'status', 'predicted_class', 'confidence_score',
            'prediction_probability', 'processing_time', 'analysis_details',
            'patient_age', 'patient_gender', 'notes', 'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'predicted_class', 'confidence_score',
            'prediction_probability', 'processing_time', 'analysis_details',
            'created_at'
        ]

class DetectionUploadSerializer(serializers.Serializer):
    uploaded_file = serializers.ImageField(required=True)
    patient_age = serializers.IntegerField(required=False, allow_null=True)
    patient_gender = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_uploaded_file(self, value):
        # Validate file size (10MB max)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File too large (max 10MB)")
        return value

class ModelMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelMetadata
        fields = ['id', 'name', 'version', 'architecture', 'accuracy', 
                  'auc_score', 'sensitivity', 'specificity', 'trained_on']
```

---

## 6. Frontend API Integration

**File:** `frontend/app/detection/page.tsx`

```typescript
async function analyzeImage(formData: FormData): Promise<DetectionResult> {
  // Get JWT token from localStorage
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  // Send to backend
  const response = await fetch('http://127.0.0.1:8000/api/detections/upload_and_detect/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      // Note: Don't set Content-Type, let browser set it for FormData
    },
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Detection failed');
  }
  
  const result = await response.json();
  return result;
}

// Usage in React component
const handleUpload = async (file: File) => {
  const formData = new FormData();
  formData.append('uploaded_file', file);
  formData.append('patient_age', age);
  formData.append('patient_gender', gender);
  formData.append('notes', notes);
  
  try {
    const result = await analyzeImage(formData);
    setDetectionResult(result);
    // Display: "97.07% Confident: Alzheimer's Disease (AD)"
  } catch (error) {
    setError(error.message);
  }
};
```

---

## 7. URL Configuration

**File:** `backend/detection/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DetectionViewSet

router = DefaultRouter()
router.register(r'detections', DetectionViewSet, basename='detection')

urlpatterns = [
    path('', include(router.urls)),
]
```

**Core URL config:**

**File:** `backend/core/urls.py`

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('detection.urls')),  # ← Added
    # ... other paths
]
```

---

## 8. Settings Configuration

**File:** `backend/core/settings.py`

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'corsheaders',
    'rest_framework',
    'detection',  # ← Added
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ... other middleware
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}
```

---

## 9. Model Performance Tracking

**File:** `backend/detection/admin.py`

```python
from django.contrib import admin
from .models import DetectionResult, ModelMetadata

@admin.register(DetectionResult)
class DetectionResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'predicted_class', 'confidence_score', 'created_at']
    list_filter = ['predicted_class', 'status', 'created_at']
    search_fields = ['user__username', 'notes']
    readonly_fields = ['created_at', 'processing_time', 'analysis_details']
    
    fieldsets = (
        ('Result', {
            'fields': ('user', 'status', 'predicted_class', 'confidence_score')
        }),
        ('Patient Info', {
            'fields': ('patient_age', 'patient_gender', 'notes'),
            'classes': ('collapse',)
        }),
        ('Analysis', {
            'fields': ('processing_time', 'analysis_details', 'prediction_probability')
        }),
        ('File', {
            'fields': ('uploaded_file',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(ModelMetadata)
class ModelMetadataAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'is_active', 'auc_score']
    list_filter = ['is_active', 'trained_on']
```

---

## 10. Error Handling Example

**File:** `backend/detection/views.py`

```python
def upload_and_detect(self, request):
    """Handle errors gracefully"""
    
    try:
        # Validate file
        if 'uploaded_file' not in request.FILES:
            return Response(
                {'error': 'No file uploaded'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['uploaded_file']
        
        # Check file size
        if file.size > 10 * 1024 * 1024:  # 10MB
            return Response(
                {'error': 'File too large (max 10MB)'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )
        
        # Check file type
        valid_types = ['image/jpeg', 'image/png']
        if file.content_type not in valid_types:
            return Response(
                {'error': 'Invalid file type. Use JPG or PNG'},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            )
        
        # Process image
        try:
            image_tensor = preprocess_image(file)
        except Exception as e:
            return Response(
                {'error': f'Image processing failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Run inference
        try:
            loader = ModelLoader()
            confidence = loader.predict(image_tensor)
        except Exception as e:
            return Response(
                {'error': f'Model inference failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Success response
        return Response(result_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Unexpected error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

---

## 🔑 Key Concepts Implemented

### 1. Singleton Pattern
The `ModelLoader` class uses singleton pattern to ensure:
- Model loaded only once (memory efficient)
- Single instance shared across all requests
- No repeated I/O operations

### 2. Image Preprocessing
Standardized pipeline ensures:
- Consistent input to model
- ImageNet normalization
- 224×224 input size
- Proper tensor format

### 3. JWT Authentication
Ensures:
- Only authenticated users can upload
- User linked to their detection results
- Secure API access
- Token stored in frontend localStorage

### 4. Database Design
Normalizes data:
- DetectionResult stores individual predictions
- ModelMetadata tracks model versions
- Foreign key links user to their detections
- JSON fields for flexible data (probabilities, analysis details)

### 5. Error Handling
Covers:
- Missing files
- Invalid file types
- File size limits
- Image processing errors
- Model inference failures
- Database errors

---

## 📊 Performance Considerations

```python
# Model loading (singleton - happens once)
Time: ~2-3 seconds
Memory: ~200-300 MB

# Image preprocessing
Time: ~0.2-0.5 seconds
Memory: ~100-150 MB per image

# Model inference
Time: ~0.5-2 seconds (CPU) or ~0.1-0.3 seconds (GPU)
Memory: ~50-100 MB during inference

# Total per request
Time: ~1-3 seconds (CPU) or ~0.5-1 second (GPU)
Memory: Peak ~400-500 MB
```

---

## 🚀 Deployment Optimization

**For Production:**

```python
# Use GPU if available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Quantize model for faster inference
model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)

# Use async tasks for long operations
from celery import shared_task

@shared_task
def analyze_image_async(file_id):
    # Offload to background worker
    pass

# Cache results
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def get_stats(request):
    pass
```

---

**These snippets represent the core logic of the integration. Refer to the actual files for complete implementation.**
