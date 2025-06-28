'use client';

import { useState } from 'react';
import { useAPIKeys } from '@/lib/hooks/use-api-keys';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Key,
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  RefreshCw,
  Edit,
} from 'lucide-react';
import { toast } from 'sonner';

export function APIKeysSection() {
  const { keys, loading, error, refetch } = useAPIKeys();
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingKey, setEditingKey] = useState<any>(null);
  const [addingKey, setAddingKey] = useState(false);
  const [validatingKey, setValidatingKey] = useState<string | null>(null);
  const [deletingKey, setDeletingKey] = useState<string | null>(null);

  // Form state for adding new key
  const [newKeyProvider, setNewKeyProvider] = useState<'anthropic' | 'openai'>('anthropic');
  const [newKeyValue, setNewKeyValue] = useState('');
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyIsPrimary, setNewKeyIsPrimary] = useState(false);

  const handleAddKey = async () => {
    if (!newKeyValue.trim()) {
      toast.error('Please enter an API key');
      return;
    }

    setAddingKey(true);
    try {
      const response = await fetch('/api/v1/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: newKeyProvider,
          api_key: newKeyValue,
          name: newKeyName || `${newKeyProvider} API Key`,
          is_primary: newKeyIsPrimary || keys.length === 0,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to add API key');
      }

      toast.success('API key added successfully');
      setShowAddDialog(false);
      setNewKeyValue('');
      setNewKeyName('');
      setNewKeyIsPrimary(false);
      refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to add API key');
    } finally {
      setAddingKey(false);
    }
  };

  const handleEditKey = (key: any) => {
    setEditingKey(key);
    setNewKeyName(key.name);
    setNewKeyIsPrimary(key.is_primary);
    setShowEditDialog(true);
  };

  const handleUpdateKey = async () => {
    if (!editingKey) return;

    setAddingKey(true);
    try {
      const response = await fetch(`/api/v1/api-keys/${editingKey.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newKeyName,
          is_primary: newKeyIsPrimary,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to update API key');
      }

      toast.success('API key updated successfully');
      setShowEditDialog(false);
      setEditingKey(null);
      setNewKeyName('');
      setNewKeyIsPrimary(false);
      refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update API key');
    } finally {
      setAddingKey(false);
    }
  };

  const handleValidateKey = async (keyId: string) => {
    setValidatingKey(keyId);
    try {
      const response = await fetch(`/api/v1/api-keys/${keyId}/validate`, {
        method: 'POST',
      });

      const result = await response.json();
      if (result.valid) {
        toast.success('API key is valid');
      } else {
        toast.error(result.error || 'API key is invalid');
      }
    } catch (err) {
      toast.error('Failed to validate API key');
    } finally {
      setValidatingKey(null);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to delete this API key?')) {
      return;
    }

    setDeletingKey(keyId);
    try {
      const response = await fetch(`/api/v1/api-keys/${keyId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to delete API key');
      }

      toast.success('API key deleted successfully');
      refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete API key');
    } finally {
      setDeletingKey(null);
    }
  };

  const handleSetPrimary = async (keyId: string) => {
    try {
      const response = await fetch(`/api/v1/api-keys/${keyId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_primary: true }),
      });

      if (!response.ok) {
        throw new Error('Failed to update API key');
      }

      toast.success('Primary API key updated');
      refetch();
    } catch (err) {
      toast.error('Failed to update primary key');
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            <CardTitle>LLM API Keys</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              <CardTitle>LLM API Keys</CardTitle>
            </div>
            <CardDescription>
              Manage your API keys for AI providers. DreamOps will automatically fallback to
              secondary keys if the primary key fails.
            </CardDescription>
          </div>
          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Key
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add API Key</DialogTitle>
                <DialogDescription>
                  Add a new API key for AI analysis
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div className="space-y-3">
                  <Label>Provider</Label>
                  <RadioGroup
                    value={newKeyProvider}
                    onValueChange={(v) => setNewKeyProvider(v as any)}
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="anthropic" id="add-anthropic" />
                      <Label htmlFor="add-anthropic">Anthropic (Claude)</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="openai" id="add-openai" />
                      <Label htmlFor="add-openai">OpenAI (GPT-4)</Label>
                    </div>
                  </RadioGroup>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="add-key">API Key</Label>
                  <Input
                    id="add-key"
                    type="password"
                    placeholder={newKeyProvider === 'anthropic' ? 'sk-ant-...' : 'sk-...'}
                    value={newKeyValue}
                    onChange={(e) => setNewKeyValue(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="add-name">Name (optional)</Label>
                  <Input
                    id="add-name"
                    placeholder="e.g., Production Key"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="add-primary"
                    checked={newKeyIsPrimary}
                    onChange={(e) => setNewKeyIsPrimary(e.target.checked)}
                    disabled={keys.length === 0}
                  />
                  <Label htmlFor="add-primary">Set as primary key</Label>
                  {keys.length === 0 && (
                    <span className="text-xs text-muted-foreground">(First key is automatically primary)</span>
                  )}
                </div>

                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setShowAddDialog(false)}
                    disabled={addingKey}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleAddKey} disabled={addingKey || !newKeyValue.trim()}>
                    {addingKey ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Adding...
                      </>
                    ) : (
                      'Add Key'
                    )}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          {/* Edit Dialog */}
          <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Edit API Key</DialogTitle>
                <DialogDescription>
                  Update the settings for this API key
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label>Provider</Label>
                  <div className="p-2 bg-muted rounded text-sm">
                    {editingKey?.provider} (Cannot be changed)
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>API Key</Label>
                  <div className="p-2 bg-muted rounded text-sm font-mono">
                    {editingKey?.api_key_masked} (Cannot be changed)
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-name">Name</Label>
                  <Input
                    id="edit-name"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="edit-primary"
                    checked={newKeyIsPrimary}
                    onChange={(e) => setNewKeyIsPrimary(e.target.checked)}
                  />
                  <Label htmlFor="edit-primary">Set as primary key</Label>
                </div>

                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowEditDialog(false);
                      setEditingKey(null);
                      setNewKeyName('');
                      setNewKeyIsPrimary(false);
                    }}
                    disabled={addingKey}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleUpdateKey} disabled={addingKey}>
                    {addingKey ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Updating...
                      </>
                    ) : (
                      'Update Key'
                    )}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {keys.length === 0 ? (
          <div className="text-center py-8">
            <Key className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-4">No API keys configured</p>
            <Button onClick={() => setShowAddDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Your First Key
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {keys.map((key) => (
              <div
                key={key.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{key.name}</span>
                      {key.is_primary && (
                        <Badge variant="default" className="text-xs">
                          Primary
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                      <span>{key.provider}</span>
                      <span className="font-mono">{key.api_key_masked}</span>
                      <div className="flex items-center gap-1">
                        {key.status === 'active' ? (
                          <>
                            <CheckCircle className="h-3 w-3 text-green-500" />
                            <span className="text-green-600">Active</span>
                          </>
                        ) : key.status === 'exhausted' ? (
                          <>
                            <AlertCircle className="h-3 w-3 text-orange-500" />
                            <span className="text-orange-600">Rate Limited</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="h-3 w-3 text-red-500" />
                            <span className="text-red-600">Invalid</span>
                          </>
                        )}
                      </div>
                      {key.error_count > 0 && (
                        <span className="text-red-600">
                          {key.error_count} error{key.error_count > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {!key.is_primary && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleSetPrimary(key.id)}
                    >
                      Set Primary
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEditKey(key)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleValidateKey(key.id)}
                    disabled={validatingKey === key.id}
                  >
                    {validatingKey === key.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteKey(key.id)}
                    disabled={deletingKey === key.id || keys.length === 1}
                  >
                    {deletingKey === key.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 pt-4 border-t">
          <p className="text-sm text-muted-foreground">
            <strong>Auto-Fallback:</strong> When the primary key fails due to rate limits or
            errors, DreamOps will automatically switch to the next available key.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}