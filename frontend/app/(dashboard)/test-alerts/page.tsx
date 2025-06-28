'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';

export default function TestAlertsPage() {
  const [loading, setLoading] = useState(false);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [usage, setUsage] = useState<any>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const TEAM_ID = 'team_123';

  const fetchAlerts = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/alerts/?team_id=${TEAM_ID}`);
      const data = await response.json();
      setAlerts(data.alerts || []);
    } catch (error) {
      toast.error('Failed to fetch alerts');
    }
  };

  const fetchUsage = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/alert-tracking/usage/${TEAM_ID}`);
      const data = await response.json();
      setUsage(data);
    } catch (error) {
      toast.error('Failed to fetch usage');
    }
  };

  const createAlert = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/alerts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_id: TEAM_ID,
          incident_id: `test_${Date.now()}`,
          title: `Test Alert ${new Date().toLocaleTimeString()}`,
          description: 'Created via test page',
          severity: 'medium',
          alert_type: 'manual'
        })
      });

      if (response.ok) {
        toast.success('Alert created successfully');
        await fetchAlerts();
        await fetchUsage();
      } else if (response.status === 403) {
        const error = await response.json();
        toast.error(error.detail.message);
      }
    } catch (error) {
      toast.error('Failed to create alert');
    } finally {
      setLoading(false);
    }
  };

  const resetUsage = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/alerts/reset-usage/${TEAM_ID}`, {
        method: 'POST'
      });

      if (response.ok) {
        toast.success('Usage reset successfully');
        await fetchUsage();
      }
    } catch (error) {
      toast.error('Failed to reset usage');
    } finally {
      setLoading(false);
    }
  };

  const deleteAlert = async (alertId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/alerts/${alertId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        toast.success('Alert deleted');
        await fetchAlerts();
      }
    } catch (error) {
      toast.error('Failed to delete alert');
    }
  };

  // Fetch initial data
  useState(() => {
    fetchAlerts();
    fetchUsage();
  });

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Test Alert CRUD Operations</h1>

      {/* Usage Card */}
      <Card className="p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Current Usage</h2>
        {usage && (
          <div className="space-y-2">
            <p>Alerts Used: {usage.alerts_used} / {usage.alerts_limit === -1 ? 'Unlimited' : usage.alerts_limit}</p>
            <p>Account Tier: <span className="font-semibold capitalize">{usage.account_tier}</span></p>
            <p>Alerts Remaining: {usage.alerts_remaining === -1 ? 'Unlimited' : usage.alerts_remaining}</p>
            {usage.is_limit_reached && (
              <p className="text-red-600 font-semibold">⚠️ Alert limit reached!</p>
            )}
          </div>
        )}
      </Card>

      {/* Actions */}
      <Card className="p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Actions</h2>
        <div className="flex gap-4">
          <Button onClick={createAlert} disabled={loading}>
            Create Test Alert
          </Button>
          <Button onClick={resetUsage} disabled={loading} variant="outline">
            Reset Usage
          </Button>
          <Button onClick={() => { fetchAlerts(); fetchUsage(); }} variant="outline">
            Refresh
          </Button>
        </div>
      </Card>

      {/* Alerts List */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Alerts ({alerts.length})</h2>
        <div className="space-y-2">
          {alerts.map((alert) => (
            <div key={alert.id} className="flex justify-between items-center p-3 border rounded">
              <div>
                <p className="font-medium">{alert.title}</p>
                <p className="text-sm text-gray-600">
                  {alert.severity} | {alert.status} | {new Date(alert.created_at).toLocaleString()}
                </p>
              </div>
              <Button 
                size="sm" 
                variant="destructive"
                onClick={() => deleteAlert(alert.id)}
              >
                Delete
              </Button>
            </div>
          ))}
          {alerts.length === 0 && (
            <p className="text-gray-500">No alerts found. Create some test alerts!</p>
          )}
        </div>
      </Card>
    </div>
  );
}