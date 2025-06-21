'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  AreaChart,
  Area,
  PieChart, 
  Pie, 
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';
import { 
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  CheckCircle,
  AlertCircle,
  Download,
  Calendar,
  Users,
  Zap,
  Target,
  Award
} from 'lucide-react';
import { apiClient, queryKeys } from '@/lib/api-client';
import { AnalyticsData } from '@/lib/types';
import { format, subDays, startOfMonth, endOfMonth } from 'date-fns';
import { toast } from 'sonner';

const SEVERITY_COLORS = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#f59e0b',
  low: '#3b82f6',
};

const TIME_RANGES = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: 'mtd', label: 'Month to date' },
  { value: 'ytd', label: 'Year to date' },
];

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState('30d');
  const [exportFormat, setExportFormat] = useState<'csv' | 'pdf'>('csv');

  // Calculate date range
  const getDateRange = () => {
    const now = new Date();
    let startDate: Date;
    
    switch (timeRange) {
      case '7d':
        startDate = subDays(now, 7);
        break;
      case '30d':
        startDate = subDays(now, 30);
        break;
      case '90d':
        startDate = subDays(now, 90);
        break;
      case 'mtd':
        startDate = startOfMonth(now);
        break;
      case 'ytd':
        startDate = new Date(now.getFullYear(), 0, 1);
        break;
      default:
        startDate = subDays(now, 30);
    }
    
    return {
      start_date: format(startDate, 'yyyy-MM-dd'),
      end_date: format(now, 'yyyy-MM-dd'),
    };
  };

  // Fetch analytics data
  const { data: analyticsData, isLoading } = useQuery({
    queryKey: queryKeys.analytics(getDateRange()),
    queryFn: () => apiClient.getAnalytics(getDateRange()),
  });

  const analytics = analyticsData?.data || {
    incidents_over_time: [],
    resolution_time_trend: [],
    success_rate_trend: [],
    incident_by_service: [],
    cost_savings: {
      total_saved: 0,
      breakdown: [],
    },
    severity_distribution: [],
    hourly_trend: [],
  };

  // Calculate summary metrics
  const summaryMetrics = {
    totalIncidents: analytics.incidents_over_time.reduce(
      (sum, day) => sum + day.critical + day.high + day.medium + day.low, 
      0
    ),
    avgResolutionTime: analytics.resolution_time_trend.length > 0
      ? Math.round(
          analytics.resolution_time_trend.reduce((sum, item) => sum + item.avg_minutes, 0) / 
          analytics.resolution_time_trend.length
        )
      : 0,
    avgSuccessRate: analytics.success_rate_trend.length > 0
      ? Math.round(
          analytics.success_rate_trend.reduce((sum, item) => sum + item.rate, 0) / 
          analytics.success_rate_trend.length
        )
      : 0,
    totalSaved: analytics.cost_savings.total_saved,
  };

  // Export functionality
  const handleExport = async () => {
    try {
      const blob = await apiClient.exportReport(exportFormat, getDateRange());
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `oncall-analytics-${format(new Date(), 'yyyy-MM-dd')}.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success(`Report exported as ${exportFormat.toUpperCase()}`);
    } catch (error) {
      toast.error('Failed to export report');
    }
  };

  // Mock data for additional charts
  const aiPerformanceData = [
    { metric: 'Accuracy', value: 92 },
    { metric: 'Speed', value: 88 },
    { metric: 'Coverage', value: 85 },
    { metric: 'Automation', value: 78 },
    { metric: 'Learning', value: 95 },
  ];

  const integrationUsageData = [
    { name: 'Kubernetes', calls: 4523, success: 98 },
    { name: 'GitHub', calls: 2341, success: 99 },
    { name: 'PagerDuty', calls: 1876, success: 100 },
    { name: 'Grafana', calls: 3211, success: 97 },
    { name: 'Datadog', calls: 987, success: 95 },
  ];

  if (isLoading) {
    return (
      <div className="flex-1 p-4 lg:p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analytics & Reporting</h1>
          <p className="text-muted-foreground mt-1">
            Track performance metrics and AI agent effectiveness
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[180px]">
              <Calendar className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIME_RANGES.map((range) => (
                <SelectItem key={range.value} value={range.value}>
                  {range.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Incidents</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summaryMetrics.totalIncidents}</div>
            <p className="text-xs text-muted-foreground mt-1">
              <TrendingDown className="h-3 w-3 text-green-600 inline mr-1" />
              12% less than previous period
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Resolution Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summaryMetrics.avgResolutionTime}m</div>
            <p className="text-xs text-muted-foreground mt-1">
              <TrendingDown className="h-3 w-3 text-green-600 inline mr-1" />
              23% faster than baseline
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summaryMetrics.avgSuccessRate}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              <TrendingUp className="h-3 w-3 text-green-600 inline mr-1" />
              5% improvement
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cost Saved</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${summaryMetrics.totalSaved.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              By AI automation
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Charts */}
      <Tabs defaultValue="incidents" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="incidents">Incidents</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="ai-metrics">AI Metrics</TabsTrigger>
          <TabsTrigger value="cost-analysis">Cost Analysis</TabsTrigger>
        </TabsList>

        <TabsContent value="incidents" className="space-y-6">
          {/* Incidents Over Time */}
          <Card>
            <CardHeader>
              <CardTitle>Incidents Over Time</CardTitle>
              <CardDescription>
                Daily breakdown by severity level
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={analytics.incidents_over_time}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="critical"
                    stackId="1"
                    stroke={SEVERITY_COLORS.critical}
                    fill={SEVERITY_COLORS.critical}
                  />
                  <Area
                    type="monotone"
                    dataKey="high"
                    stackId="1"
                    stroke={SEVERITY_COLORS.high}
                    fill={SEVERITY_COLORS.high}
                  />
                  <Area
                    type="monotone"
                    dataKey="medium"
                    stackId="1"
                    stroke={SEVERITY_COLORS.medium}
                    fill={SEVERITY_COLORS.medium}
                  />
                  <Area
                    type="monotone"
                    dataKey="low"
                    stackId="1"
                    stroke={SEVERITY_COLORS.low}
                    fill={SEVERITY_COLORS.low}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Incidents by Service */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Incidents by Service</CardTitle>
                <CardDescription>
                  Top services with most incidents
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={analytics.incident_by_service.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="service" angle={-45} textAnchor="end" height={80} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Incident Distribution</CardTitle>
                <CardDescription>
                  Breakdown by incident type
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Infrastructure', value: 35, color: '#3b82f6' },
                        { name: 'Application', value: 30, color: '#8b5cf6' },
                        { name: 'Database', value: 20, color: '#ec4899' },
                        { name: 'Network', value: 10, color: '#10b981' },
                        { name: 'Security', value: 5, color: '#f59e0b' },
                      ]}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {[
                        { color: '#3b82f6' },
                        { color: '#8b5cf6' },
                        { color: '#ec4899' },
                        { color: '#10b981' },
                        { color: '#f59e0b' },
                      ].map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="performance" className="space-y-6">
          {/* Resolution Time Trend */}
          <Card>
            <CardHeader>
              <CardTitle>Resolution Time Trend</CardTitle>
              <CardDescription>
                Average time to resolve incidents (minutes)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={analytics.resolution_time_trend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="avg_minutes"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Success Rate Trend */}
          <Card>
            <CardHeader>
              <CardTitle>AI Resolution Success Rate</CardTitle>
              <CardDescription>
                Percentage of incidents successfully resolved by AI
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={analytics.success_rate_trend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="rate"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={{ fill: '#10b981' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai-metrics" className="space-y-6">
          {/* AI Performance Radar */}
          <Card>
            <CardHeader>
              <CardTitle>AI Agent Performance</CardTitle>
              <CardDescription>
                Multi-dimensional performance metrics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={aiPerformanceData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} />
                  <Radar
                    name="Performance"
                    dataKey="value"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.6}
                  />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Integration Usage */}
          <Card>
            <CardHeader>
              <CardTitle>Integration Usage</CardTitle>
              <CardDescription>
                API calls and success rates by integration
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {integrationUsageData.map((integration) => (
                  <div key={integration.name} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{integration.name}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-muted-foreground">
                          {integration.calls.toLocaleString()} calls
                        </span>
                        <Badge variant={integration.success >= 98 ? 'default' : 'secondary'}>
                          {integration.success}% success
                        </Badge>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${integration.success}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* AI Actions Summary */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Total AI Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">12,847</div>
                <p className="text-xs text-muted-foreground mt-1">
                  This period
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Approval Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">94.2%</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Human approved actions
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Rollback Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">0.8%</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Actions rolled back
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="cost-analysis" className="space-y-6">
          {/* Cost Savings Trend */}
          <Card>
            <CardHeader>
              <CardTitle>Cost Savings Over Time</CardTitle>
              <CardDescription>
                Monthly savings from AI automation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={analytics.cost_savings.breakdown}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
                  <Bar dataKey="amount" fill="#10b981" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Cost Breakdown */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Cost Savings Breakdown</CardTitle>
                <CardDescription>
                  By category
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-blue-600" />
                      <span>Time Saved</span>
                    </div>
                    <span className="font-bold">$45,230</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Zap className="h-4 w-4 text-yellow-600" />
                      <span>Faster Resolution</span>
                    </div>
                    <span className="font-bold">$32,180</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-green-600" />
                      <span>Reduced Escalations</span>
                    </div>
                    <span className="font-bold">$18,420</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Target className="h-4 w-4 text-purple-600" />
                      <span>Prevented Outages</span>
                    </div>
                    <span className="font-bold">$78,900</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>ROI Calculator</CardTitle>
                <CardDescription>
                  Return on investment metrics
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Total Investment</span>
                      <span className="text-sm">$50,000</span>
                    </div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Total Savings</span>
                      <span className="text-sm font-bold text-green-600">
                        ${summaryMetrics.totalSaved.toLocaleString()}
                      </span>
                    </div>
                    <Separator className="my-3" />
                    <div className="flex items-center justify-between">
                      <span className="font-medium">ROI</span>
                      <span className="text-2xl font-bold text-green-600">
                        {Math.round((summaryMetrics.totalSaved / 50000) * 100)}%
                      </span>
                    </div>
                  </div>
                  <div className="pt-4">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Award className="h-4 w-4" />
                      <span>Payback period: 2.3 months</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </section>
  );
}