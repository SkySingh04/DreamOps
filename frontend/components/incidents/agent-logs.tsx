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
    <Card className={`${className} overflow-hidden w-full max-w-full`} style={{ maxWidth: '100%', width: '100%', overflowX: 'hidden' }}>
      <CardHeader className="w-full max-w-full overflow-hidden" style={{ maxWidth: '100%', width: '100%', overflowX: 'hidden' }}>
        <div className="flex items-center justify-between min-w-0 w-full max-w-full overflow-hidden" style={{ maxWidth: '100%', width: '100%', overflowX: 'hidden' }}>
          <div className="min-w-0 flex-1 overflow-hidden max-w-full">
            <CardTitle className="flex items-center gap-2 min-w-0 w-full max-w-full overflow-hidden">
              <Zap className="w-5 h-5 flex-shrink-0" />
              <span className="truncate flex-1 min-w-0">AI Agent Logs</span>
            </CardTitle>
            <CardDescription className="flex items-center gap-2 mt-1 w-full max-w-full overflow-hidden">
              <span className="truncate flex-1 min-w-0">Real-time logs from the AI agent processing</span>
              <div className="flex items-center gap-2 flex-shrink-0">
                {activeIncidents.size > 0 && (
                  <Badge variant="destructive" className="animate-pulse flex-shrink-0">
                    {activeIncidents.size} Active
                  </Badge>
                )}
                <Badge variant={isConnected ? "default" : "secondary"} className="flex-shrink-0">
                  {isConnected ? "● Connected" : "○ Disconnected"}
                </Badge>
              </div>
            </CardDescription>
          </div>
          
          <div className="flex items-center gap-2 flex-shrink-0 overflow-hidden">
            <Button
              variant="ghost"
              size="sm"
              onClick={clearLogs}
              className="h-8 w-8 p-0 flex-shrink-0"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        {currentProgress !== undefined && currentProgress < 1 && (
          <div className="mt-4 space-y-2 w-full max-w-full overflow-hidden">
            <div className="flex items-center justify-between text-sm w-full max-w-full overflow-hidden">
              <span className="text-muted-foreground truncate flex-1 min-w-0">
                {currentStage && stageLabels[currentStage]}
              </span>
              <span className="text-muted-foreground flex-shrink-0">
                {Math.round((currentProgress || 0) * 100)}%
              </span>
            </div>
            <Progress value={(currentProgress || 0) * 100} className="h-2 w-full max-w-full" />
          </div>
        )}
      </CardHeader>
      
      <CardContent className="p-0 overflow-hidden w-full max-w-full" style={{ maxWidth: '100%', width: '100%', overflowX: 'hidden' }}>
        <ScrollArea 
          ref={scrollAreaRef}
          className="h-[400px] border-t overflow-hidden w-full max-w-full" 
          onScroll={handleScroll}
          style={{ maxWidth: '100%', width: '100%', overflowX: 'hidden' }}
        >
          <div className="p-4 space-y-2 overflow-hidden w-full max-w-full" style={{ maxWidth: '100%', width: '100%', overflowX: 'hidden', wordBreak: 'break-all' }}>
            {relevantLogs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground w-full max-w-full overflow-hidden">
                <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm w-full max-w-full overflow-hidden">Waiting for AI agent activity...</p>
              </div>
            ) : (
              relevantLogs.map((log, index) => (
                <div 
                  key={`${log.timestamp}-${index}`} 
                  className="w-full max-w-full overflow-hidden" 
                  style={{ maxWidth: '100%', width: '100%', overflowX: 'hidden', wordBreak: 'break-all' }}
                >
                  <LogEntry log={log} />
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}