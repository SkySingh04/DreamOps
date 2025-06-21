'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Brain, 
  Zap, 
  Search, 
  AlertTriangle, 
  Wrench, 
  BarChart, 
  Rocket, 
  FileText,
  Copy,
  CheckCircle 
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface AIAnalysisDisplayProps {
  analysis: string
  timestamp?: string
  responseTime?: string
  className?: string
  parsedAnalysis?: any
  confidenceScore?: number
  riskLevel?: string
}

interface ParsedAnalysis {
  immediateActions?: string[]
  rootCause?: string[]
  impact?: string[]
  remediation?: string[]
  monitoring?: string[]
  automation?: string[]
  followUp?: string[]
}

const sectionIcons = {
  immediateActions: { icon: Zap, label: 'Immediate Actions', color: 'text-red-600' },
  rootCause: { icon: Search, label: 'Root Cause Analysis', color: 'text-orange-600' },
  impact: { icon: AlertTriangle, label: 'Impact Assessment', color: 'text-yellow-600' },
  remediation: { icon: Wrench, label: 'Remediation Steps', color: 'text-blue-600' },
  monitoring: { icon: BarChart, label: 'Monitoring', color: 'text-purple-600' },
  automation: { icon: Rocket, label: 'Automation Opportunities', color: 'text-green-600' },
  followUp: { icon: FileText, label: 'Follow-up Actions', color: 'text-gray-600' },
}

function parseAnalysis(analysis: string): ParsedAnalysis {
  const sections: ParsedAnalysis = {}
  const lines = analysis.split('\n')
  let currentSection: keyof ParsedAnalysis | null = null
  let currentContent: string[] = []

  const sectionMapping: Record<string, keyof ParsedAnalysis> = {
    'IMMEDIATE ACTIONS': 'immediateActions',
    'ROOT CAUSE ANALYSIS': 'rootCause',
    'IMPACT ASSESSMENT': 'impact',
    'REMEDIATION STEPS': 'remediation',
    'MONITORING': 'monitoring',
    'AUTOMATION OPPORTUNITIES': 'automation',
    'FOLLOW-UP ACTIONS': 'followUp',
  }

  for (const line of lines) {
    const trimmedLine = line.trim()
    
    // Check for section headers
    let foundSection = false
    for (const [pattern, sectionKey] of Object.entries(sectionMapping)) {
      if (trimmedLine.includes(pattern)) {
        // Save previous section
        if (currentSection && currentContent.length > 0) {
          sections[currentSection] = currentContent
        }
        currentSection = sectionKey
        currentContent = []
        foundSection = true
        break
      }
    }

    if (!foundSection && currentSection && trimmedLine) {
      // Skip numbered headers and emojis
      if (!trimmedLine.match(/^\d+\.\s*🎯|🔍|💥|🛠️|📊|🚀|📝/)) {
        currentContent.push(trimmedLine)
      }
    }
  }

  // Save last section
  if (currentSection && currentContent.length > 0) {
    sections[currentSection] = currentContent
  }

  return sections
}

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group">
      <Button
        size="sm"
        variant="ghost"
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={handleCopy}
      >
        {copied ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
      </Button>
      <SyntaxHighlighter
        language="bash"
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: '0.375rem',
          fontSize: '0.875rem',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

function AnalysisSection({ 
  title, 
  items, 
  icon: Icon, 
  color 
}: { 
  title: string
  items: string[]
  icon: any
  color: string 
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Icon className={cn("h-5 w-5", color)} />
        <h3 className="font-semibold">{title}</h3>
      </div>
      <div className="space-y-2">
        {items.map((item, index) => {
          // Check if item contains code (backticks)
          const codeMatch = item.match(/`([^`]+)`/)
          if (codeMatch) {
            const [beforeCode, code, afterCode] = item.split(/`[^`]+`/)
            return (
              <div key={index} className="space-y-2">
                {beforeCode && <p className="text-sm">{beforeCode}</p>}
                <CodeBlock code={codeMatch[1]} />
                {afterCode && <p className="text-sm">{afterCode}</p>}
              </div>
            )
          }

          // Check for multiline code blocks
          if (item.includes('```')) {
            const parts = item.split('```')
            return (
              <div key={index} className="space-y-2">
                {parts.map((part, i) => {
                  if (i % 2 === 1) {
                    // This is a code block
                    const [lang, ...codeLines] = part.trim().split('\n')
                    return <CodeBlock key={i} code={codeLines.join('\n')} />
                  }
                  return part.trim() && <p key={i} className="text-sm">{part.trim()}</p>
                })}
              </div>
            )
          }

          return (
            <Alert key={index} className="border-l-4">
              <AlertDescription className="text-sm">{item}</AlertDescription>
            </Alert>
          )
        })}
      </div>
    </div>
  )
}

export function AIAnalysisDisplay({ 
  analysis, 
  timestamp, 
  responseTime,
  className,
  parsedAnalysis: providedParsedAnalysis,
  confidenceScore,
  riskLevel
}: AIAnalysisDisplayProps) {
  // Use provided parsed analysis or parse it ourselves
  const parsedData = providedParsedAnalysis || parseAnalysis(analysis)
  
  // Map the parsed data to our expected format
  const parsedAnalysis: ParsedAnalysis = {
    immediateActions: parsedData.immediate_actions || parsedData.immediateActions || [],
    rootCause: parsedData.root_cause || parsedData.rootCause || [],
    impact: parsedData.impact || [],
    remediation: parsedData.remediation || [],
    monitoring: parsedData.monitoring || [],
    automation: parsedData.automation || [],
    followUp: parsedData.follow_up || parsedData.followUp || []
  }
  
  const hasAnalysis = Object.values(parsedAnalysis).some(arr => arr && arr.length > 0)

  if (!hasAnalysis) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            AI Analysis
          </CardTitle>
          <CardDescription>
            Waiting for AI analysis...
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              AI Analysis
            </CardTitle>
            <CardDescription>
              Claude's recommendations for this incident
            </CardDescription>
          </div>
          {responseTime && (
            <Badge variant="secondary">
              {responseTime} response time
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent>
        <Tabs defaultValue="immediate" className="w-full">
          <TabsList className="grid grid-cols-4 lg:grid-cols-7 w-full">
            {Object.entries(parsedAnalysis).map(([key, _]) => {
              const config = sectionIcons[key as keyof typeof sectionIcons]
              if (!config) return null
              return (
                <TabsTrigger key={key} value={key} className="text-xs">
                  <config.icon className="h-4 w-4" />
                </TabsTrigger>
              )
            })}
          </TabsList>
          
          {Object.entries(parsedAnalysis).map(([key, items]) => {
            const config = sectionIcons[key as keyof typeof sectionIcons]
            if (!config || !items) return null
            
            return (
              <TabsContent key={key} value={key} className="mt-6">
                <AnalysisSection
                  title={config.label}
                  items={items}
                  icon={config.icon}
                  color={config.color}
                />
              </TabsContent>
            )
          })}
        </Tabs>
      </CardContent>
    </Card>
  )
}