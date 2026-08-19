import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { AppHeader } from "./AppHeader";
import { cn } from "@/lib/utils";
import { ThemeProvider, useTheme } from "@/core/contexts/ThemeContext";

const AppLayoutInner = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { isDark } = useTheme();

  useEffect(() => {
    const formatButtons = () => {
      const buttons = document.querySelectorAll("button, [role='button'], .btn");
      buttons.forEach((btn) => {
        const text = btn.textContent?.trim().toLowerCase();
        if (text === "reset") {
          btn.classList.add("btn-reset");
          if (!btn.querySelector(".btn-icon-svg")) {
            const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("class", "w-4 h-4 mr-2 btn-icon-svg inline-block align-middle");
            svg.setAttribute("fill", "none");
            svg.setAttribute("stroke", "currentColor");
            svg.setAttribute("stroke-width", "2.5");
            svg.setAttribute("viewBox", "0 0 24 24");
            svg.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"></path>`;
            btn.insertBefore(svg, btn.firstChild);
          }
        } else if (text === "submit" || text === "confirm" || text === "save") {
          btn.classList.add("btn-submit");
          if (!btn.querySelector(".btn-icon-svg")) {
            const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("class", "w-4 h-4 mr-2 btn-icon-svg inline-block align-middle");
            svg.setAttribute("fill", "none");
            svg.setAttribute("stroke", "currentColor");
            svg.setAttribute("stroke-width", "2.5");
            svg.setAttribute("viewBox", "0 0 24 24");
            svg.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"></path>`;
            btn.insertBefore(svg, btn.firstChild);
          }
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
      <main
        className={cn(
          "pt-[48px] pb-[28px] min-h-screen transition-all duration-300 flex flex-col justify-between",
          sidebarCollapsed ? "pl-[64px]" : "pl-[240px]"
        )}
      >
        <div className="p-5 flex-1">
          <Outlet />
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