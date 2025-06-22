'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { 
  Info, 
  AlertTriangle, 
  XCircle, 
  CheckCircle, 
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Copy,
  Check
} from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { AgentLogEntry } from '@/lib/hooks/use-agent-logs'

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

interface LogEntryProps {
  log: AgentLogEntry
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Button
      size="sm"
      variant="ghost"
      className="h-6 px-2"
      onClick={handleCopy}
    >
      {copied ? (
        <Check className="h-3 w-3" />
      ) : (
        <Copy className="h-3 w-3" />
      )}
    </Button>
  )
}

export function LogEntry({ log }: LogEntryProps) {
  // Check if this is an analysis complete log with full analysis
  const hasFullAnalysis = log.stage === 'complete' && log.metadata?.analysis
  const shouldShowExpandButton = hasFullAnalysis || (log.metadata && Object.keys(log.metadata).length > 3)
  
  // Auto-expand analysis logs by default
  const [isExpanded, setIsExpanded] = useState(hasFullAnalysis)
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
      "rounded-lg transition-colors overflow-hidden",
      log.level === 'ALERT' && "bg-red-50 border border-red-200",
      log.level === 'ERROR' && "bg-red-50/50",
      log.level === 'SUCCESS' && "bg-green-50/50"
    )}>
      <div className="flex items-start gap-3 p-3 overflow-hidden">
        <Icon className={cn("w-4 h-4 mt-0.5 flex-shrink-0", config.color)} />
        
        <div className="flex-1 space-y-1 min-w-0 overflow-hidden">
          <div className="flex items-center gap-2 flex-wrap">
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
          
          <p className="text-sm break-words">{log.message}</p>
          
          {/* Basic metadata (always visible) */}
          {log.metadata && !hasFullAnalysis && Object.keys(log.metadata).length > 0 && (
            <div className="text-xs text-muted-foreground mt-1">
              {Object.entries(log.metadata)
                .filter(([key]) => !['analysis', 'parsed_analysis'].includes(key))
                .slice(0, 3)
                .map(([key, value]) => (
                  <span key={key} className="mr-3">
                    <span className="font-medium">{key}:</span> {String(value)}
                  </span>
                ))}
            </div>
          )}
        </div>

        {shouldShowExpandButton && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-6 w-6 p-0"
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="pb-3 overflow-hidden">
          {hasFullAnalysis ? (
            <div className="mt-2 overflow-hidden max-w-full">
              <div className="markdown-content px-3 overflow-hidden max-w-full">
                <div className="overflow-x-auto max-w-full">
                  <ReactMarkdown
                  components={{
                    code({ node, className, children, ...props }: any) {
                      const match = /language-(\w+)/.exec(className || '')
                      const codeString = String(children).replace(/\n$/, '')
                      const isInline = !match && (!node || node.position?.start.line === node.position?.end.line)
                      
                      if (!isInline && match) {
                        return (
                          <div className="relative group">
                            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <CopyButton text={codeString} />
                            </div>
                            <SyntaxHighlighter
                              language={match[1]}
                              style={oneDark}
                              customStyle={{
                                margin: 0,
                                borderRadius: '0.375rem',
                                fontSize: '0.875rem',
                                maxWidth: '100%',
                                overflowX: 'auto',
                              }}
                              {...props}
                            >
                              {codeString}
                            </SyntaxHighlighter>
                          </div>
                        )
                      }
                      
                      if (isInline) {
                        return (
                          <code className="bg-gray-200 px-1 py-0.5 rounded text-sm font-mono" {...props}>
                            {children}
                          </code>
                        )
                      }
                      
                      return (
                        <div className="relative group">
                          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <CopyButton text={codeString} />
                          </div>
                          <pre className="bg-gray-900 text-gray-100 p-3 rounded overflow-x-auto">
                            <code {...props}>{children}</code>
                          </pre>
                        </div>
                      )
                    },
                    h1: ({ children }) => <h1 className="text-lg font-bold mt-4 mb-2">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-base font-semibold mt-3 mb-2">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>,
                    ul: ({ children }) => <ul className="list-disc pl-5 space-y-1 max-w-full">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1 max-w-full">{children}</ol>,
                    li: ({ children }) => <li className="text-sm break-words">{children}</li>,
                    p: ({ children }) => <p className="text-sm mb-2 break-words">{children}</p>,
                  }}
                  >
                    {log.metadata.analysis}
                  </ReactMarkdown>
                </div>
              </div>
              
              {/* Show parsed analysis summary */}
              {log.metadata.parsed_analysis && (
                <div className="mt-4 pt-4 border-t space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium">Confidence Score:</span>
                    <Badge variant="outline">{Math.round((log.metadata.confidence_score || 0.85) * 100)}%</Badge>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium">Risk Level:</span>
                    <Badge variant={log.metadata.risk_level === 'high' ? 'destructive' : 'secondary'}>
                      {log.metadata.risk_level || 'medium'}
                    </Badge>
                  </div>
                  {log.metadata.response_time && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium">Response Time:</span>
                      <span>{log.metadata.response_time}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            // Regular metadata display
            <div className="text-xs text-muted-foreground space-y-1">
              {Object.entries(log.metadata || {}).map(([key, value]) => (
                <div key={key}>
                  <span className="font-medium">{key}:</span>{' '}
                  {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}