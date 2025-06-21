'use client'

import { useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { useAgentLogs } from '@/lib/hooks/use-agent-logs'
import { Zap, Trash2, Info } from 'lucide-react'
import { LogEntry } from './agent-log-entry'

interface AgentLogsProps {
  incidentId?: string
  className?: string
}

const stageLabels: Record<string, string> = {
  activation: '🚨 AI Agent Activated',
  webhook_received: '📨 Webhook Received',
  agent_triggered: '🤖 Agent Triggered',
  gathering_context: '🔍 Gathering Context',
  claude_analysis: '🤖 Claude Analysis',
  complete: '✅ Analysis Complete',
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
    <Card className={`${className} overflow-hidden`}>
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
      
      <CardContent className="p-0 overflow-hidden">
        <ScrollArea 
          ref={scrollAreaRef}
          className="h-[400px] border-t overflow-hidden" 
          onScroll={handleScroll}
        >
          <div className="p-4 space-y-2 overflow-hidden">
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