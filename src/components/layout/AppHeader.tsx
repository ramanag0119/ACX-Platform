import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, User, LogOut, Check, Trash2, X, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
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
  type: "info" | "warning" | "success" | "error";
}

const mockNotifications: Notification[] = [
  {
    id: "1",
    message: "Room 301 check-in completed successfully",
    timestamp: "2 minutes ago",
    read: false,
    type: "success",
  },
  {
    id: "2",
    message: "Firmware update available for MIKOS devices",
    timestamp: "15 minutes ago",
    read: false,
    type: "info",
  },
  {
    id: "3",
    message: "High energy consumption detected in Zone B",
    timestamp: "1 hour ago",
    read: false,
    type: "warning",
  },
  {
    id: "4",
    message: "Maintenance ticket #1234 has been resolved",
    timestamp: "2 hours ago",
    read: true,
    type: "success",
  },
  {
    id: "5",
    message: "New booking request for Conference Room A",
    timestamp: "3 hours ago",
    read: true,
    type: "info",
  },
];

interface AppHeaderProps {
  sidebarCollapsed: boolean;
}

export const AppHeader = ({ sidebarCollapsed }: AppHeaderProps) => {
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications);
  const [showNotifications, setShowNotifications] = useState(false);
  const { logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const unreadCount = notifications.filter((n) => !n.read).length;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const markAllAsUnread = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: false })));
  };

  const clearAll = () => {
    setNotifications([]);
  };

  return (
    <>
      <header
        className={cn(
          "fixed top-0 right-0 h-[70px] z-30 flex items-center justify-between px-6 transition-all duration-300",
          sidebarCollapsed ? "left-[72px]" : "left-[240px]"
        )}
        style={{
          background: '#FFFFFF',
          borderBottom: '1px solid rgba(124,92,255,0.1)'
        }}
      >
        <div className="flex items-center gap-3">
          {/* Search could go here */}
        </div>

        <div className="flex items-center gap-4">
          {/* Notifications */}
          <Button
            variant="ghost"
            size="icon"
            className="relative h-10 w-10 rounded-xl hover:bg-muted"
            onClick={() => setShowNotifications(true)}
          >
            <Bell className="h-5 w-5 text-muted-foreground" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-primary text-white text-[10px] flex items-center justify-center font-bold">
                {unreadCount}
              </span>
            )}
          </Button>

          {/* Dark Mode Toggle */}
          <Button
            variant="ghost"
            size="icon"
            className="relative h-10 w-10 rounded-xl hover:bg-muted transition-all duration-300"
            onClick={toggleTheme}
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            <div className="relative">
              {isDark ? (
                <Sun className="h-5 w-5 text-amber-400 transition-all duration-300 rotate-0 scale-100" />
              ) : (
                <Moon className="h-5 w-5 text-muted-foreground transition-all duration-300 rotate-0 scale-100" />
              )}
            </div>
          </Button>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-xl h-10 w-10 p-0 hover:bg-muted">
                <div className="h-9 w-9 rounded-xl bg-primary flex items-center justify-center">
                  <User className="h-4 w-4 text-white" />
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48 rounded-xl shadow-lg border">
              <DropdownMenuItem className="cursor-pointer rounded-lg">
                <User className="mr-2 h-4 w-4" />
                Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleLogout}
                className="cursor-pointer text-destructive focus:text-destructive rounded-lg"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
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
              {notifications.length === 0 ? (
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