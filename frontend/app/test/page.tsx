'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'

export default function TestPage() {
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(false)

  const handleClick = () => {
    setCount(count + 1)
  }

  const handleAsyncClick = async () => {
    setLoading(true)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    setLoading(false)
    setCount(count + 1)
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
        <h1 className="text-2xl font-bold mb-6 text-center">Button Test</h1>
        
        <div className="space-y-4">
          <div className="text-center">
            <p className="text-lg mb-2">Count: {count}</p>
          </div>
          
          <Button 
            onClick={handleClick}
            className="w-full"
          >
            Click Me (Instant)
          </Button>
          
          <Button 
            onClick={handleAsyncClick}
            disabled={loading}
            className="w-full"
          >
            {loading ? 'Loading...' : 'Click Me (Async)'}
          </Button>
          
          <Button 
            onClick={() => window.location.href = '/login'}
            variant="outline"
            className="w-full"
          >
            Go to Login
          </Button>
        </div>
      </div>
    </div>
  )
}


