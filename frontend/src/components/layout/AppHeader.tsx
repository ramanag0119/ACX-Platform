import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, User, LogOut, Check, Trash2, X, Moon, Sun, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/core/contexts/AuthContext";
import { useTheme } from "@/core/contexts/ThemeContext";
import { useNotifications } from "@/lib/api/hooks";
import { describeApiError } from "@/lib/api/client";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface Notification {
  id: string;
  message: string;
  timestamp: string;
  read: boolean;
}

interface AppHeaderProps {
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
}

/**
 * The panel shows notification DELIVERY METADATA only -- template name and
 * status. The backend deliberately withholds the rendered body and params,
 * which carry OTPs and keypad keys for some templates, so there is no message
 * text to display and none is invented here.
 *
 * Read/unread is local presentation state: the schema stores no per-user read
 * flag for `notification`, and Phase 2.10 adds no writes.
 */
export const AppHeader = ({ sidebarCollapsed, onToggleSidebar }: AppHeaderProps) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const [readIds, setReadIds] = useState<Set<string>>(new Set());
  const [dismissed, setDismissed] = useState(false);
  const { logout, user, canRead } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();

  // /notifications is gated on the `dashboard` module by the backend.
  const notificationsQuery = useNotifications(
    canRead("dashboard") ? { page: 1, page_size: 20 } : undefined,
  );
  const canSeeNotifications = canRead("dashboard");

  const notifications = useMemo<Notification[]>(() => {
    if (dismissed || !canSeeNotifications) return [];
    return (notificationsQuery.data?.items ?? []).map((item) => ({
      id: String(item.id),
      message: `${item.template_name ?? "Notification"} - ${item.status}`,
      timestamp: new Date(item.created_on).toLocaleString(),
      read: readIds.has(String(item.id)),
    }));
  }, [notificationsQuery.data, readIds, dismissed, canSeeNotifications]);

  // A fresh page of notifications is unread again.
  useEffect(() => {
    setDismissed(false);
  }, [notificationsQuery.dataUpdatedAt]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const displayName = user
    ? [user.first_name, user.last_name].filter(Boolean).join(" ") || user.user_name || ""
    : "";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const markAllAsRead = () => {
    setReadIds(new Set(notifications.map((n) => n.id)));
  };

  const markAllAsUnread = () => {
    setReadIds(new Set());
  };

  const clearAll = () => {
    setDismissed(true);
  };

  return (
    <>
      <header
        className="fixed top-0 left-0 right-0 h-[48px] z-50 flex items-center justify-between px-3 md:px-4 bg-white dark:bg-[#0f1117] border-b border-slate-200/90 dark:border-slate-800 transition-colors shadow-xs"
      >
        {/* Left: Sidebar Toggle, App Icon, App Name */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onToggleSidebar}
            className="flex items-center justify-center w-8 h-8 rounded-md text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? (
              <Menu className="w-4 h-4" />
            ) : (
              <X className="w-4 h-4" />
            )}
          </button>

          <div className="flex items-center gap-2">
            <img
              src="/ikanos-app-icon.png"
              alt="Logo"
              className="w-6 h-6 object-contain rounded-md shadow-xs"
            />
            <span className="font-semibold text-[15px] text-[#2563eb] dark:text-blue-400 tracking-tight select-none">
              Inspironics Ikanos
            </span>
          </div>
        </div>

        {/* Right: Notifications, User, Theme Toggle, Logout */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Notifications */}
          <Button
            variant="ghost"
            size="icon"
            className="relative h-8 w-8 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            onClick={() => setShowNotifications(true)}
            title="Notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-primary text-white text-[9px] flex items-center justify-center font-bold">
                {unreadCount}
              </span>
            )}
          </Button>

          {/* User Display */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-1.5 py-1 px-2 rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-xs font-medium">
                <User className="h-3.5 w-3.5 text-slate-600 dark:text-slate-400" />
                <span className="hidden sm:inline">INSP Admin</span>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 rounded-xl shadow-lg border">
              <div className="px-3 py-2">
                <p className="text-sm font-medium truncate">{displayName || "Signed in"}</p>
                {user?.email && (
                  <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                )}
                {user?.roles?.length ? (
                  <p className="mt-1 text-xs text-muted-foreground truncate">
                    {user.roles.map((role) => role.role_name).join(", ")}
                  </p>
                ) : null}
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleLogout}
                className="cursor-pointer text-destructive focus:text-destructive text-xs"
              >
                <LogOut className="mr-2 h-3.5 w-3.5" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Dark Mode Toggle */}
          <button
            className="flex items-center justify-center w-8 h-8 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            onClick={toggleTheme}
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {isDark ? (
              <Sun className="h-4 w-4 text-amber-400" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </button>

          {/* Direct Logout Button */}
          <button
            onClick={handleLogout}
            className="flex items-center justify-center w-8 h-8 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-destructive transition-colors"
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Notification Panel Overlay */}
      {showNotifications && (
        <div
          className="fixed inset-0 bg-black/30 z-50"
          onClick={() => setShowNotifications(false)}
        >
          <div
            className="fixed right-0 top-0 h-full w-[380px] bg-card shadow-xl animate-slide-in-right border-l border-border"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Panel Header */}
            <div className="h-[70px] flex items-center justify-between px-5 border-b border-border">
              <h2 className="text-lg font-semibold">Notifications</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowNotifications(false)}
                className="h-8 w-8 rounded-lg hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 p-4 border-b border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={markAllAsUnread}
                className="text-xs rounded-lg h-8"
              >
                Mark all unread
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={markAllAsRead}
                className="text-xs rounded-lg h-8"
              >
                <Check className="h-3 w-3 mr-1" />
                Mark all read
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={clearAll}
                className="text-xs text-destructive hover:text-destructive rounded-lg h-8"
              >
                <Trash2 className="h-3 w-3 mr-1" />
                Clear
              </Button>
            </div>

            {/* Notification List */}
            <div className="overflow-y-auto h-[calc(100vh-8rem)] scrollbar-thin">
              {notificationsQuery.isLoading ? (
                <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                  <p className="text-sm">Loading notifications...</p>
                </div>
              ) : notificationsQuery.error ? (
                <div className="flex flex-col items-center justify-center h-48 px-6 text-center text-muted-foreground">
                  <Bell className="h-12 w-12 mb-3 opacity-20" />
                  <p className="text-sm">{describeApiError(notificationsQuery.error)}</p>
                </div>
              ) : notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                  <Bell className="h-12 w-12 mb-3 opacity-20" />
                  <p>No notifications</p>
                </div>
              ) : (
                <>
                  {notifications.filter((n) => !n.read).length > 0 && (
                    <div className="px-6 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      New
                    </div>
                  )}
                  {notifications
                    .filter((n) => !n.read)
                    .map((notification) => (
                      <div
                        key={notification.id}
                        className="mx-4 mb-2 p-4 rounded-xl bg-primary/5 border border-primary/10 hover:bg-primary/10 transition-colors cursor-pointer"
                      >
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 rounded-full bg-primary mt-2 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-foreground">
                              {notification.message}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {notification.timestamp}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}

                  {notifications.filter((n) => n.read).length > 0 && (
                    <div className="px-6 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Earlier
                    </div>
                  )}
                  {notifications
                    .filter((n) => n.read)
                    .map((notification) => (
                      <div
                        key={notification.id}
                        className="mx-4 mb-2 p-4 rounded-xl hover:bg-muted/50 transition-colors cursor-pointer"
                      >
                        <div className="flex items-start gap-3">
                          <div className="w-2 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-muted-foreground">
                              {notification.message}
                            </p>
                            <p className="text-xs text-muted-foreground/70 mt-1">
                              {notification.timestamp}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};