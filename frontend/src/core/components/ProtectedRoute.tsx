import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/core/contexts/AuthContext";
import { InlineLoading } from "@/core/components/DataState";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Authentication gate. Module-level authorization happens one level in, at
 * <ModuleGuard> inside the layout, so a denied module still renders the
 * sidebar and header rather than throwing the user out of the shell.
 */
export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isAuthenticated, isRestoring } = useAuth();
  const location = useLocation();

  // Do not bounce to /login while a stored token is still being validated.
  if (isRestoring) return <InlineLoading label="Restoring your session..." />;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
};
