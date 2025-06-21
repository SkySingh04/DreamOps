'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AIAnalysisDisplay } from './ai-analysis-display'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Brain, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

interface IncidentAIAnalysisProps {
  incidentId: string
  className?: string
}

export function IncidentAIAnalysis({ incidentId, className }: IncidentAIAnalysisProps) {
  const [analysisFromLogs, setAnalysisFromLogs] = useState<any>(null)
  
  // Fetch analysis from API
  const { data: analysisData, isLoading, error, refetch } = useQuery({
    queryKey: ['incident-analysis', incidentId],
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/incidents/${incidentId}/analysis`)
      if (!response.ok) throw new Error('Failed to fetch analysis')
      return response.json()
    },
  })

  // Set up polling for pending analysis
  useEffect(() => {
    if (analysisData?.status === 'pending') {
      const interval = setInterval(() => {
        refetch()
      }, 5000)
      
      return () => clearInterval(interval)
    }
  }, [analysisData?.status, refetch])
  
  // Listen for analysis from agent logs
  useEffect(() => {
    // This will be populated by the agent logs when analysis completes
    const handleLogUpdate = (event: CustomEvent) => {
      if (event.detail?.incident_id === incidentId && event.detail?.stage === 'complete') {
        const metadata = event.detail.metadata
        if (metadata?.analysis && metadata?.parsed_analysis) {
          setAnalysisFromLogs({
            analysis: metadata.analysis,
            parsed_analysis: metadata.parsed_analysis,
            confidence_score: metadata.confidence_score,
            risk_level: metadata.risk_level,
            response_time: metadata.response_time
          })
        }
      }
    }
    
    window.addEventListener('agent-log-update' as any, handleLogUpdate)
    return () => window.removeEventListener('agent-log-update' as any, handleLogUpdate)
  }, [incidentId])
  
  // Determine which analysis to show
  const analysis = analysisFromLogs || analysisData
  
  if (isLoading) {
    return (
      <div className={className}>
        <div className="flex items-center gap-2 mb-4">
          <Brain className="h-5 w-5" />
          <h3 className="font-semibold">AI Analysis</h3>
        </div>
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <Alert className={className}>
        <AlertDescription>
          Failed to load AI analysis. Please try again later.
        </AlertDescription>
      </Alert>
    )
  }
  
  if (analysis?.status === 'pending') {
    return (
      <div className={className}>
        <div className="flex items-center gap-2 mb-4">
          <Brain className="h-5 w-5" />
          <h3 className="font-semibold">AI Analysis</h3>
        </div>
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertDescription>
            AI analysis is being processed. This typically takes 10-30 seconds...
          </AlertDescription>
        </Alert>
      </div>
    )
  }
  
  if (analysis?.status === 'analyzed' || analysis?.parsed_analysis) {
    return (
      <AIAnalysisDisplay
        analysis={analysis.analysis || ''}
        timestamp={analysis.timestamp}
        responseTime={analysis.response_time || analysis.processing_time}
        parsedAnalysis={analysis.parsed_analysis}
        confidenceScore={analysis.confidence_score}
        riskLevel={analysis.risk_level}
        className={className}
      />
    )
  }
  
  return (
    <div className={className}>
      <div className="flex items-center gap-2 mb-4">
        <Brain className="h-5 w-5" />
        <h3 className="font-semibold">AI Analysis</h3>
      </div>
      <Alert>
        <AlertDescription>
          No AI analysis available for this incident.
        </AlertDescription>
      </Alert>
    </div>
  )
}