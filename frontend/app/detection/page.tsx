'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Navigation from '@/components/Navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Upload, Brain, AlertCircle, CheckCircle2, FileText, Loader2, Download } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'

type ModelType = 'alzheimers' | null

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000'

export default function DetectionPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedModel, setSelectedModel] = useState<ModelType>('alzheimers')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [hasResults, setHasResults] = useState(false)
  const [detectionResult, setDetectionResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [patientAge, setPatientAge] = useState<string>('')
  const [patientGender, setPatientGender] = useState<string>('')
  const [notes, setNotes] = useState<string>('')

  // Auth check - redirect if not logged in
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/signup')
    }
  }, [user, authLoading, router])

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-teal-50">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
      </div>
    )
  }

  // Don't render if not authenticated
  if (!user) {
    return null
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Accept images (.jpg, .png) and NIfTI files (.nii, .nii.gz)
      const validImageTypes = ['image/jpeg', 'image/png']
      const validNiftiExtensions = ['.nii', '.nii.gz']
      const fileName = file.name.toLowerCase()
      
      const isImage = validImageTypes.includes(file.type)
      const isNifti = validNiftiExtensions.some(ext => fileName.endsWith(ext))
      
      if (!isImage && !isNifti) {
        setError('Please upload an image file (JPG, PNG) or NIfTI file (.nii, .nii.gz)')
        return
      }
      setSelectedFile(file)
      setError(null)
    }
  }

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select an image file first!')
      return
    }

    setIsAnalyzing(true)
    setError(null)

    try {
      const token = localStorage.getItem('authToken')
      if (!token) {
        setError('Authentication required. Please log in.')
        setIsAnalyzing(false)
        return
      }

      const formData = new FormData()
      formData.append('uploaded_file', selectedFile)
      if (patientAge) formData.append('patient_age', patientAge)
      if (patientGender) formData.append('patient_gender', patientGender)
      if (notes) formData.append('notes', notes)

      const response = await fetch(
        `${API_BASE_URL}/api/detections/upload_and_detect/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Detection failed')
      }

      const result = await response.json()
      
      setDetectionResult({
        modelType: 'Alzheimer\'s Detection Model (ResNet-34)',
        // Keep both the stored key and a human-readable label for UI usage
        predicted_class: result.predicted_class,
        classification: result.predicted_class_display || (result.predicted_class === 'alzheimers' ? "Alzheimer's Disease (AD)" : 'Control (CN)'),
        confidence: (result.confidence_score * 100).toFixed(1),
        processingTime: result.processing_time?.toFixed(2),
        probabilities: result.prediction_probability,
        analysis: result.analysis_details,
        timestamp: new Date(result.created_at).toLocaleString(),
        detectionId: result.id,
        modelVersion: result.model_version,
      })

      setHasResults(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during detection')
      console.error('Detection error:', err)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleDownloadReport = () => {
    if (!detectionResult) return

    const reportContent = `
ALZHEIMER'S DISEASE DETECTION REPORT
=====================================

Report Generated: ${detectionResult.timestamp}
Detection ID: ${detectionResult.detectionId}

CLASSIFICATION RESULTS
----------------------
Predicted Class: ${detectionResult.classification}
Confidence Score: ${detectionResult.confidence}%

CLASS PROBABILITIES
-------------------
${Object.entries(detectionResult.probabilities || {})
  .map(([cls, prob]: [string, any]) => `${cls}: ${(prob * 100).toFixed(2)}%`)
  .join('\n')}

ANALYSIS DETAILS
----------------
Model: ${detectionResult.modelType}
Model Version: ${detectionResult.modelVersion}
Processing Time: ${detectionResult.processingTime}s

${detectionResult.analysis ? `Raw Output: ${detectionResult.analysis.raw_output}
Sigmoid Probability: ${detectionResult.analysis.sigmoid_probability}
Threshold: ${detectionResult.analysis.threshold_used}` : ''}

PATIENT INFORMATION
-------------------
Age: ${patientAge || 'Not provided'}
Gender: ${patientGender || 'Not provided'}
Notes: ${notes || 'None'}

CLINICAL RECOMMENDATIONS
------------------------
${detectionResult.classification === 'Alzheimer\'s Disease (AD)' ? 
  `• Immediate consultation with a neurologist is recommended
• Consider additional diagnostic tests (PET scan, CSF analysis)
• Monitor cognitive function regularly
• Discuss treatment options with healthcare provider` :
  `• Results suggest normal cognitive function
• Continue regular health check-ups
• Maintain cognitive activities for brain health`}

Generated by DementiaNext AI Detection System
    `.trim()

    const element = document.createElement('a')
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(reportContent))
    element.setAttribute('download', `alzheimers_report_${detectionResult.detectionId}.txt`)
    element.style.display = 'none'
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  const resetForm = () => {
    setSelectedFile(null)
    setSelectedModel('alzheimers')
    setHasResults(false)
    setDetectionResult(null)
    setError(null)
    setPatientAge('')
    setPatientGender('')
    setNotes('')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-teal-50">
      <Navigation />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 rounded-full bg-gradient-to-r from-blue-500 to-teal-500 flex items-center justify-center">
              <Brain className="text-white" size={40} />
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
            <span className="bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent">
              Alzheimer's Detection
            </span>
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Upload an MRI image for AI-powered Alzheimer's disease detection
          </p>
        </motion.div>

        {/* Error Alert */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3"
          >
            <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900">Error</h3>
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          </motion.div>
        )}

        {!hasResults ? (
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Upload Section */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="lg:col-span-2"
            >
              <Card className="border-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Upload size={24} />
                    Upload MRI Image
                  </CardTitle>
                  <CardDescription>
                    Upload brain MRI slice for analysis
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-400 transition-colors">
                    <label className="cursor-pointer block">
                      <Upload className="mx-auto mb-4 text-gray-400" size={48} />
                      <p className="text-lg font-medium text-gray-700 mb-2">
                        Click to browse or drop file
                      </p>
                      <p className="text-sm text-gray-500 mb-4">
                        Supported: JPG, PNG, NIfTI (.nii, .nii.gz)
                      </p>
                      <Input
                        type="file"
                        onChange={handleFileSelect}
                        accept="image/*,.nii,.nii.gz"
                        className="hidden"
                      />
                    </label>
                  </div>

                  {selectedFile && (
                    <div className="p-4 bg-blue-50 rounded-lg flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{selectedFile.name}</p>
                        <p className="text-sm text-gray-600">
                          {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                      <CheckCircle2 className="text-green-600" size={24} />
                    </div>
                  )}

                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Age (optional)
                      </label>
                      <Input 
                        type="number" 
                        placeholder="Patient age" 
                        value={patientAge}
                        onChange={(e) => setPatientAge(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Gender (optional)
                      </label>
                      <select
                        value={patientGender}
                        onChange={(e) => setPatientGender(e.target.value)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2"
                      >
                        <option value="">Select...</option>
                        <option value="M">Male</option>
                        <option value="F">Female</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Clinical Notes (optional)
                    </label>
                    <textarea
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                      rows={3}
                      placeholder="Enter any relevant clinical observations..."
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                    />
                  </div>

                  <Button
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || !selectedFile}
                    className="w-full py-6 text-lg bg-blue-600 hover:bg-blue-700"
                    size="lg"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="mr-2 animate-spin" size={20} />
                        Analyzing with AI...
                      </>
                    ) : (
                      <>
                        <Brain className="mr-2" size={20} />
                        Analyze MRI Image
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>

            {/* Info Section */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="space-y-6"
            >
              <Card className="border-2 border-blue-200 bg-blue-50">
                <CardHeader>
                  <CardTitle className="text-lg">Model Info</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>
                    <p className="font-semibold text-gray-900">ResNet-34</p>
                    <p className="text-gray-700">AUC: 0.9707</p>
                    <p className="text-gray-700">Accuracy: 91.84%</p>
                    <p className="text-gray-700">Sensitivity: 88.46%</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-2 border-green-200 bg-green-50">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText size={20} />
                    Output
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-gray-700">
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-600" />
                      Classification (AD vs CN)
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-600" />
                      Confidence scores
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-600" />
                      Downloadable report
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        ) : (
          /* Results Section */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            <Card className="border-2 border-green-200 bg-green-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-green-900">
                  <CheckCircle2 size={28} />
                  Analysis Complete
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-8">
                  <div>
                    <p className="text-sm text-gray-600 mb-2">Classification</p>
                    <p className="text-3xl font-bold text-gray-900 mb-4">
                      {detectionResult.classification}
                    </p>
                    <p className="text-sm text-gray-600 mb-2">Confidence</p>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-600"
                          style={{ width: `${detectionResult.confidence}%` }}
                        />
                      </div>
                      <span className="text-2xl font-bold text-green-600">
                        {detectionResult.confidence}%
                      </span>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Processing Time</p>
                      <p className="text-xl font-semibold text-gray-900">
                        {detectionResult.processingTime}s
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Detection ID</p>
                      <p className="text-lg font-mono text-gray-900">
                        {detectionResult.detectionId}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Timestamp</p>
                      <p className="text-sm text-gray-900">
                        {detectionResult.timestamp}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {detectionResult.probabilities && (
              <Card className="border-2">
                <CardHeader>
                  <CardTitle>Classification Probabilities</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {Object.entries(detectionResult.probabilities).map(
                    ([cls, prob]: [string, any]) => (
                      <div key={cls}>
                        <div className="flex justify-between items-center mb-2">
                          <p className="font-medium text-gray-900">{cls}</p>
                          <Badge variant="secondary">
                            {(prob * 100).toFixed(2)}%
                          </Badge>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-600"
                            style={{ width: `${prob * 100}%` }}
                          />
                        </div>
                      </div>
                    )
                  )}
                </CardContent>
              </Card>
            )}

            <div className="flex gap-4">
              <Button
                onClick={handleDownloadReport}
                className="flex-1 bg-blue-600 hover:bg-blue-700 py-6 text-lg"
                size="lg"
              >
                <Download className="mr-2" size={20} />
                Download Report
              </Button>
              <Button
                onClick={resetForm}
                variant="outline"
                className="flex-1 py-6 text-lg"
                size="lg"
              >
                Analyze Another
              </Button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
