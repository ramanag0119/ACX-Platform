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

const KeySettings = () => {
  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Default Key Settings</h1>
        <p className="page-description">
          Configure default key management and access settings
        </p>
      </div>

      {/* Settings Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Manager Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="manager">Select Manager</Label>
            <Select>
              <SelectTrigger className="w-full max-w-md">
                <SelectValue placeholder="Select a manager" />
              </SelectTrigger>
              <SelectContent className="bg-popover">
                <SelectItem value="john">John Smith - Operations</SelectItem>
                <SelectItem value="sarah">Sarah Johnson - Front Desk</SelectItem>
                <SelectItem value="michael">Michael Brown - Security</SelectItem>
                <SelectItem value="emily">Emily Davis - Housekeeping</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button>
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
