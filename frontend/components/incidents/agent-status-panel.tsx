'use client'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { AlertCircle, Zap, CheckCircle, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AgentStatusPanelProps {
  activeIncidents: Set<string>
  currentStage?: string
  currentProgress?: number
  className?: string
}

const stageInfo: Record<string, { label: string; description: string }> = {
  activation: { 
    label: '🚨 AI Agent Activated', 
    description: 'Processing incoming incident...' 
  },
  webhook_received: { 
    label: '📨 Webhook Received', 
    description: 'Validating and parsing alert data...' 
  },
  agent_triggered: { 
    label: '🤖 Agent Triggered', 
    description: 'Initializing analysis pipeline...' 
  },
  gathering_context: { 
    label: '🔍 Gathering Context', 
    description: 'Collecting data from integrations...' 
  },
  claude_analysis: { 
    label: '🤖 Claude Analysis', 
    description: 'AI is analyzing the incident...' 
  },
  complete: { 
    label: '✅ Analysis Complete', 
    description: 'Recommendations are ready!' 
  },
}

export function AgentStatusPanel({
  activeIncidents,
  currentStage,
  currentProgress = 0,
  className
}: AgentStatusPanelProps) {
  const isActive = activeIncidents.size > 0
  const isComplete = currentStage === 'complete' || currentProgress >= 1
  
  if (!isActive && !isComplete) {
    return null
  }

  const stageData = currentStage ? stageInfo[currentStage] : null
  
  return (
    <Alert 
      className={cn(
        "transition-all duration-300",
        isActive && !isComplete && "border-red-600 bg-red-50",
        isComplete && "border-green-600 bg-green-50",
        className
      )}
    >
      <div className="flex items-start gap-3">
        {isActive && !isComplete ? (
          <Zap className="h-5 w-5 text-red-600 animate-pulse" />
        ) : (
          <CheckCircle className="h-5 w-5 text-green-600" />
        )}
        
        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between">
            <AlertTitle className="text-lg">
              {isActive && !isComplete ? (
                <>
                  <span className="text-red-700">AI AGENT ACTIVATED</span>
                  {activeIncidents.size > 1 && (
                    <Badge variant="destructive" className="ml-2">
                      {activeIncidents.size} incidents
                    </Badge>
                  )}
                </>
              ) : (
                <span className="text-green-700">AI ANALYSIS COMPLETE</span>
              )}
            </AlertTitle>
            
            {currentProgress > 0 && currentProgress < 1 && (
              <Badge variant="outline" className="gap-1">
                <Clock className="w-3 h-3" />
                {Math.round(currentProgress * 100)}%
              </Badge>
            )}
          </div>
          
          <AlertDescription>
            {stageData ? (
              <div className="space-y-2">
                <p className="text-sm font-medium">{stageData.label}</p>
                <p className="text-sm text-muted-foreground">{stageData.description}</p>
              </div>
            ) : (
              <p className="text-sm">
                {isActive 
                  ? `Processing ${activeIncidents.size} incident${activeIncidents.size > 1 ? 's' : ''}...`
                  : 'All incidents processed successfully.'
                }
              </p>
            )}
          </AlertDescription>
          
          {currentProgress > 0 && currentProgress < 1 && (
            <Progress value={currentProgress * 100} className="h-2 mt-3" />
          )}
        </div>
      </div>
    </Alert>
  )
}