'use client';

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Save, Key, Bell, Brain, Shield } from 'lucide-react';

export default function SettingsPage() {
  return (
    <section className="flex-1 p-4 lg:p-8">
      <div className="mb-6">
        <h1 className="text-lg lg:text-2xl font-medium mb-2">Agent Settings</h1>
        <p className="text-muted-foreground">
          Configure your AI agent and incident response preferences
        </p>
      </div>

      <div className="space-y-6">
        {/* AI Configuration */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              <CardTitle>AI Configuration</CardTitle>
            </div>
            <CardDescription>
              Configure Claude AI settings for incident analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="model">Claude Model</Label>
              <Select defaultValue="claude-3-5-sonnet">
                <SelectTrigger id="model" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="claude-3-5-sonnet">Claude 3.5 Sonnet</SelectItem>
                  <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                  <SelectItem value="claude-3-haiku">Claude 3 Haiku</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="context">Additional Context</Label>
              <Textarea
                id="context"
                placeholder="Add any specific context or instructions for the AI agent..."
                className="mt-2 min-h-[100px]"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="auto-analyze">Auto-analyze incidents</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically analyze new incidents as they arrive
                </p>
              </div>
              <Switch id="auto-analyze" defaultChecked />
            </div>
          </CardContent>
        </Card>

        {/* Alert Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              <CardTitle>Alert Settings</CardTitle>
            </div>
            <CardDescription>
              Configure how alerts are processed and prioritized
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="priority">Priority Threshold</Label>
              <Select defaultValue="high">
                <SelectTrigger id="priority" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical Only</SelectItem>
                  <SelectItem value="high">High and Above</SelectItem>
                  <SelectItem value="medium">Medium and Above</SelectItem>
                  <SelectItem value="all">All Alerts</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="auto-ack">Auto-acknowledge</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically acknowledge alerts when AI starts analysis
                </p>
              </div>
              <Switch id="auto-ack" />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="dedup">De-duplication</Label>
                <p className="text-sm text-muted-foreground">
                  Group similar alerts together
                </p>
              </div>
              <Switch id="dedup" defaultChecked />
            </div>
          </CardContent>
        </Card>

        {/* API Keys */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              <CardTitle>API Keys</CardTitle>
            </div>
            <CardDescription>
              Manage your API keys and authentication
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="anthropic-key">Anthropic API Key</Label>
              <div className="flex gap-2 mt-2">
                <Input
                  id="anthropic-key"
                  type="password"
                  placeholder="sk-ant-api03-..."
                  defaultValue="sk-ant-api03-•••••••••••••••"
                />
                <Button variant="outline">Update</Button>
              </div>
            </div>

            <div>
              <Label htmlFor="webhook-url">Webhook URL</Label>
              <div className="flex gap-2 mt-2">
                <Input
                  id="webhook-url"
                  placeholder="https://your-domain.com/api/alerts"
                  readOnly
                  defaultValue="https://oncall-agent.com/api/alerts"
                />
                <Button variant="outline">Copy</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Security */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              <CardTitle>Security</CardTitle>
            </div>
            <CardDescription>
              Security and compliance settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="audit-logs">Audit Logs</Label>
                <p className="text-sm text-muted-foreground">
                  Keep detailed logs of all agent actions
                </p>
              </div>
              <Switch id="audit-logs" defaultChecked />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="data-retention">Data Retention</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically delete old incident data after 90 days
                </p>
              </div>
              <Switch id="data-retention" defaultChecked />
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button className="min-w-[200px]">
            <Save className="h-4 w-4 mr-2" />
            Save Settings
          </Button>
        </div>
      </div>
    </section>
  );
}