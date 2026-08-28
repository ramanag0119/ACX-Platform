import { useLocation } from "react-router-dom";
import { ShieldOff } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/core/contexts/AuthContext";
import { moduleForPath } from "@/core/rbac/modules";

/** Shown in place of a screen the signed-in role has no read grant for. */
export const ModuleDenied = ({ moduleName }: { moduleName: string }) => (
  <div className="space-y-6 animate-fade-in">
    <div className="page-header">
      <h1 className="page-title">Access denied</h1>
      <p className="page-description">
        Your role does not grant access to this module.
      </p>
    </div>
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 rounded-full bg-muted p-4">
          <ShieldOff className="h-10 w-10 text-muted-foreground" />
        </div>
        <h2 className="mb-2 text-xl font-semibold">No permission</h2>
        <p className="max-w-md text-muted-foreground">
          Read access to <span className="font-mono">{moduleName}</span> is not granted to any
          of your roles. Ask an administrator to update the role's module permissions.
        </p>
      </CardContent>
    </Card>
  </div>
);

/**
 * Route-level authorization, driven entirely by the backend's effective
 * permissions (`role_module_permission` via /auth/me). This is UX: it avoids
 * rendering a screen that would only fill with 403s. The API still enforces
 * the same rule on every request.
 */
export const ModuleGuard = ({ children }: { children: React.ReactNode }) => {
  const { canRead } = useAuth();
  const { pathname } = useLocation();

  const moduleName = moduleForPath(pathname);
  if (moduleName && !canRead(moduleName)) return <ModuleDenied moduleName={moduleName} />;

  return <>{children}</>;
};
