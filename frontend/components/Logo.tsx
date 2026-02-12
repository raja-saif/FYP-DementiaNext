'use client'

import React from 'react'

export default function Logo({ className = "", size = 60 }: { className?: string, size?: number }) {
  return (
    <div className="cursor-pointer">
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        className={className}
      >
        <defs>
          <linearGradient id="umbrellaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0066cc" />
            <stop offset="50%" stopColor="#00a896" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>
        </defs>
        
        {/* Main umbrella canopy */}
        <path
          d="M 50 25 Q 20 35, 15 50 Q 15 55, 20 55 L 35 55 Q 40 50, 45 55 L 55 55 Q 60 50, 65 55 L 80 55 Q 85 55, 85 50 Q 80 35, 50 25 Z"
          fill="url(#umbrellaGradient)"
          stroke="#0066cc"
          strokeWidth="2"
        />
        
        {/* Umbrella handle */}
        <path
          d="M 50 55 L 50 80 Q 50 85, 45 85"
          stroke="#0066cc"
          strokeWidth="3"
          fill="none"
          strokeLinecap="round"
        />
        
        {/* AD label (Alzheimer's Disease) */}
        <circle cx="30" cy="65" r="8" fill="#0066cc" />
        <text x="30" y="68" fontSize="7" fill="white" textAnchor="middle" fontWeight="bold">AD</text>
        
        {/* FTD label (Frontotemporal Dementia) */}
        <circle cx="50" cy="70" r="8" fill="#00a896" />
        <text x="50" y="73" fontSize="6" fill="white" textAnchor="middle" fontWeight="bold">FTD</text>
        
        {/* PDD label (Parkinson's Dementia) */}
        <circle cx="70" cy="65" r="8" fill="#10b981" />
        <text x="70" y="68" fontSize="6" fill="white" textAnchor="middle" fontWeight="bold">PDD</text>
      </svg>
    </div>
  )
}