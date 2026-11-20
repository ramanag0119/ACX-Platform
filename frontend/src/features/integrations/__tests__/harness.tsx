/**
 * Test-only render harness for integrations.test.cjs. Never imported by the
 * application (the Vite build does not reach it).
 *
 * The .cjs test bundles this file with esbuild and replaces
 * "@/core/contexts/AuthContext" with a stub that reads the signed-in user
 * from `globalThis.__TEST_AUTH__`, so the REAL sidebar, route guard, pages
 * and components render under any permission set without a backend.
 *
 * Pages are rendered with react-dom/server. React Query does not fetch during
 * a server render, so a page shows what the seeded cache holds -- and the
 * query keys it registers are returned, which is how the tests prove which
 * server-side filters and page a screen asked for.
 */
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AppSidebar } from "@/components/layout/AppSidebar";
import { ModuleGuard } from "@/core/components/ModuleGuard";
import { DataState, TableLoading } from "@/core/components/DataState";
import { ApiError } from "@/lib/api/client";
import * as integrationApi from "@/lib/api/integrations";
import type { DeadLetterEntry, IntegrationMessage, IntegrationOverview as Overview } from "@/lib/api/integrations";
import { moduleForPath } from "@/core/rbac/modules";
import { MessageFilterBar } from "../components/MessageFilterBar";
import { DeadLetterTable, MessageTable } from "../components/MessageTables";
import { QueryErrorState } from "../components/QueryErrorState";
import * as presentation from "../lib/presentation";
import DeadLetters from "../pages/DeadLetters";
import IntegrationOverview from "../pages/IntegrationOverview";
import MessageLogs from "../pages/MessageLogs";
import { FiasMonitoring, HtngMonitoring } from "../pages/ProtocolMonitoring";
import { OverviewView } from "../views/OverviewView";
import { MonitoringDashboard } from "../views/MonitoringDashboard";
import { ThemeProvider } from "@/core/contexts/ThemeContext";
import type { IntegrationMetrics } from "@/lib/api/integrations";

export { ApiError, integrationApi, moduleForPath, presentation };

type Seed = [unknown[], unknown];

function render(path: string, element: ReactElement, seed: Seed[] = []) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  for (const [key, data] of seed) client.setQueryData(key, data);
  const html = renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{element}</MemoryRouter>
    </QueryClientProvider>,
  );
  const keys = client.getQueryCache().getAll().map((q) => q.queryKey);
  client.clear();
  return { html, keys };
}

const PAGES: Record<string, () => ReactElement> = {
  "/integrations": () => <IntegrationOverview />,
  "/integrations/htng": () => <HtngMonitoring />,
  "/integrations/fias": () => <FiasMonitoring />,
  "/integrations/messages": () => <MessageLogs />,
  "/integrations/dlq": () => <DeadLetters />,
};

/** A real page inside the real route guard, at `path` (query string allowed). */
export function renderPage(path: string, seed: Seed[] = []) {
  const page = PAGES[path.split("?")[0]];
  if (!page) throw new Error(`no page for ${path}`);
  return render(path, <ModuleGuard>{page()}</ModuleGuard>, seed);
}

export function renderSidebar(path: string) {
  return render(path, <AppSidebar collapsed={false} />).html;
}

export const renderOverviewView = (data: Overview) => render("/integrations", <OverviewView data={data} />).html;

export const renderMessageTable = (rows: IntegrationMessage[], names: [string, string][] = []) =>
  render("/", <MessageTable rows={rows} facilityNames={new Map(names)} caption="t" />).html;

export const renderDeadLetterTable = (rows: DeadLetterEntry[]) =>
  render("/", <DeadLetterTable rows={rows} facilityNames={new Map()} caption="t" />).html;

export const renderQueryError = (error: unknown) =>
  render("/", <QueryErrorState error={error} onRetry={() => undefined} />).html;

export const renderLoading = () =>
  render("/", <DataState isLoading error={null} loader={<TableLoading columns={4} />}><span /></DataState>).html;

export const renderEmpty = (title: string) =>
  render("/", <DataState isLoading={false} error={null} isEmpty emptyTitle={title}><span /></DataState>).html;

export const renderFilterBar = (filters: presentation.MessageFilters, facilities: presentation.FacilityOption[]) =>
  render("/", <MessageFilterBar filters={filters} onChange={() => undefined} facilities={facilities} idPrefix="t" />).html;

// ------------------------------------------------- monitoring dashboard view

/** The windowed KPI + chart view on its own, optionally under the dark theme
 *  (ThemeProvider reads localStorage "theme" when it mounts). */
export function renderDashboard(opts: {
  protocol: "htng" | "fias";
  metrics?: IntegrationMetrics;
  isLoading?: boolean;
  error?: unknown;
  dark?: boolean;
}) {
  const saved = (globalThis as { localStorage?: unknown }).localStorage;
  (globalThis as { localStorage?: unknown }).localStorage = {
    getItem: () => (opts.dark ? "dark" : "light"), setItem() {}, removeItem() {},
  };
  try {
    return render(
      "/",
      <ThemeProvider>
        <MonitoringDashboard protocol={opts.protocol} metrics={opts.metrics} isLoading={opts.isLoading ?? false}
          error={opts.error ?? null} onRetry={() => undefined} />
      </ThemeProvider>,
    ).html;
  } finally {
    (globalThis as { localStorage?: unknown }).localStorage = saved;
  }
}
