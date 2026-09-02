import { AlertTriangle, Save, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { DataState } from "@/core/components/DataState";
import { NoEndpointNotice } from "@/core/components/NoEndpointNotice";
import { useFacilities, useUsers } from "@/lib/api/hooks";
import { MAX_PAGE_SIZE } from "@/lib/api/types";

/**
 * Default Key Settings.
 *
 * The manager picker lists real staff from GET /users, and the currently
 * configured holder comes from `facility.default_key_user` on GET /facilities.
 *
 * Saving and resetting a default key are write flows over `access_key` /
 * `key_type`, which have no endpoint -- those controls are disabled.
 */
const KeySettings = () => {
  const usersQuery = useUsers({ page: 1, page_size: MAX_PAGE_SIZE, is_staff: 1 });
  const facilitiesQuery = useFacilities({ page: 1, page_size: MAX_PAGE_SIZE });

  const staff = usersQuery.data?.items ?? [];
  const currentKeyUserId = facilitiesQuery.data?.items[0]?.default_key_user ?? undefined;

  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Default Key Settings</h1>
        <p className="page-description">
          Configure default key management and access settings
        </p>
      </div>

      <NoEndpointNotice feature="Default key management" tables="access_key, key_type" />

      {/* Settings Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Manager Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="manager">Select Manager</Label>
            <DataState
              isLoading={usersQuery.isLoading || facilitiesQuery.isLoading}
              error={usersQuery.error ?? facilitiesQuery.error}
              isEmpty={staff.length === 0}
              emptyTitle="No staff users found"
            >
              <Select defaultValue={currentKeyUserId}>
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

          <Button disabled title="Saving needs a write endpoint, which does not exist">
            <Save className="h-4 w-4 mr-2" />
            Save Settings
          </Button>
        </CardContent>
      </Card>

      {/* Reset Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Reset Default Key</CardTitle>
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

          <Button variant="destructive">
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset Default Key
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default KeySettings;
