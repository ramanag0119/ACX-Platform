import { useState } from "react";
import { Outlet } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { AppHeader } from "./AppHeader";
import { cn } from "@/lib/utils";
import { ThemeProvider, useTheme } from "@/contexts/ThemeContext";

const AppLayoutInner = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { isDark } = useTheme();

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{
        background: isDark
          ? 'linear-gradient(180deg, #0f1117, #131824)'
          : 'linear-gradient(180deg, #F4F2FA, #ECE9F6)'
      }}
    >
      <AppSidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <AppHeader sidebarCollapsed={sidebarCollapsed} />
      <main
        className={cn(
          "pt-[70px] min-h-screen transition-all duration-300",
          sidebarCollapsed ? "pl-[84px]" : "pl-[276px]"
        )}
        style={{ marginLeft: "16px" }}
      >
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export const AppLayout = () => {
  return (
    <ThemeProvider>
      <AppLayoutInner />
    </ThemeProvider>
  );
};