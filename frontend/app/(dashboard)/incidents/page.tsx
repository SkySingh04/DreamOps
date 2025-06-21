'use client';

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Search, Filter, ExternalLink } from 'lucide-react';

export default function IncidentsPage() {
  // Mock incident data
  const incidents = [
    {
      id: 'INC-001',
      title: 'API Gateway High Error Rate',
      service: 'api-gateway',
      severity: 'critical',
      status: 'active',
      createdAt: '2024-06-21T10:30:00Z',
      assignee: 'John Doe',
      aiAnalysis: 'Claude identified potential database connection issues'
    },
    {
      id: 'INC-002',
      title: 'Database Connection Pool Exhausted',
      service: 'user-service',
      severity: 'high',
      status: 'resolved',
      createdAt: '2024-06-21T08:15:00Z',
      resolvedAt: '2024-06-21T09:45:00Z',
      assignee: 'Jane Smith',
      aiAnalysis: 'Claude recommended connection pool size increase'
    },
    {
      id: 'INC-003',
      title: 'High Memory Usage Warning',
      service: 'order-service',
      severity: 'medium',
      status: 'monitoring',
      createdAt: '2024-06-21T07:00:00Z',
      assignee: 'Mike Johnson',
      aiAnalysis: 'Claude detected memory leak pattern in recent deployment'
    }
  ];

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-red-100 text-red-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'monitoring':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <section className="flex-1 p-4 lg:p-8">
      <div className="mb-6">
        <h1 className="text-lg lg:text-2xl font-medium mb-4">Incident History</h1>
        
        {/* Search and Filter Bar */}
        <div className="flex gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search incidents..."
              className="pl-10"
            />
          </div>
          <Button variant="outline">
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </Button>
        </div>

        {/* Incidents Table */}
        <Card>
          <CardHeader>
            <CardTitle>All Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">ID</th>
                    <th className="text-left py-3 px-4">Title</th>
                    <th className="text-left py-3 px-4">Service</th>
                    <th className="text-left py-3 px-4">Severity</th>
                    <th className="text-left py-3 px-4">Status</th>
                    <th className="text-left py-3 px-4">Assignee</th>
                    <th className="text-left py-3 px-4">Created</th>
                    <th className="text-left py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((incident) => (
                    <tr key={incident.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 font-mono text-sm">{incident.id}</td>
                      <td className="py-3 px-4">
                        <div>
                          <p className="font-medium">{incident.title}</p>
                          <p className="text-xs text-muted-foreground mt-1">
                            AI: {incident.aiAnalysis}
                          </p>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="secondary">{incident.service}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge className={getSeverityColor(incident.severity)}>
                          {incident.severity}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge className={getStatusColor(incident.status)}>
                          {incident.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{incident.assignee}</td>
                      <td className="py-3 px-4 text-sm">
                        {new Date(incident.createdAt).toLocaleString()}
                      </td>
                      <td className="py-3 px-4">
                        <Button variant="ghost" size="sm">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}