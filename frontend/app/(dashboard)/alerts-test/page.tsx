'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { Plus, Minus, RefreshCw, Trash2 } from 'lucide-react';

export default function AlertsTestPage() {
  const [loading, setLoading] = useState(false);
  const [usage, setUsage] = useState<any>(null);
  const [alertCount, setAlertCount] = useState(0);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const TEAM_ID = 'team_123';

  const fetchUsage = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/alert-tracking/usage/${TEAM_ID}`);
      const data = await response.json();
      setUsage(data);
      setAlertCount(data.alerts_used);
    } catch (error) {
      toast.error('Failed to fetch usage');
    }
  };

  // Create alert (+ button)
  const createAlert = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/alerts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_id: TEAM_ID,
          incident_id: `test_${Date.now()}`,
          title: `Alert #${alertCount + 1}`,
          description: 'Created via + button',
          severity: 'medium',
          alert_type: 'manual'
        })
      });

      if (response.ok) {
        toast.success(`Alert #${alertCount + 1} created!`);
        await fetchUsage();
      } else if (response.status === 403) {
        const error = await response.json();
        toast.error(error.detail.message || 'Alert limit reached! Upgrade required.');
      }
    } catch (error) {
      toast.error('Failed to create alert');
    } finally {
      setLoading(false);
    }
  };

  // Delete last alert (- button)
  const deleteLastAlert = async () => {
    setLoading(true);
    try {
      // First get list of alerts
      const listResponse = await fetch(`${API_URL}/api/v1/alerts/?team_id=${TEAM_ID}`);
      const data = await listResponse.json();
      
      if (data.alerts && data.alerts.length > 0) {
        // Delete the last alert
        const lastAlert = data.alerts[0]; // They're sorted newest first
        const deleteResponse = await fetch(`${API_URL}/api/v1/alerts/${lastAlert.id}`, {
          method: 'DELETE'
        });

        if (deleteResponse.ok) {
          toast.success('Last alert deleted!');
          // Note: This doesn't decrement usage count in current implementation
          await fetchUsage();
        }
      } else {
        toast.info('No alerts to delete');
      }
    } catch (error) {
      toast.error('Failed to delete alert');
    } finally {
      setLoading(false);
    }
  };

  // Reset usage
  const resetUsage = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/alerts/reset-usage/${TEAM_ID}`, {
        method: 'POST'
      });

      if (response.ok) {
        toast.success('Usage reset to 0!');
        await fetchUsage();
      }
    } catch (error) {
      toast.error('Failed to reset usage');
    } finally {
      setLoading(false);
    }
  };

  // Delete all alerts
  const deleteAllAlerts = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/alerts/?team_id=${TEAM_ID}&confirm=true`, {
        method: 'DELETE'
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(`Deleted ${data.count} alerts`);
        await fetchUsage();
      }
    } catch (error) {
      toast.error('Failed to delete all alerts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsage();
  }, []);

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <h1 className="text-3xl font-bold mb-6 text-center">Alert Testing</h1>

      {/* Main Counter Card */}
      <Card className="p-8 mb-6">
        <div className="text-center">
          <h2 className="text-6xl font-bold mb-4">
            {usage?.alerts_used || 0} / {usage?.alerts_limit === -1 ? '∞' : (usage?.alerts_limit || 3)}
          </h2>
          <p className="text-xl text-gray-600 mb-2">Alerts Used</p>
          <p className="text-lg">
            Account Tier: <span className="font-semibold capitalize text-blue-600">
              {usage?.account_tier || 'free'}
            </span>
          </p>
          {usage?.is_limit_reached && (
            <p className="text-red-600 font-semibold mt-4 text-xl animate-pulse">
              ⚠️ Alert limit reached! Upgrade required.
            </p>
          )}
        </div>

        {/* Big + and - buttons */}
        <div className="flex justify-center gap-8 mt-8">
          <Button
            size="lg"
            onClick={deleteLastAlert}
            disabled={loading || alertCount === 0}
            variant="outline"
            className="w-24 h-24 text-3xl"
          >
            <Minus className="w-12 h-12" />
          </Button>

          <Button
            size="lg"
            onClick={createAlert}
            disabled={loading}
            className="w-24 h-24 text-3xl bg-green-600 hover:bg-green-700"
          >
            <Plus className="w-12 h-12" />
          </Button>
        </div>

        <div className="text-center mt-4 text-sm text-gray-500">
          Press + to create alert, - to delete last alert
        </div>
      </Card>

      {/* Action Buttons */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4">Quick Actions</h3>
        <div className="grid grid-cols-2 gap-4">
          <Button onClick={fetchUsage} variant="outline" disabled={loading}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={resetUsage} variant="outline" disabled={loading}>
            Reset to 0
          </Button>
          <Button onClick={deleteAllAlerts} variant="destructive" disabled={loading}>
            <Trash2 className="w-4 h-4 mr-2" />
            Delete All
          </Button>
          <Button 
            onClick={() => window.location.href = '/dashboard'}
            variant="outline"
          >
            Go to Dashboard
          </Button>
        </div>
      </Card>

      {/* Usage Info */}
      {usage && (
        <Card className="p-4 mt-4 bg-gray-50">
          <p className="text-sm text-gray-600">
            Alerts Remaining: {usage.alerts_remaining === -1 ? 'Unlimited' : usage.alerts_remaining}
          </p>
          <p className="text-sm text-gray-600">
            Limit Reached: {usage.is_limit_reached ? 'Yes' : 'No'}
          </p>
        </Card>
      )}
    </div>
  );
}