'use client'

import { useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { useAgentLogs, AgentLogEntry } from '@/lib/hooks/use-agent-logs'
import { AlertCircle, CheckCircle, Info, AlertTriangle, XCircle, Zap, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AgentLogsProps {
  incidentId?: string
  className?: string
}

const logLevelConfig = {
  DEBUG: { icon: Info, color: 'text-gray-500', bgColor: 'bg-gray-100', label: 'DEBUG' },
  INFO: { icon: Info, color: 'text-blue-600', bgColor: 'bg-blue-100', label: 'INFO' },
  WARNING: { icon: AlertTriangle, color: 'text-yellow-600', bgColor: 'bg-yellow-100', label: 'WARN' },
  ERROR: { icon: XCircle, color: 'text-red-600', bgColor: 'bg-red-100', label: 'ERROR' },
  SUCCESS: { icon: CheckCircle, color: 'text-green-600', bgColor: 'bg-green-100', label: 'SUCCESS' },
  ALERT: { icon: AlertCircle, color: 'text-red-700', bgColor: 'bg-red-200', label: 'ALERT' },
}

const stageLabels: Record<string, string> = {
  activation: '🚨 AI Agent Activated',
  webhook_received: '📨 Webhook Received',
  agent_triggered: '🤖 Agent Triggered',
  gathering_context: '🔍 Gathering Context',
  claude_analysis: '🤖 Claude Analysis',
  complete: '✅ Analysis Complete',
}

function LogEntry({ log }: { log: AgentLogEntry }) {
  const config = logLevelConfig[log.level]
  const Icon = config.icon
  
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      fractionalSecondDigits: 3 
    })
  }

  return (
    <div className={cn(
      "flex items-start gap-3 p-3 rounded-lg transition-colors",
      log.level === 'ALERT' && "bg-red-50 border border-red-200",
      log.level === 'ERROR' && "bg-red-50/50",
      log.level === 'SUCCESS' && "bg-green-50/50"
    )}>
      <Icon className={cn("w-4 h-4 mt-0.5 flex-shrink-0", config.color)} />
      
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-mono">
            {formatTimestamp(log.timestamp)}
          </span>
          <Badge variant="secondary" className={cn("text-xs", config.bgColor, config.color)}>
            {config.label}
          </Badge>
          {log.integration && (
            <Badge variant="outline" className="text-xs">
              {log.integration}
            </Badge>
          )}
          {log.stage && (
            <Badge variant="outline" className="text-xs">
              {stageLabels[log.stage] || log.stage}
            </Badge>
          )}
        </div>
        
        <p className="text-sm">{log.message}</p>
        
        {log.metadata && Object.keys(log.metadata).length > 0 && (
          <div className="text-xs text-muted-foreground mt-1">
            {Object.entries(log.metadata).map(([key, value]) => (
              <span key={key} className="mr-3">
                <span className="font-medium">{key}:</span> {String(value)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function AgentLogs({ incidentId, className }: AgentLogsProps) {
  const { logs, isConnected, activeIncidents, currentStage, currentProgress, clearLogs } = useAgentLogs(incidentId)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const shouldAutoScroll = useRef(true)
  
  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (shouldAutoScroll.current && scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [logs])

  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const target = event.target as HTMLDivElement
    const isAtBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 50
    shouldAutoScroll.current = isAtBottom
  }

  const relevantLogs = incidentId 
    ? logs.filter(log => !log.incident_id || log.incident_id === incidentId)
    : logs

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5" />
              AI Agent Logs
              {activeIncidents.size > 0 && (
                <Badge variant="destructive" className="animate-pulse">
                  {activeIncidents.size} Active
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Real-time logs from the AI agent processing
            </CardDescription>
          </div>
          
          <div className="flex items-center gap-2">
            <Badge variant={isConnected ? "default" : "secondary"}>
              {isConnected ? "● Connected" : "○ Disconnected"}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearLogs}
              className="h-8 w-8 p-0"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        {currentProgress !== undefined && currentProgress < 1 && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                {currentStage && stageLabels[currentStage]}
              </span>
              <span className="text-muted-foreground">
                {Math.round((currentProgress || 0) * 100)}%
              </span>
            </div>
            <Progress value={(currentProgress || 0) * 100} className="h-2" />
          </div>
        )}
      </CardHeader>
      
      <CardContent className="p-0">
        <ScrollArea 
          ref={scrollAreaRef}
          className="h-[400px] border-t" 
          onScroll={handleScroll}
        >
          <div className="p-4 space-y-2">
            {relevantLogs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Waiting for AI agent activity...</p>
              </div>
            ) : (
              relevantLogs.map((log, index) => (
                <LogEntry key={`${log.timestamp}-${index}`} log={log} />
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}