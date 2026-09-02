import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from "react";

import {
  UNAUTHORIZED_EVENT,
  clearToken,
  getToken,
  setToken,
} from "@/lib/api/client";
import { fetchCurrentUser, login as loginRequest } from "@/lib/api/endpoints";
import type { CurrentUser, UserPermissionRead } from "@/lib/api/types";

/**
 * Real HMS Web authentication against POST /api/v1/auth/login.
 *
 * The backend issues the JWT and is the only thing that validates it; we store
 * the token and the identity it returns from GET /auth/me. No credential is
 * kept, and the token payload is never decoded here -- `permissions` come from
 * the backend's `role_module_permission` projection, not from the JWT.
 *
 * Access is by MODULE + read/write, never by role name. Administrator and
 * Duty Manager both reach HMS Web because the backend's `platform` says so
 * (role_type admin/manager); Staff, Technician and Guest are mobile platforms
 * and are refused by the backend at login, not by this file.
 */

export interface AuthContextType {
  user: CurrentUser | null;
  isAuthenticated: boolean;
  /** True while an existing token is being re-validated on a page load. */
  isRestoring: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  /** Effective permissions, straight from the backend. */
  permissions: UserPermissionRead[];
  canRead: (moduleName: string) => boolean;
  canWrite: (moduleName: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isRestoring, setIsRestoring] = useState<boolean>(() => Boolean(getToken()));

  const signOut = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  // Re-validate a stored token against the backend before trusting it. A token
  // that has expired or been revoked must not produce a logged-in shell.
  useEffect(() => {
    if (!getToken()) {
      setIsRestoring(false);
      return;
    }
    let cancelled = false;
    fetchCurrentUser()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        if (!cancelled) signOut();
      })
      .finally(() => {
        if (!cancelled) setIsRestoring(false);
      });
    return () => {
      cancelled = true;
    };
  }, [signOut]);

  // Any 401 from any request means the session is over.
  useEffect(() => {
    const handle = () => signOut();
    window.addEventListener(UNAUTHORIZED_EVENT, handle);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handle);
  }, [signOut]);

  const login = useCallback(async (username: string, password: string) => {
    const token = await loginRequest(username, password);
    setToken(token.access_token);
    try {
      setUser(await fetchCurrentUser());
    } catch (error) {
      // A token we cannot use is worse than none at all.
      clearToken();
      throw error;
    }
  }, []);

  const value = useMemo<AuthContextType>(() => {
    // Derived inside the memo so a new [] each render cannot churn consumers.
    const permissions = user?.permissions ?? [];
    const find = (moduleName: string) =>
      permissions.find((permission) => permission.module_name === moduleName);
    return {
      user,
      isAuthenticated: Boolean(user),
      isRestoring,
      login,
      logout: signOut,
      permissions,
      canRead: (moduleName) => Boolean(find(moduleName)?.read_access),
      canWrite: (moduleName) => Boolean(find(moduleName)?.write_access),
    };
  }, [user, isRestoring, login, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

/** Convenience for screens that only care about one module. */
export const useModuleAccess = (moduleName: string) => {
  const { canRead, canWrite } = useAuth();
  return { canRead: canRead(moduleName), canWrite: canWrite(moduleName) };
};
