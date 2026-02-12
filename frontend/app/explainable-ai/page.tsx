'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Navigation from '@/components/Navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Eye, Brain, Activity, TrendingUp, AlertCircle, Info, Download, Loader2 } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

export default function ExplainableAIPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  
  // NOTE: Feature intentionally deferred. UI kept read-only to avoid edits.
  const [selectedRegion, setSelectedRegion] = useState<string | null>('hippocampus')

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

  const brainRegions = [
    {
      id: 'hippocampus',
      name: 'Hippocampus',
      importance: 95,
      status: 'Severely Affected',
      color: 'from-red-500 to-red-600',
      description: 'Critical for memory formation. Significant atrophy detected.',
      findings: [
        'Volume reduction: 32% below normal',
        'Bilateral atrophy observed',
        'Strong predictor of AD diagnosis'
      ]
    },
    {
      id: 'temporalLobe',
      name: 'Temporal Lobe',
      importance: 88,
      status: 'Moderately Affected',
      color: 'from-orange-500 to-orange-600',
      description: 'Involved in memory and language. Noticeable thinning.',
      findings: [
        'Cortical thinning: 18% reduction',
        'Affects language processing',
        'Correlates with cognitive decline'
      ]
    },
    {
      id: 'frontalLobe',
      name: 'Frontal Lobe',
      importance: 72,
      status: 'Mildly Affected',
      color: 'from-yellow-500 to-yellow-600',
      description: 'Executive function center. Early stage changes.',
      findings: [
        'Minor volume loss: 8%',
        'Decision-making impact',
        'May worsen over time'
      ]
    },
    {
      id: 'parietalLobe',
      name: 'Parietal Lobe',
      importance: 65,
      status: 'Early Changes',
      color: 'from-blue-500 to-blue-600',
      description: 'Sensory processing area. Minimal changes detected.',
      findings: [
        'Slight metabolic changes',
        'Spatial awareness intact',
        'Monitor for progression'
      ]
    }
  ]

  const biomarkers = [
    {
      name: 'Amyloid-β Plaques',
      level: 'Elevated',
      impact: 92,
      color: 'from-red-500 to-pink-500',
      explanation: 'Abnormal protein deposits strongly associated with Alzheimer\'s Disease'
    },
    {
      name: 'Tau Protein',
      level: 'High',
      impact: 88,
      color: 'from-orange-500 to-red-500',
      explanation: 'Elevated levels indicate neuronal damage and cognitive decline'
    },
    {
      name: 'APOE-ε4 Gene',
      level: 'Positive',
      impact: 75,
      color: 'from-purple-500 to-pink-500',
      explanation: 'Genetic risk factor increases likelihood of developing AD'
    },
    {
      name: 'Brain Glucose Metabolism',
      level: 'Reduced',
      impact: 70,
      color: 'from-blue-500 to-cyan-500',
      explanation: 'Decreased energy usage in brain regions, common in dementia'
    }
  ]

  const currentRegion = brainRegions.find(r => r.id === selectedRegion)

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50">
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
            <div className="w-20 h-20 rounded-full bg-gradient-to-r from-green-500 to-blue-500 flex items-center justify-center">
              <Eye className="text-white" size={40} />
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
              Explainable AI Insights
            </span>
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Transparent visualization of brain regions and biomarkers influencing the diagnosis
          </p>
          <div className="mt-6 flex items-center justify-center gap-4">
            <Badge className="text-sm px-4 py-2">Patient ID: PT-2025-001</Badge>
            <Badge variant="secondary" className="text-sm px-4 py-2">Diagnosis: AD</Badge>
            <Badge variant="outline" className="text-sm px-4 py-2">Confidence: 94.2%</Badge>
          </div>
        </motion.div>

        {/* Brain Region Analysis */}
        <div className="grid lg:grid-cols-3 gap-8 mb-12">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-2"
          >
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain size={24} />
                  Brain Region Importance Map
                </CardTitle>
                <CardDescription>
                  AI-identified regions contributing to diagnosis - click to explore
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* Brain Visualization */}
                <div className="relative bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-8 mb-6">
                  <div className="relative w-full aspect-square max-w-md mx-auto">
                    {/* SVG Brain visualization */}
                    <svg viewBox="0 0 200 200" className="w-full h-full">
                      <defs>
                        <radialGradient id="brainGlow">
                          <stop offset="0%" stopColor="#667eea" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="#764ba2" stopOpacity="0" />
                        </radialGradient>
                      </defs>
                      
                      {/* Glowing background */}
                      <circle cx="100" cy="100" r="90" fill="url(#brainGlow)" />
                      
                      {/* Hippocampus (center-bottom) */}
                      <ellipse
                        cx="100"
                        cy="120"
                        rx="25"
                        ry="15"
                        fill={selectedRegion === 'hippocampus' ? '#ef4444' : '#fca5a5'}
                        className="cursor-pointer transition-all hover:opacity-80"
                        onClick={() => setSelectedRegion('hippocampus')}
                        opacity={selectedRegion === 'hippocampus' ? 1 : 0.6}
                      />
                      
                      {/* Temporal Lobe (sides) */}
                      <path
                        d="M 40 100 Q 30 120, 40 140 L 60 130 Q 50 110, 60 100 Z"
                        fill={selectedRegion === 'temporalLobe' ? '#f97316' : '#fdba74'}
                        className="cursor-pointer transition-all hover:opacity-80"
                        onClick={() => setSelectedRegion('temporalLobe')}
                        opacity={selectedRegion === 'temporalLobe' ? 1 : 0.6}
                      />
                      <path
                        d="M 160 100 Q 170 120, 160 140 L 140 130 Q 150 110, 140 100 Z"
                        fill={selectedRegion === 'temporalLobe' ? '#f97316' : '#fdba74'}
                        className="cursor-pointer transition-all hover:opacity-80"
                        onClick={() => setSelectedRegion('temporalLobe')}
                        opacity={selectedRegion === 'temporalLobe' ? 1 : 0.6}
                      />
                      
                      {/* Frontal Lobe (top-front) */}
                      <ellipse
                        cx="100"
                        cy="60"
                        rx="40"
                        ry="30"
                        fill={selectedRegion === 'frontalLobe' ? '#eab308' : '#fde047'}
                        className="cursor-pointer transition-all hover:opacity-80"
                        onClick={() => setSelectedRegion('frontalLobe')}
                        opacity={selectedRegion === 'frontalLobe' ? 1 : 0.6}
                      />
                      
                      {/* Parietal Lobe (top-back) */}
                      <ellipse
                        cx="100"
                        cy="80"
                        rx="35"
                        ry="25"
                        fill={selectedRegion === 'parietalLobe' ? '#3b82f6' : '#93c5fd'}
                        className="cursor-pointer transition-all hover:opacity-80"
                        onClick={() => setSelectedRegion('parietalLobe')}
                        opacity={selectedRegion === 'parietalLobe' ? 1 : 0.6}
                      />
                      
                      {/* Connecting lines and labels */}
                      <text x="100" y="195" textAnchor="middle" fontSize="10" fill="#666" fontWeight="500">
                        Click regions to view details
                      </text>
                    </svg>
                  </div>
                </div>

                {/* Region List */}
                <div className="space-y-3">
                  {brainRegions.map((region) => (
                    <div
                      key={region.id}
                      onClick={() => setSelectedRegion(region.id)}
                      className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                        selectedRegion === region.id
                          ? 'border-purple-400 bg-purple-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold">{region.name}</span>
                        <Badge variant="secondary">{region.status}</Badge>
                      </div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm text-gray-600">Importance:</span>
                        <div className="flex-1">
                          <Progress value={region.importance} className="h-2" />
                        </div>
                        <span className="text-sm font-bold text-purple-600">{region.importance}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Selected Region Details */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
          >
            {currentRegion && (
              <Card className="border-2 border-purple-200 sticky top-24">
                <CardHeader>
                  <CardTitle className="text-lg">{currentRegion.name}</CardTitle>
                  <CardDescription>
                    Detailed Analysis
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className={`w-full h-2 rounded-full bg-gradient-to-r ${currentRegion.color} mb-3`} />
                    <p className="text-sm text-gray-700 mb-4">
                      {currentRegion.description}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <div className="font-semibold text-sm text-gray-700 mb-2">Key Findings:</div>
                    {currentRegion.findings.map((finding, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <AlertCircle className="text-purple-600 flex-shrink-0 mt-0.5" size={16} />
                        <span className="text-sm">{finding}</span>
                      </div>
                    ))}
                  </div>

                  <div className="pt-4 border-t">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Impact on Diagnosis</span>
                      <span className="text-2xl font-bold text-purple-600">
                        {currentRegion.importance}%
                      </span>
                    </div>
                    <Progress value={currentRegion.importance} className="h-3" />
                  </div>
                </CardContent>
              </Card>
            )}
          </motion.div>
        </div>

        {/* Biomarkers Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mb-12"
        >
          <Card className="border-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity size={24} />
                Biomarker Analysis
              </CardTitle>
              <CardDescription>
                Key biological markers contributing to the diagnosis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-6">
                {biomarkers.map((marker, idx) => (
                  <motion.div
                    key={marker.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: idx * 0.1 }}
                    className="p-6 rounded-xl border-2 border-gray-200 hover:border-purple-300 transition-all"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-lg">{marker.name}</h3>
                      <Badge className={`bg-gradient-to-r ${marker.color}`}>
                        {marker.level}
                      </Badge>
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-4">{marker.explanation}</p>
                    
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Impact on Diagnosis</span>
                        <span className="font-bold text-purple-600">{marker.impact}%</span>
                      </div>
                      <Progress value={marker.impact} className="h-2" />
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Feature Importance Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mb-12"
        >
          <Card className="border-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp size={24} />
                Overall Feature Importance
              </CardTitle>
              <CardDescription>
                Ranked factors contributing to AI decision
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { name: 'Hippocampal Atrophy', value: 95 },
                  { name: 'Amyloid-β Levels', value: 92 },
                  { name: 'Tau Protein', value: 88 },
                  { name: 'Temporal Lobe Changes', value: 88 },
                  { name: 'APOE-ε4 Status', value: 75 },
                  { name: 'Frontal Lobe Volume', value: 72 },
                  { name: 'Brain Metabolism', value: 70 },
                  { name: 'Parietal Lobe Changes', value: 65 },
                  { name: 'White Matter Integrity', value: 58 },
                  { name: 'Cognitive Test Scores', value: 52 }
                ].map((feature, idx) => (
                  <div key={feature.name}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{feature.name}</span>
                      <span className="font-bold text-purple-600">{feature.value}%</span>
                    </div>
                    <Progress value={feature.value} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Explanation Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <Card className="border-2 border-blue-200 bg-blue-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info size={24} />
                AI Decision Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-700 leading-relaxed">
                The AI model classified this case as <strong>Alzheimer's Disease (AD)</strong> with{' '}
                <strong>94.2% confidence</strong> based on multiple converging factors:
              </p>
              
              <div className="bg-white rounded-lg p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-red-500 mt-2" />
                  <p className="text-sm">
                    <strong>Primary Factor:</strong> Severe hippocampal atrophy (32% volume reduction) 
                    is the strongest indicator, as this region is critical for memory formation.
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-orange-500 mt-2" />
                  <p className="text-sm">
                    <strong>Supporting Evidence:</strong> Elevated amyloid-β plaques and tau protein 
                    levels are hallmark biomarkers of Alzheimer's Disease.
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-yellow-500 mt-2" />
                  <p className="text-sm">
                    <strong>Genetic Component:</strong> Positive APOE-ε4 gene increases risk and 
                    supports the AD classification over other dementia subtypes.
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-2" />
                  <p className="text-sm">
                    <strong>Pattern Recognition:</strong> The combination of affected brain regions 
                    matches the typical AD progression pattern rather than FTD or PDD.
                  </p>
                </div>
              </div>

              <div className="flex gap-4 pt-4">
                <Button className="flex-1">
                  <Download className="mr-2" />
                  Download Detailed Report
                </Button>
                <Button variant="outline" className="flex-1">
                  View Patient Dashboard
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}


