'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Activity, AlertCircle, CheckCircle, Clock, TrendingUp, Shield, Server } from 'lucide-react';

export default function DashboardPage() {
  // Mock data - will be replaced with API calls
  const metrics = {
    activeIncidents: 2,
    resolvedToday: 8,
    avgResponseTime: '3.2 min',
    healthScore: 95,
    ai_agent_status: 'online'
  };

  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Oncall AI Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Real-time incident monitoring and AI-powered resolution
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Badge 
            variant="outline" 
            className={`px-3 py-1 ${
              metrics?.ai_agent_status === 'online' 
                ? 'bg-green-50 text-green-700 border-green-300' 
                : 'bg-red-50 text-red-700 border-red-300'
            }`}
          >
            <span className={`mr-2 h-2 w-2 rounded-full ${
              metrics?.ai_agent_status === 'online' ? 'bg-green-600' : 'bg-red-600'
            }`}></span>
            AI Agent {metrics?.ai_agent_status === 'online' ? 'Online' : 'Offline'}
          </Badge>
        </div>
      </div>
      
      {/* Metrics Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Active Incidents
            </CardTitle>
            <AlertCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.activeIncidents}</div>
            <p className="text-xs text-gray-600">
              Requires immediate attention
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Resolved Today
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.resolvedToday}</div>
            <p className="text-xs text-gray-600">
              <TrendingUp className="inline h-3 w-3 mr-1" />
              +12% from yesterday
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Avg Response Time
            </CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.avgResponseTime}</div>
            <p className="text-xs text-gray-600">
              Target: &lt; 5 min
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              System Health
            </CardTitle>
            <Activity className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.healthScore}%</div>
            <Progress value={metrics.healthScore} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-red-500" />
                  <span className="text-sm">API Gateway High Error Rate</span>
                </div>
                <Badge variant="destructive" className="text-xs">Critical</Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-yellow-500" />
                  <span className="text-sm">Database Connection Pool</span>
                </div>
                <Badge variant="secondary" className="text-xs">Resolved</Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-blue-500" />
                  <span className="text-sm">High Memory Usage</span>
                </div>
                <Badge variant="outline" className="text-xs">Monitoring</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>AI Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-green-500" />
                  <span className="text-sm">Auto-scaled deployment</span>
                </div>
                <span className="text-xs text-gray-500">2 min ago</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-sm">Cleared Redis cache</span>
                </div>
                <span className="text-xs text-gray-500">5 min ago</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-blue-500" />
                  <span className="text-sm">Analyzed log patterns</span>
                </div>
                <span className="text-xs text-gray-500">8 min ago</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}