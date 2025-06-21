'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { 
  Terminal as TerminalIcon,
  Activity,
  Bot,
  Play,
  Pause,
  RefreshCw,
  Maximize2,
  Minimize2,
  Copy,
  Download,
  Filter,
  AlertCircle,
  CheckCircle,
  Info,
  Loader2,
  Zap,
  Clock,
  Server,
  Database,
  Globe,
  Cpu,
  HardDrive,
  Wifi,
  BarChart3
} from 'lucide-react';
import { useWebSocket } from '@/lib/hooks/use-websocket';
import { format } from 'date-fns';
import { toast } from 'sonner';

import Terminal from '@/components/ui/terminal';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  source: string;
  message: string;
  metadata?: Record<string, any>;
}

interface AIAnalysis {
  id: string;
  timestamp: string;
  incident_id?: string;
  analysis_type: string;
  confidence: number;
  summary: string;
  recommendations: string[];
  context?: Record<string, any>;
}

interface SystemMetric {
  name: string;
  value: number;
  unit: string;
  status: 'healthy' | 'warning' | 'critical';
  trend?: 'up' | 'down' | 'stable';
}

const LOG_LEVELS = {
  info: { color: 'text-blue-600', bgColor: 'bg-blue-50', icon: Info },
  warning: { color: 'text-yellow-600', bgColor: 'bg-yellow-50', icon: AlertCircle },
  error: { color: 'text-red-600', bgColor: 'bg-red-50', icon: AlertCircle },
  debug: { color: 'text-gray-600', bgColor: 'bg-gray-50', icon: Info },
};

export default function MonitoringPage() {
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedLogLevel, setSelectedLogLevel] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [aiAnalyses, setAiAnalyses] = useState<AIAnalysis[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<any>(null);

  // Mock system metrics
  const [systemMetrics, setSystemMetrics] = useState<SystemMetric[]>([
    { name: 'CPU Usage', value: 45, unit: '%', status: 'healthy', trend: 'stable' },
    { name: 'Memory', value: 72, unit: '%', status: 'warning', trend: 'up' },
    { name: 'Disk I/O', value: 120, unit: 'MB/s', status: 'healthy', trend: 'down' },
    { name: 'Network', value: 850, unit: 'Mbps', status: 'healthy', trend: 'stable' },
    { name: 'API Latency', value: 42, unit: 'ms', status: 'healthy', trend: 'down' },
    { name: 'Error Rate', value: 0.2, unit: '%', status: 'healthy', trend: 'stable' },
  ]);

  // WebSocket for real-time updates - DISABLED
  // const { isConnected } = useWebSocket({
  //   onMessage: (message) => {
  //     // Handle metric updates from WebSocket
  //     if (message.type === 'metric_update') {
  //       // Update metrics based on incoming data
  //       const metricData = message.data;
  //       if (metricData && metricData.name && metricData.value !== undefined) {
  //         setSystemMetrics(prev => prev.map(m => 
  //           m.name === metricData.name 
  //             ? { ...m, value: metricData.value, trend: metricData.trend || m.trend }
  //             : m
  //         ));
  //       }
  //     }
  //   },
  // });
  const isConnected = false; // Hardcoded to false for now

  // Auto-scroll logs
  useEffect(() => {
    if (isLiveMode && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isLiveMode]);

  // Generate mock logs for demo
  useEffect(() => {
    if (!isLiveMode) return;

    const sources = ['api-gateway', 'user-service', 'order-service', 'payment-service', 'k8s-controller'];
    const messages = [
      'Request processed successfully',
      'Database query executed',
      'Cache hit for key: user_123',
      'Scaling deployment to 3 replicas',
      'Health check passed',
      'Metrics collected and sent',
      'Connection pool status: healthy',
      'Rate limit: 450/500 requests',
    ];

    const interval = setInterval(() => {
      const newLog: LogEntry = {
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        level: Math.random() > 0.8 ? 'warning' : Math.random() > 0.95 ? 'error' : 'info',
        source: sources[Math.floor(Math.random() * sources.length)],
        message: messages[Math.floor(Math.random() * messages.length)],
      };
      setLogs(prev => [...prev.slice(-99), newLog]);
    }, 2000);

    return () => clearInterval(interval);
  }, [isLiveMode]);

  // Generate mock AI analyses
  useEffect(() => {
    if (!isLiveMode) return;

    const analysisTypes = [
      'Anomaly Detection',
      'Root Cause Analysis',
      'Performance Analysis',
      'Capacity Planning',
      'Security Scan',
    ];

    const interval = setInterval(() => {
      const newAnalysis: AIAnalysis = {
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        analysis_type: analysisTypes[Math.floor(Math.random() * analysisTypes.length)],
        confidence: Math.random() * 0.3 + 0.7, // 0.7-1.0
        summary: 'Detected unusual pattern in service communication',
        recommendations: [
          'Monitor service latency over next 30 minutes',
          'Consider scaling if pattern persists',
          'Check for recent deployments',
        ],
      };
      setAiAnalyses(prev => [...prev.slice(-19), newAnalysis]);
    }, 10000);

    return () => clearInterval(interval);
  }, [isLiveMode]);

  const filteredLogs = logs.filter(log => {
    if (selectedLogLevel !== 'all' && log.level !== selectedLogLevel) return false;
    if (searchQuery && !log.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const handleExecuteCommand = (command: string) => {
    // In production, this would send the command to the backend
    toast.info(`Executing: ${command}`);
    
    // Mock response
    setTimeout(() => {
      if (terminalRef.current) {
        terminalRef.current.writeln(`\n$ ${command}`);
        terminalRef.current.writeln('Command executed successfully');
      }
    }, 500);
  };

  const exportLogs = () => {
    const content = filteredLogs.map(log => 
      `[${log.timestamp}] [${log.level.toUpperCase()}] [${log.source}] ${log.message}`
    ).join('\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs-${format(new Date(), 'yyyy-MM-dd-HHmmss')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('Logs exported');
  };

  const getMetricIcon = (metric: SystemMetric) => {
    switch (metric.name) {
      case 'CPU Usage':
        return <Cpu className="h-4 w-4" />;
      case 'Memory':
        return <HardDrive className="h-4 w-4" />;
      case 'Network':
        return <Wifi className="h-4 w-4" />;
      case 'API Latency':
        return <Clock className="h-4 w-4" />;
      case 'Error Rate':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  return (
    <section className={`flex-1 ${isFullscreen ? 'fixed inset-0 z-50 bg-white' : 'p-4 lg:p-8'}`}>
      <div className="space-y-6 h-full flex flex-col">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Live Monitoring</h1>
            <p className="text-muted-foreground mt-1">
              Real-time system logs, metrics, and AI analysis
            </p>
          </div>
          <div className="flex items-center gap-4">
            <Badge variant={isConnected ? 'default' : 'destructive'}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsLiveMode(!isLiveMode)}
            >
              {isLiveMode ? (
                <>
                  <Pause className="h-4 w-4 mr-2" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Resume
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsFullscreen(!isFullscreen)}
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* System Metrics Overview */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
          {systemMetrics.map((metric) => (
            <Card key={metric.name} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getMetricIcon(metric)}
                  <span className="text-sm font-medium">{metric.name}</span>
                </div>
                <Badge
                  variant={
                    metric.status === 'healthy' ? 'default' :
                    metric.status === 'warning' ? 'secondary' :
                    'destructive'
                  }
                  className="h-2 w-2 p-0"
                />
              </div>
              <div className="mt-2">
                <span className="text-2xl font-bold">{metric.value}</span>
                <span className="text-sm text-muted-foreground ml-1">{metric.unit}</span>
                {metric.trend && (
                  <span className={`text-xs ml-2 ${
                    metric.trend === 'up' ? 'text-red-600' :
                    metric.trend === 'down' ? 'text-green-600' :
                    'text-gray-600'
                  }`}>
                    {metric.trend === 'up' ? '↑' : metric.trend === 'down' ? '↓' : '→'}
                  </span>
                )}
              </div>
              <Progress 
                value={metric.unit === '%' ? metric.value : (metric.value / 1000) * 100} 
                className="mt-2 h-1"
              />
            </Card>
          ))}
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="logs" className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="logs">Live Logs</TabsTrigger>
            <TabsTrigger value="ai-analysis">AI Analysis</TabsTrigger>
            <TabsTrigger value="terminal">Terminal</TabsTrigger>
            <TabsTrigger value="grafana">Metrics Dashboard</TabsTrigger>
          </TabsList>

          <TabsContent value="logs" className="flex-1 flex flex-col">
            <Card className="flex-1 flex flex-col">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle>Real-time Logs</CardTitle>
                  <div className="flex items-center gap-2">
                    <Input
                      placeholder="Search logs..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-64"
                    />
                    <select
                      value={selectedLogLevel}
                      onChange={(e) => setSelectedLogLevel(e.target.value)}
                      className="px-3 py-1 border rounded-md"
                    >
                      <option value="all">All Levels</option>
                      <option value="info">Info</option>
                      <option value="warning">Warning</option>
                      <option value="error">Error</option>
                      <option value="debug">Debug</option>
                    </select>
                    <Button variant="outline" size="sm" onClick={exportLogs}>
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 overflow-hidden">
                <div className="h-full overflow-y-auto font-mono text-sm space-y-1">
                  {filteredLogs.map((log) => {
                    const logConfig = LOG_LEVELS[log.level];
                    const Icon = logConfig.icon;
                    
                    return (
                      <div
                        key={log.id}
                        className={`flex items-start gap-2 p-2 rounded hover:bg-gray-50`}
                      >
                        <span className="text-xs text-gray-500 whitespace-nowrap">
                          {format(new Date(log.timestamp), 'HH:mm:ss.SSS')}
                        </span>
                        <div className={`p-1 rounded ${logConfig.bgColor}`}>
                          <Icon className={`h-3 w-3 ${logConfig.color}`} />
                        </div>
                        <span className={`font-medium ${logConfig.color}`}>
                          [{log.source}]
                        </span>
                        <span className="flex-1">{log.message}</span>
                      </div>
                    );
                  })}
                  <div ref={logsEndRef} />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="ai-analysis" className="flex-1">
            <Card className="h-full">
              <CardHeader>
                <CardTitle>AI Agent Analysis Stream</CardTitle>
                <CardDescription>
                  Real-time insights and recommendations from the AI agent
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-[600px] overflow-y-auto">
                  {aiAnalyses.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Bot className="h-12 w-12 mx-auto mb-4" />
                      <p>Waiting for AI analysis...</p>
                    </div>
                  ) : (
                    aiAnalyses.map((analysis) => (
                      <Card key={analysis.id} className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-100 rounded-lg">
                              <Bot className="h-5 w-5 text-blue-600" />
                            </div>
                            <div>
                              <h4 className="font-semibold">{analysis.analysis_type}</h4>
                              <p className="text-xs text-muted-foreground">
                                {format(new Date(analysis.timestamp), 'PPpp')}
                              </p>
                            </div>
                          </div>
                          <Badge variant="outline">
                            {Math.round(analysis.confidence * 100)}% confidence
                          </Badge>
                        </div>
                        
                        <p className="text-sm mb-3">{analysis.summary}</p>
                        
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-muted-foreground">
                            Recommendations:
                          </p>
                          {analysis.recommendations.map((rec, idx) => (
                            <div key={idx} className="flex items-start gap-2 text-sm">
                              <Zap className="h-3 w-3 text-yellow-600 mt-0.5" />
                              <span>{rec}</span>
                            </div>
                          ))}
                        </div>
                      </Card>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="terminal" className="flex-1">
            <Card className="h-full flex flex-col">
              <CardHeader>
                <CardTitle>Kubernetes Terminal</CardTitle>
                <CardDescription>
                  Execute kubectl commands directly from the dashboard
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <Alert className="mb-4">
                  <TerminalIcon className="h-4 w-4" />
                  <AlertDescription>
                    Connected to cluster: oncall-agent-eks (ap-south-1)
                  </AlertDescription>
                </Alert>
                <div className="h-[500px] bg-gray-900 rounded-lg p-4">
                  <Terminal ref={terminalRef} onCommand={handleExecuteCommand} />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="grafana" className="flex-1">
            <Card className="h-full">
              <CardHeader>
                <CardTitle>Metrics Dashboard</CardTitle>
                <CardDescription>
                  Embedded Grafana dashboards
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <div className="h-[600px] bg-gray-100 rounded-lg flex items-center justify-center">
                  <div className="text-center">
                    <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-muted-foreground">
                      Grafana dashboard would be embedded here
                    </p>
                    <Button variant="outline" className="mt-4">
                      Open in Grafana
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </section>
  );
}