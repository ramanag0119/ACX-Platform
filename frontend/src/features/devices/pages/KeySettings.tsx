import { useState, useEffect } from "react";
import { AlertTriangle, Save, RotateCcw, ShieldCheck, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DataState } from "@/core/components/DataState";
import { useKeySettings, useUsers } from "@/lib/api/hooks";
import { useUpdateKeySettings, useResetKeySettings } from "@/lib/api/mutations";
import { MAX_PAGE_SIZE } from "@/lib/api/types";
import { useAuth } from "@/core/contexts/AuthContext";
import { PageHeader } from "@/components/layout/PageHeader";

/**
 * Default Key Settings.
 *
 * Configures the designated staff manager in `facility.default_key_user`,
 * and manages default master access keys in `access_key` (key_type=4).
 * Fully database-driven with PostgreSQL persistence and RBAC permissions.
 */
const KeySettings = () => {
  const { canWrite } = useAuth();
  const mayWrite = canWrite("default_key");

  const keySettingsQuery = useKeySettings();
  const usersQuery = useUsers({ page: 1, page_size: MAX_PAGE_SIZE, is_staff: 1 });

  const updateKeySettings = useUpdateKeySettings();
  const resetKeySettings = useResetKeySettings();

  const staff = usersQuery.data?.items ?? [];
  const currentKeyUserId = keySettingsQuery.data?.default_key_user ?? undefined;

  const [selectedManagerId, setSelectedManagerId] = useState<string | undefined>(undefined);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);

  useEffect(() => {
    if (currentKeyUserId) {
      setSelectedManagerId(currentKeyUserId);
    }
  }, [currentKeyUserId]);

  const hasChanges = selectedManagerId !== (currentKeyUserId ?? undefined);

  const handleSave = () => {
    if (!mayWrite) return;
    updateKeySettings.mutate({
      default_key_user: selectedManagerId || null,
    });
  };

  const handleResetConfirm = () => {
    if (!mayWrite) return;
    resetKeySettings.mutate(undefined, {
      onSuccess: () => {
        setSelectedManagerId(undefined);
        setResetDialogOpen(false);
      },
    });
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      <PageHeader
        title="Default Key Settings"
        description="Configure default key management, designated master key holder, and security access"
      />

      {/* Active Keys Status Badge Card */}
      <Card className="border border-border/80 shadow-sm bg-card text-card-foreground">
        <CardContent className="p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">
                Active Default Master Keys
              </div>
              <div className="text-xs text-muted-foreground">
                Authoritative count from PostgreSQL <code className="font-mono">access_key</code>
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-foreground">
              {keySettingsQuery.data?.active_keys_count ?? 0}
            </div>
            <div className="text-[11px] text-emerald-600 font-medium flex items-center justify-end gap-1">
              <CheckCircle2 className="h-3 w-3" /> Issued & Active
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Settings Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Designated Default Key Manager</CardTitle>
          <CardDescription className="text-xs">
            Select the staff manager responsible for default master access key operations.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="manager">Select Manager</Label>
            <DataState
              isLoading={usersQuery.isLoading || keySettingsQuery.isLoading}
              error={usersQuery.error ?? keySettingsQuery.error}
              isEmpty={staff.length === 0}
              emptyTitle="No staff users found"
            >
              <Select
                value={selectedManagerId ?? ""}
                onValueChange={(val) => setSelectedManagerId(val || undefined)}
                disabled={!mayWrite || updateKeySettings.isPending}
              >
                <SelectTrigger className="w-full max-w-md">
                  <SelectValue placeholder="Select a manager" />
                </SelectTrigger>
                <SelectContent className="bg-popover">
                  {staff.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {[user.first_name, user.last_name].filter(Boolean).join(" ")}
                      {user.department_name ? ` - ${user.department_name}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </DataState>
          </div>

          {keySettingsQuery.data?.manager_name && (
            <div className="p-3 bg-muted/30 rounded-lg text-xs space-y-1 border border-border/50">
              <div className="font-medium text-foreground">Current Active Manager:</div>
              <div className="text-muted-foreground">
                {keySettingsQuery.data.manager_name}
                {keySettingsQuery.data.manager_email && ` (${keySettingsQuery.data.manager_email})`}
              </div>
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button
              onClick={handleSave}
              disabled={!mayWrite || !hasChanges || updateKeySettings.isPending}
              className="bg-brand hover:bg-brand-hover text-white shadow-sm"
            >
              <Save className="h-4 w-4 mr-2" />
              {updateKeySettings.isPending ? "Saving..." : "Save Settings"}
            </Button>
            {hasChanges && (
              <Button
                variant="ghost"
                onClick={() => setSelectedManagerId(currentKeyUserId)}
                className="text-xs"
              >
                Discard Changes
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Reset Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Reset Default Key</CardTitle>
          <CardDescription className="text-xs">
            Revoke all active default keys and clear manager assignment in the database.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <Alert variant="destructive" className="border-destructive/50 bg-destructive/10">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Warning</AlertTitle>
            <AlertDescription>
              Resetting the default key will revoke all current key assignments
              and require re-configuration of access permissions for all staff
              members. This action cannot be undone.
            </AlertDescription>
          </Alert>

          <Button
            variant="destructive"
            onClick={() => setResetDialogOpen(true)}
            disabled={!mayWrite || resetKeySettings.isPending}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            {resetKeySettings.isPending ? "Resetting..." : "Reset Default Key"}
          </Button>
        </CardContent>
      </Card>

      {/* Confirmation Dialog for Reset */}
      <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold text-destructive flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" /> Confirm Default Key Reset
            </DialogTitle>
            <DialogDescription className="text-sm pt-2 text-foreground">
              Are you sure you want to reset default key settings? All active default master keys
              will be permanently revoked in the database (<code className="font-mono text-xs">status = 0</code>) and the current manager assignment will be unlinked.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0 pt-4">
            <Button
              variant="outline"
              onClick={() => setResetDialogOpen(false)}
              disabled={resetKeySettings.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleResetConfirm}
              disabled={resetKeySettings.isPending}
            >
              {resetKeySettings.isPending ? "Resetting..." : "Yes, Reset Default Key"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default KeySettings;
