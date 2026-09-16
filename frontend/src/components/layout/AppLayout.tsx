import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { AppHeader } from "./AppHeader";
import { cn } from "@/lib/utils";
import { ThemeProvider, useTheme } from "@/core/contexts/ThemeContext";
import { ModuleGuard } from "@/core/components/ModuleGuard";

const AppLayoutInner = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { isDark } = useTheme();

  useEffect(() => {
    const formatButtons = () => {
      // Remove any previously injected icons if present
      document.querySelectorAll(".btn-icon-svg").forEach((el) => el.remove());

      const buttons = document.querySelectorAll("button, [role='button'], .btn");
      buttons.forEach((btn) => {
        const text = btn.textContent?.trim().toLowerCase();
        if (text === "reset" || text === "cancel") {
          btn.classList.add("btn-reset");
        } else if (text === "submit" || text === "confirm" || text === "save") {
          btn.classList.add("btn-submit");
        }
      });
    };

    formatButtons();

    const observer = new MutationObserver(() => {
      formatButtons();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{
        background: isDark
          ? 'linear-gradient(180deg, #0f1117, #131824)'
          : 'linear-gradient(180deg, #F4F2FA, #ECE9F6)'
      }}
    >
      <AppHeader
        sidebarCollapsed={sidebarCollapsed}
        onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <AppSidebar collapsed={sidebarCollapsed} />
      {/*
        The shell is exactly one viewport tall, and the CONTENT scrolls inside
        it rather than the window.

        It used to be `min-h-screen` PLUS 48px/28px of padding for the fixed
        header and footer, so every page was 100vh + 76px and scrolled even
        when it had nothing to scroll. `h-screen` makes the padding part of the
        viewport instead of extra to it, which is what removes that dead space
        and lets a page's own heading stay put with plain `position: sticky`.
      */}
      <main
        className={cn(
          "pt-[48px] pb-[28px] h-screen transition-all duration-300 flex flex-col",
          sidebarCollapsed ? "pl-[64px]" : "pl-[240px]"
        )}
      >
        <div className="hms-content flex-1 min-h-0 overflow-y-auto px-4 py-3">
          <ModuleGuard>
            <Outlet />
          </ModuleGuard>
        </div>
      </main>

      {/* Full-width fixed bottom footer spanning 100% from left to right edge */}
      <footer className="fixed bottom-0 left-0 right-0 w-full h-[28px] z-50 flex items-center justify-between px-4 text-[11.5px] font-normal text-slate-500 dark:text-slate-400 border-t border-slate-200/90 dark:border-slate-800 bg-[#F0F4F8] dark:bg-[#0f1117] select-none">
        <div className="flex items-center">
          <span>© 2026 IKANOS Portal</span>
        </div>
        <div className="flex items-center">
          <span>Version : 2.1.0</span>
        </div>
      </footer>
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