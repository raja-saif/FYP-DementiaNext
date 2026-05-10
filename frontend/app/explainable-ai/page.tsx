'use client'

import React, { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import Navigation from '@/components/Navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Eye, Brain, Activity, AlertCircle, Loader2, ImageIcon, Layers, ArrowLeft, RefreshCw, TrendingUp, Info, Play, Pause, SkipBack, SkipForward, ScanLine } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { PUBLIC_API_BASE_URL } from '@/lib/publicApi'

interface GradCAMData {
  detection_id: string
  predicted_class: string
  confidence: number
  gradcam: {
    overlay_base64: string
    heatmap_base64: string
    original_base64: string
    target_layer: string
    gradcam_class: number
    gradcam_class_name: string
    gradcam_confidence: number
    selected_slice?: number
    slice_selection_method?: string
  }
  analysis: Record<string, unknown>
  model_type: string
}

interface SliceData {
  index: number
  original_base64: string
  overlay_base64: string
  heatmap_base64: string
  confidence: number
  predicted_class_name: string
}

interface SlicesResponse {
  detection_id: string
  predicted_class: string
  confidence: number
  model_type: string
  total_slices: number
  best_slice_index: number
  slices: SliceData[]
}

function ExplainableAIContent() {
  const { user, token, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const detectionId = searchParams.get('detection_id')
  
  const [gradcamData, setGradcamData] = useState<GradCAMData | null>(null)
  const [gradcamLoading, setGradcamLoading] = useState(false)
  const [gradcamError, setGradcamError] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<'original' | 'overlay' | 'heatmap' | 'comparison' | 'sliceExplorer'>('comparison')
  const [slicesData, setSlicesData] = useState<SlicesResponse | null>(null)
  const [slicesLoading, setSlicesLoading] = useState(false)
  const [slicesError, setSlicesError] = useState<string | null>(null)
  const [currentSlicePos, setCurrentSlicePos] = useState(0)
  const [sliceViewMode, setSliceViewMode] = useState<'overlay' | 'original' | 'heatmap'>('overlay')
  const [isPlaying, setIsPlaying] = useState(false)
  const playRef = React.useRef<ReturnType<typeof setInterval> | null>(null)

  // Auth check - redirect if not logged in
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  // Fetch Grad-CAM data if detection_id is provided
  useEffect(() => {
    if (detectionId && token && !authLoading) {
      console.log('Triggering XAI fetch - detectionId:', detectionId, 'token exists:', !!token)
      fetchGradCAMData(detectionId)
    } else {
      console.log('XAI fetch not triggered - detectionId:', detectionId, 'token exists:', !!token, 'authLoading:', authLoading)
    }
  }, [detectionId, token, authLoading])

  useEffect(() => {
    if (isPlaying && slicesData && slicesData.slices.length > 0) {
      playRef.current = setInterval(() => {
        setCurrentSlicePos((prev) => {
          if (prev >= slicesData.slices.length - 1) {
            setIsPlaying(false)
            return prev
          }
          return prev + 1
        })
      }, 200)
    }
    return () => {
      if (playRef.current) clearInterval(playRef.current)
    }
  }, [isPlaying, slicesData])

  const fetchSlicesData = async (id: string) => {
    setSlicesLoading(true)
    setSlicesError(null)
    try {
      const response = await fetch(
        `${PUBLIC_API_BASE_URL}/api/detection/detections/${id}/explainability_slices/?num_slices=30`,
        { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } },
      )
      if (!response.ok) {
        const errorText = await response.text()
        try {
          const error = JSON.parse(errorText)
          throw new Error(error.error || `HTTP ${response.status}`)
        } catch {
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }
      }
      const data: SlicesResponse = await response.json()
      setSlicesData(data)
      const bestPos = data.slices.findIndex(s => s.index === data.best_slice_index)
      setCurrentSlicePos(bestPos >= 0 ? bestPos : Math.floor(data.slices.length / 2))
    } catch (err) {
      setSlicesError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSlicesLoading(false)
    }
  }

  const fetchGradCAMData = async (id: string) => {
    setGradcamLoading(true)
    setGradcamError(null)
    try {
      const url = `${PUBLIC_API_BASE_URL}/api/detection/detections/${id}/explainability/`
      console.log('Fetching XAI data from:', url)
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      
      console.log('Response status:', response.status)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('API Error:', errorText)
        try {
          const error = JSON.parse(errorText)
          throw new Error(error.error || error.detail || `HTTP ${response.status}: Failed to fetch explainability data`)
        } catch {
          throw new Error(`HTTP ${response.status}: ${errorText || 'Failed to fetch explainability data'}`)
        }
      }
      
      const data = await response.json()
      console.log('XAI data received:', data)
      setGradcamData(data)
    } catch (err) {
      console.error('XAI fetch error:', err)
      setGradcamError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setGradcamLoading(false)
    }
  }

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
      </div>
    )
  }

  // Don't render if not authenticated
  if (!user) {
    return null
  }

  const getClassDisplayName = (cls: string) => {
    const mapping: Record<string, string> = {
      'alzheimers': "Alzheimer's Disease",
      'ad': "Alzheimer's Disease",
      'pd': "Parkinson's Disease",
      'ftd': "Frontotemporal Dementia",
      'cn': "Normal/Control",
      'Normal': "Normal/Control",
      'Dementia': "Dementia Detected",
    }
    return mapping[cls] || cls
  }

  return (
    <div className="min-h-screen bg-white">
      <Navigation />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        {/* Back Navigation + Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8 relative"
        >
          {detectionId && (
            <button
              type="button"
              aria-label="Go back to detection results"
              onClick={() => router.push(`/detection?detection_id=${detectionId}`)}
              className="mb-5 flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-700 shadow-sm ring-1 ring-black/[0.04] transition-all hover:border-blue-300 hover:bg-gradient-to-br hover:from-blue-50 hover:to-indigo-50 hover:text-blue-700 hover:shadow-md hover:ring-blue-200/40 active:scale-95"
            >
              <ArrowLeft className="h-5 w-5" strokeWidth={2.25} aria-hidden />
            </button>
          )}
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-gray-900">
            Explainable AI Insights
          </h1>
          <p className="text-base sm:text-lg text-gray-600 mt-2 max-w-3xl leading-relaxed">
            Grad-CAM visualization of MRI regions influencing the AI diagnosis
          </p>
          {gradcamData && (
            <div className="mt-4 flex items-center gap-3 flex-wrap">
              <span className="text-xs font-mono text-gray-400 bg-gray-100 px-2.5 py-1 rounded">
                {gradcamData.detection_id}
              </span>
              <Badge className="bg-blue-50 text-blue-700 border border-blue-200 text-xs">
                {getClassDisplayName(gradcamData.predicted_class)}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {(gradcamData.confidence * 100).toFixed(1)}% Confidence
              </Badge>
              <Badge variant="outline" className="text-xs">
                {gradcamData.model_type === 'binary' ? 'Binary' : 'Subtype'}
              </Badge>
            </div>
          )}
        </motion.div>

        {/* Prompt to run detection when no detection_id */}
        {!detectionId && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-12"
          >
            <Card className="border-2 border-dashed border-blue-300 bg-gradient-to-br from-blue-50 to-cyan-50">
              <CardContent className="p-8 text-center">
                <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                  <Brain className="text-white" size={40} />
                </div>
                <h3 className="text-2xl font-bold text-gray-800 mb-3">No Detection Selected</h3>
                <p className="text-gray-600 mb-6 max-w-lg mx-auto">
                  To view the AI explainability analysis with MRI heatmaps and highlighted brain regions, 
                  you need to first run a detection on an MRI scan.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  <Button 
                    onClick={() => router.push('/detection')}
                    className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700"
                    size="lg"
                  >
                    <Brain className="mr-2" size={20} />
                    Run New Detection
                  </Button>
                  <Button 
                    onClick={() => router.push('/patient-dashboard')}
                    variant="outline"
                    size="lg"
                  >
                    <Activity className="mr-2" size={20} />
                    View Detection History
                  </Button>
                </div>
                <p className="text-sm text-gray-500 mt-6">
                  After completing a detection, click "View Explainability Analysis" to see the Grad-CAM visualization.
                </p>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Grad-CAM Visualization Section - Only show when real data available */}
        {(gradcamLoading || gradcamData || gradcamError) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-12"
          >
            <Card className="border border-gray-200 shadow-sm rounded-xl overflow-hidden">
              <CardHeader className="border-b border-gray-100 bg-white">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-3 text-gray-900 text-xl sm:text-2xl font-semibold">
                      <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
                        <Layers size={18} className="text-blue-600" />
                      </div>
                      Neural Attention Mapping
                    </CardTitle>
                    <CardDescription className="text-gray-600 mt-1.5 text-base">
                      Brain regions that influenced the AI diagnosis
                    </CardDescription>
                  </div>
                  {gradcamData && (
                    <div className="hidden md:flex">
                      <span className="text-emerald-600 text-xs font-semibold bg-emerald-50 border border-emerald-100 px-3 py-1.5 rounded-full">Live Analysis</span>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {gradcamLoading && (
                  <div className="flex flex-col items-center justify-center py-20">
                    <div className="relative">
                      <div className="w-16 h-16 rounded-full border-4 border-gray-200 border-t-blue-500 animate-spin" />
                      <Brain className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-blue-500" size={24} />
                    </div>
                    <p className="text-gray-700 mt-6 font-medium">Generating attention maps...</p>
                    <p className="text-gray-400 text-sm mt-1">Analyzing MRI with Grad-CAM</p>
                  </div>
                )}
                
                {gradcamError && (
                  <div className="m-6 bg-red-50 border border-red-200 rounded-lg p-5">
                    <div className="flex items-center gap-3">
                      <AlertCircle className="text-red-500" size={20} />
                      <div>
                        <p className="font-semibold text-red-700 text-sm">Visualization Error</p>
                        <p className="text-red-600 text-sm mt-0.5">{gradcamError}</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {gradcamData && (
                  <div>
                    {/* View Mode Selector */}
                    <div className="flex flex-wrap justify-center gap-2 p-4 bg-gray-50 border-b border-gray-100">
                      <Button
                        variant={activeView === 'comparison' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setActiveView('comparison')}
                        className={activeView === 'comparison' 
                          ? 'bg-blue-600 text-white border-0 shadow-sm' 
                          : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}
                      >
                        <Layers className="mr-1.5 h-3.5 w-3.5" />
                        Side-by-Side
                      </Button>
                      <Button
                        variant={activeView === 'original' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setActiveView('original')}
                        className={activeView === 'original' 
                          ? 'bg-gray-700 text-white border-0 shadow-sm' 
                          : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}
                      >
                        <Brain className="mr-1.5 h-3.5 w-3.5" />
                        Preprocessed MRI
                      </Button>
                      <Button
                        variant={activeView === 'overlay' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setActiveView('overlay')}
                        className={activeView === 'overlay' 
                          ? 'bg-emerald-600 text-white border-0 shadow-sm' 
                          : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}
                      >
                        <ImageIcon className="mr-1.5 h-3.5 w-3.5" />
                        MRI + Heatmap
                      </Button>
                      <Button
                        variant={activeView === 'heatmap' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setActiveView('heatmap')}
                        className={activeView === 'heatmap' 
                          ? 'bg-orange-600 text-white border-0 shadow-sm' 
                          : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}
                      >
                        <Activity className="mr-1.5 h-3.5 w-3.5" />
                        Heatmap Only
                      </Button>
                      <Button
                        variant={activeView === 'sliceExplorer' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => {
                          setActiveView('sliceExplorer')
                          if (!slicesData && !slicesLoading && detectionId) {
                            fetchSlicesData(detectionId)
                          }
                        }}
                        className={activeView === 'sliceExplorer'
                          ? 'bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white border-0 shadow-lg shadow-violet-500/25'
                          : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}
                      >
                        <ScanLine className="mr-1.5 h-3.5 w-3.5" />
                        3D Slice Explorer
                      </Button>
                    </div>
                    
                    {/* Comparison View - Three Images Side by Side */}
                    {activeView === 'comparison' && (
                      <div>
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
                          <div className="p-5 border-r border-gray-100">
                            <div className="flex items-center justify-between mb-3">
                              <h3 className="text-gray-800 font-semibold text-sm">Preprocessed MRI Scan</h3>
                              <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Input</span>
                            </div>
                            <div className="rounded-lg overflow-hidden border border-gray-200 bg-black">
                              <img
                                src={`data:image/png;base64,${gradcamData.gradcam.original_base64}`}
                                alt="Preprocessed MRI"
                                className="w-full h-auto aspect-square object-contain"
                              />
                            </div>
                            <p className="text-gray-400 text-xs text-center mt-2">Preprocessed brain scan</p>
                          </div>
                          
                          <div className="p-5 border-r border-gray-100">
                            <div className="flex items-center justify-between mb-3">
                              <h3 className="text-gray-800 font-semibold text-sm flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-orange-500" />
                                AI Attention Map
                              </h3>
                              <span className="text-[10px] font-medium text-orange-600 uppercase tracking-wider">Focus</span>
                            </div>
                            <div className="rounded-lg overflow-hidden border border-orange-200 bg-black">
                              <img
                                src={`data:image/png;base64,${gradcamData.gradcam.heatmap_base64}`}
                                alt="Attention Heatmap"
                                className="w-full h-auto aspect-square object-contain"
                              />
                            </div>
                            <p className="text-orange-500 text-xs text-center mt-2">Neural network attention weights</p>
                          </div>
                          
                          <div className="p-5">
                            <div className="flex items-center justify-between mb-3">
                              <h3 className="text-gray-800 font-semibold text-sm flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                                Highlighted Regions
                              </h3>
                              <span className="text-[10px] font-medium text-emerald-600 uppercase tracking-wider">Result</span>
                            </div>
                            <div className="rounded-lg overflow-hidden border border-emerald-200 bg-black">
                              <img
                                src={`data:image/png;base64,${gradcamData.gradcam.overlay_base64}`}
                                alt="MRI with Highlighted Regions"
                                className="w-full h-auto aspect-square object-contain"
                              />
                            </div>
                            <p className="text-emerald-500 text-xs text-center mt-2">Critical areas highlighted</p>
                          </div>
                        </div>
                        
                        <div className="hidden lg:flex items-center justify-center py-3 bg-gray-50 border-t border-gray-100">
                          <div className="flex items-center gap-4 text-gray-400 text-xs">
                            <span>Original Scan</span>
                            <div className="flex items-center">
                              <div className="w-8 h-0.5 bg-gradient-to-r from-gray-300 to-orange-400" />
                              <div className="w-1.5 h-1.5 rounded-full bg-orange-400" />
                            </div>
                            <span className="text-orange-500">AI Analysis</span>
                            <div className="flex items-center">
                              <div className="w-8 h-0.5 bg-gradient-to-r from-orange-400 to-emerald-500" />
                              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            </div>
                            <span className="text-emerald-600">Key Regions</span>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Single Image Views */}
                    {activeView !== 'comparison' && activeView !== 'sliceExplorer' && (
                      <div className="grid lg:grid-cols-2 gap-0">
                        <div className="p-6 flex flex-col bg-white">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-gray-800 font-semibold text-sm flex items-center gap-2">
                              <div className={`w-2 h-2 rounded-full ${
                                activeView === 'original' ? 'bg-gray-400' :
                                activeView === 'overlay' ? 'bg-emerald-500' : 'bg-orange-500'
                              }`} />
                              {activeView === 'original' ? 'Preprocessed MRI Scan' :
                               activeView === 'overlay' ? 'MRI with Attention Overlay' : 
                               'Attention Heatmap'}
                            </h3>
                            <span className="text-xs text-gray-400">
                              {gradcamData.model_type === 'binary' ? 'Binary' : 'Subtype'}
                            </span>
                          </div>
                          
                          <div className={`flex-1 rounded-lg overflow-hidden bg-black border ${
                            activeView === 'original' ? 'border-gray-200' :
                            activeView === 'overlay' ? 'border-emerald-200' : 'border-orange-200'
                          }`}>
                            <img
                              src={`data:image/png;base64,${
                                activeView === 'original' ? gradcamData.gradcam.original_base64 :
                                activeView === 'overlay' ? gradcamData.gradcam.overlay_base64 : 
                                gradcamData.gradcam.heatmap_base64
                              }`}
                              alt={`${activeView} view`}
                              className="w-full h-auto max-h-[500px] object-contain mx-auto"
                            />
                          </div>
                          
                          <p className="text-center text-gray-400 text-xs mt-3">
                            {activeView === 'original' 
                              ? 'Preprocessed brain MRI scan used for AI analysis'
                              : activeView === 'overlay' 
                              ? 'Red/orange regions = diagnostically significant areas'
                              : 'Pure attention weights showing neural network focus intensity'}
                          </p>
                        </div>
                        
                        <div className="p-6 border-l border-gray-100 bg-gray-50/50 space-y-5">
                          <div>
                            <h3 className="text-gray-800 font-semibold text-sm mb-3 flex items-center gap-2">
                              <Activity className="text-blue-600" size={16} />
                              Prediction Results
                            </h3>
                            
                            <div className="bg-white rounded-lg p-4 border border-gray-200">
                              <div className="flex items-center justify-between mb-3">
                                <span className="text-xs text-gray-500">Classification</span>
                                <span className={`inline-block px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                                  gradcamData.predicted_class.includes('Normal') || gradcamData.predicted_class === 'cn'
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                                    : 'bg-orange-50 text-orange-700 border border-orange-100'
                                }`}>
                                  {gradcamData.gradcam.gradcam_class_name}
                                </span>
                              </div>
                              
                              <div className="mb-3">
                                <div className="flex justify-between text-xs mb-1.5">
                                  <span className="text-gray-500">Confidence</span>
                                  <span className="text-gray-900 font-bold">{(gradcamData.confidence * 100).toFixed(1)}%</span>
                                </div>
                                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                                  <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${gradcamData.confidence * 100}%` }}
                                    transition={{ duration: 1, ease: "easeOut" }}
                                    className="h-full bg-gradient-to-r from-blue-500 to-teal-500 rounded-full"
                                  />
                                </div>
                              </div>
                              
                              <div className="flex items-center gap-2 text-xs">
                                <span className="text-gray-400">Layer:</span>
                                <code className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-[11px] font-mono">
                                  {gradcamData.gradcam.target_layer}
                                </code>
                              </div>
                            </div>
                          </div>
                          
                          <div>
                            <h3 className="text-gray-800 font-semibold text-sm mb-3 flex items-center gap-2">
                              <Eye className="text-violet-600" size={16} />
                              Attention Legend
                            </h3>
                            
                            <div className="bg-white rounded-lg p-4 border border-gray-200">
                              <div className="h-4 rounded-md bg-gradient-to-r from-blue-600 via-cyan-500 via-green-500 via-yellow-500 via-orange-500 to-red-600 mb-2" />
                              <div className="flex justify-between text-[10px] text-gray-500">
                                <span>Low</span>
                                <span>Mild</span>
                                <span>Moderate</span>
                                <span>High</span>
                                <span>Critical</span>
                              </div>
                            </div>
                          </div>
                          
                          <div>
                            <h3 className="text-gray-800 font-semibold text-sm mb-3 flex items-center gap-2">
                              <Info className="text-amber-600" size={16} />
                              Key Insights
                            </h3>
                            
                            <div className="space-y-2">
                              <div className="flex items-start gap-2.5 bg-white rounded-lg p-3 border border-gray-200">
                                <div className="w-6 h-6 rounded bg-red-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                                  <div className="w-2 h-2 rounded-full bg-red-500" />
                                </div>
                                <div>
                                  <p className="text-gray-800 text-xs font-medium">High Attention Regions</p>
                                  <p className="text-gray-500 text-[11px] mt-0.5">Red/orange areas are most relevant to the diagnosis</p>
                                </div>
                              </div>
                              
                              <div className="flex items-start gap-2.5 bg-white rounded-lg p-3 border border-gray-200">
                                <div className="w-6 h-6 rounded bg-emerald-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                                  <Brain className="w-3 h-3 text-emerald-600" />
                                </div>
                                <div>
                                  <p className="text-gray-800 text-xs font-medium">Neural Network Focus</p>
                                  <p className="text-gray-500 text-[11px] mt-0.5">Structural patterns in highlighted brain regions</p>
                                </div>
                              </div>
                              
                              <div className="flex items-start gap-2.5 bg-white rounded-lg p-3 border border-gray-200">
                                <div className="w-6 h-6 rounded bg-blue-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                                  <TrendingUp className="w-3 h-3 text-blue-600" />
                                </div>
                                <div>
                                  <p className="text-gray-800 text-xs font-medium">Clinical Correlation</p>
                                  <p className="text-gray-500 text-[11px] mt-0.5">Maps align with known pathological markers</p>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* 3D Slice Explorer View */}
                    {activeView === 'sliceExplorer' && (
                      <div className="p-6">
                        {slicesLoading && (
                          <div className="flex flex-col items-center justify-center py-20">
                            <div className="relative">
                              <div className="w-16 h-16 rounded-full border-4 border-gray-200 border-t-violet-500 animate-spin" />
                              <ScanLine className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-violet-500" size={24} />
                            </div>
                            <p className="text-gray-700 mt-6 font-medium">Generating multi-slice Grad-CAM++...</p>
                            <p className="text-gray-400 text-sm mt-1">Analyzing all axial slices across the MRI volume</p>
                          </div>
                        )}

                        {slicesError && (
                          <div className="bg-red-50 border border-red-200 rounded-lg p-5">
                            <div className="flex items-center gap-3">
                              <AlertCircle className="text-red-500" size={20} />
                              <div>
                                <p className="font-semibold text-red-700 text-sm">Slice Explorer Error</p>
                                <p className="text-red-600 text-sm mt-0.5">{slicesError}</p>
                              </div>
                            </div>
                          </div>
                        )}

                        {slicesData && slicesData.slices.length > 0 && (
                          <div className="grid lg:grid-cols-3 gap-6">
                            {/* Main image viewer */}
                            <div className="lg:col-span-2 space-y-4">
                              <div className="flex items-center gap-2 mb-2">
                                <div className="flex gap-1">
                                  {(['overlay', 'original', 'heatmap'] as const).map((mode) => (
                                    <button
                                      key={mode}
                                      onClick={() => setSliceViewMode(mode)}
                                      className={`px-3 py-1 text-xs rounded-full font-medium transition-all ${
                                        sliceViewMode === mode
                                          ? 'bg-violet-600 text-white shadow-sm'
                                          : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                                      }`}
                                    >
                                      {mode === 'overlay' ? 'Overlay' : mode === 'original' ? 'Original' : 'Heatmap'}
                                    </button>
                                  ))}
                                </div>
                              </div>

                              <div className="rounded-xl overflow-hidden border border-gray-200 bg-black relative">
                                <img
                                  src={`data:image/png;base64,${
                                    sliceViewMode === 'overlay'
                                      ? slicesData.slices[currentSlicePos].overlay_base64
                                      : sliceViewMode === 'original'
                                      ? slicesData.slices[currentSlicePos].original_base64
                                      : slicesData.slices[currentSlicePos].heatmap_base64
                                  }`}
                                  alt={`Slice ${slicesData.slices[currentSlicePos].index}`}
                                  className="w-full h-auto max-h-[500px] object-contain mx-auto"
                                />
                                <div className="absolute bottom-3 left-3 bg-black/70 text-white text-xs px-3 py-1.5 rounded-full backdrop-blur-sm">
                                  Slice {slicesData.slices[currentSlicePos].index} / {slicesData.total_slices}
                                </div>
                                {slicesData.slices[currentSlicePos].index === slicesData.best_slice_index && (
                                  <div className="absolute top-3 right-3 bg-amber-500/90 text-white text-xs px-3 py-1.5 rounded-full backdrop-blur-sm font-medium">
                                    Best Slice
                                  </div>
                                )}
                              </div>

                              {/* Playback controls */}
                              <div className="flex items-center justify-center gap-3">
                                <Button
                                  variant="outline" size="sm"
                                  onClick={() => setCurrentSlicePos(0)}
                                  className="h-9 w-9 p-0"
                                >
                                  <SkipBack size={16} />
                                </Button>
                                <Button
                                  variant="outline" size="sm"
                                  onClick={() => {
                                    if (isPlaying) {
                                      setIsPlaying(false)
                                    } else {
                                      if (currentSlicePos >= slicesData.slices.length - 1) setCurrentSlicePos(0)
                                      setIsPlaying(true)
                                    }
                                  }}
                                  className={`h-10 w-10 p-0 rounded-full ${isPlaying ? 'bg-violet-600 text-white border-violet-600 hover:bg-violet-700' : ''}`}
                                >
                                  {isPlaying ? <Pause size={18} /> : <Play size={18} />}
                                </Button>
                                <Button
                                  variant="outline" size="sm"
                                  onClick={() => setCurrentSlicePos(slicesData.slices.length - 1)}
                                  className="h-9 w-9 p-0"
                                >
                                  <SkipForward size={16} />
                                </Button>
                                <Button
                                  variant="outline" size="sm"
                                  onClick={() => {
                                    const bestPos = slicesData.slices.findIndex(s => s.index === slicesData.best_slice_index)
                                    if (bestPos >= 0) setCurrentSlicePos(bestPos)
                                  }}
                                  className="text-xs h-9 px-3 text-amber-600 border-amber-300 hover:bg-amber-50"
                                >
                                  Jump to Best
                                </Button>
                              </div>

                              {/* Range slider */}
                              <div className="relative px-1">
                                <input
                                  type="range"
                                  min={0}
                                  max={slicesData.slices.length - 1}
                                  value={currentSlicePos}
                                  onChange={(e) => {
                                    setIsPlaying(false)
                                    setCurrentSlicePos(Number(e.target.value))
                                  }}
                                  className="w-full accent-violet-600"
                                />
                                {(() => {
                                  const bestPos = slicesData.slices.findIndex(s => s.index === slicesData.best_slice_index)
                                  if (bestPos < 0) return null
                                  const pct = (bestPos / (slicesData.slices.length - 1)) * 100
                                  return (
                                    <div
                                      className="absolute top-0 w-2 h-2 rounded-full bg-amber-500 -translate-x-1/2 pointer-events-none"
                                      style={{ left: `${pct}%` }}
                                    />
                                  )
                                })()}
                              </div>

                              {/* Mini confidence chart */}
                              <div className="flex items-end gap-[2px] h-12 px-1">
                                {slicesData.slices.map((s, i) => {
                                  const maxConf = Math.max(...slicesData.slices.map(sl => sl.confidence))
                                  const hPct = maxConf > 0 ? (s.confidence / maxConf) * 100 : 0
                                  return (
                                    <div
                                      key={s.index}
                                      onClick={() => { setIsPlaying(false); setCurrentSlicePos(i) }}
                                      className={`flex-1 rounded-t cursor-pointer transition-all ${
                                        i === currentSlicePos
                                          ? 'bg-violet-500'
                                          : s.index === slicesData.best_slice_index
                                          ? 'bg-amber-400'
                                          : 'bg-gray-300 hover:bg-gray-400'
                                      }`}
                                      style={{ height: `${Math.max(hPct, 4)}%` }}
                                      title={`Slice ${s.index}: ${(s.confidence * 100).toFixed(1)}%`}
                                    />
                                  )
                                })}
                              </div>
                              <p className="text-gray-400 text-[10px] text-center -mt-2">Per-slice confidence distribution</p>
                            </div>

                            {/* Side panel */}
                            <div className="space-y-4">
                              <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                                <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                  <Activity className="text-violet-600" size={16} />
                                  Current Slice
                                </h4>
                                <div className="space-y-2 text-xs">
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">Slice Index</span>
                                    <span className="font-mono font-semibold text-gray-800">
                                      {slicesData.slices[currentSlicePos].index}
                                    </span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">Prediction</span>
                                    <span className="font-semibold text-gray-800">
                                      {slicesData.slices[currentSlicePos].predicted_class_name}
                                    </span>
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-gray-500">Confidence</span>
                                      <span className="font-bold text-gray-800">
                                        {(slicesData.slices[currentSlicePos].confidence * 100).toFixed(1)}%
                                      </span>
                                    </div>
                                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                      <div
                                        className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 rounded-full transition-all duration-200"
                                        style={{ width: `${slicesData.slices[currentSlicePos].confidence * 100}%` }}
                                      />
                                    </div>
                                  </div>
                                </div>
                              </div>

                              <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                                <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                  <Layers className="text-blue-600" size={16} />
                                  Volume Info
                                </h4>
                                <div className="space-y-2 text-xs">
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">Total Slices</span>
                                    <span className="font-mono text-gray-800">{slicesData.total_slices}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">Sampled</span>
                                    <span className="font-mono text-gray-800">{slicesData.slices.length}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">Best Slice</span>
                                    <span className="font-mono text-amber-600 font-semibold">
                                      #{slicesData.best_slice_index}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                                <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                  <Eye className="text-amber-600" size={16} />
                                  Heatmap Legend
                                </h4>
                                <div className="h-3 rounded-md bg-gradient-to-r from-blue-600 via-cyan-500 via-green-500 via-yellow-500 via-orange-500 to-red-600 mb-1.5" />
                                <div className="flex justify-between text-[10px] text-gray-500">
                                  <span>Low</span>
                                  <span>Moderate</span>
                                  <span>Critical</span>
                                </div>
                              </div>

                              <div className="bg-violet-50 rounded-xl p-4 border border-violet-200">
                                <h4 className="text-sm font-semibold text-violet-800 mb-2 flex items-center gap-2">
                                  <Info className="text-violet-600" size={16} />
                                  How to Use
                                </h4>
                                <ul className="text-[11px] text-violet-700 space-y-1.5 leading-relaxed">
                                  <li>Drag the slider or click confidence bars to browse slices</li>
                                  <li>Press Play to animate through the volume</li>
                                  <li>The amber marker indicates the most diagnostically relevant slice</li>
                                  <li>Toggle between Overlay, Original, and Heatmap views</li>
                                </ul>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Bottom Stats Bar */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-gray-100 border-t border-gray-100">
                      <div className="bg-white p-3 text-center">
                        <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-0.5">Detection ID</p>
                        <p className="text-gray-700 font-mono text-xs">{gradcamData.detection_id.slice(0, 12)}...</p>
                      </div>
                      <div className="bg-white p-3 text-center">
                        <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-0.5">Model Type</p>
                        <p className="text-blue-600 font-semibold text-xs">
                          {gradcamData.model_type === 'binary' ? 'Binary Detector' : 'Subtype Classifier'}
                        </p>
                      </div>
                      <div className="bg-white p-3 text-center">
                        <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-0.5">Analysis Layer</p>
                        <p className="text-gray-600 font-mono text-xs">{gradcamData.gradcam.target_layer}</p>
                      </div>
                      <div className="bg-white p-3 text-center">
                        <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-0.5">Grad-CAM Class</p>
                        <p className="text-emerald-600 font-semibold text-xs">{gradcamData.gradcam.gradcam_class_name}</p>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Footer Actions */}
        {detectionId && gradcamData && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="flex justify-center gap-3 mt-6"
          >
            <Button 
              onClick={() => router.push(`/detection?detection_id=${detectionId}`)}
              variant="outline"
              size="sm"
            >
              <ArrowLeft className="mr-1.5" size={14} />
              Back to Results
            </Button>
            <Button 
              onClick={() => fetchGradCAMData(detectionId)}
              variant="outline"
              size="sm"
            >
              <RefreshCw className="mr-1.5" size={14} />
              Refresh
            </Button>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default function ExplainableAIPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-background">
          <Loader2 className="h-10 w-10 animate-spin text-[#4ADE80]" aria-label="Loading" />
        </div>
      }
    >
      <ExplainableAIContent />
    </Suspense>
  )
}
