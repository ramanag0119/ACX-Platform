/**
 * Integrations dashboard tests -- `node --test` + esbuild, the same tooling
 * as src/features/occupancy/__tests__/roomConditions.test.cjs (no extra
 * test framework is installed in this repository).
 *
 *   node --test src/features/integrations/__tests__/integrations.test.cjs
 *
 * Fixtures (observability-fixtures.json) are REAL responses produced by the
 * backend observability code in its synthetic test environment, so these
 * tests render the actual API contract, not a hand-written imitation.
 */
const { test, describe, before, beforeEach } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");
const esbuild = require("esbuild");

const ROOT = path.resolve(__dirname, "../../../..");
const FX = JSON.parse(fs.readFileSync(path.join(__dirname, "observability-fixtures.json"), "utf8"));
const FAC_A = "aaaaaaaa-0000-4000-8000-000000000001";
const FAC_B = "bbbbbbbb-0000-4000-8000-000000000002";

// --- bundle the harness in memory (nothing is written to the repository) ---
const authStub = {
  name: "auth-stub",
  setup(build) {
    build.onResolve({ filter: /^@\/core\/contexts\/AuthContext$/ }, () => ({ path: "auth", namespace: "stub" }));
    build.onLoad({ filter: /.*/, namespace: "stub" }, () => ({
      loader: "js",
      contents:
        "export const useAuth = () => globalThis.__TEST_AUTH__;\n" +
        "export const AuthProvider = ({ children }) => children;\n",
    }));
  },
};
let H;
let P;
before(async () => {
  const bundle = await esbuild.build({
    entryPoints: [path.join(__dirname, "harness.tsx")],
    bundle: true,
    platform: "node",
    format: "cjs",
    target: "node20",
    write: false,
    jsx: "automatic",
    tsconfig: path.join(ROOT, "tsconfig.app.json"),
    define: {
      "import.meta.env": JSON.stringify({ VITE_API_BASE_URL: "/api/v1" }),
      "process.env.NODE_ENV": '"production"',
    },
    plugins: [authStub],
    logLevel: "silent",
  });
  const virtualFile = path.join(__dirname, "harness.bundle.cjs");
  const mod = new Module(virtualFile);
  mod.filename = virtualFile;
  mod.paths = Module._nodeModulePaths(ROOT);
  mod._compile(bundle.outputFiles[0].text, virtualFile);
  H = mod.exports;
  P = H.presentation;
});

// --- helpers ------------------------------------------------------------------
function signIn({ read = true, write = false, facilities = [FAC_A] } = {}) {
  globalThis.__TEST_AUTH__ = {
    user: { id: "u", facility_ids: facilities, permissions: [] },
    isAuthenticated: true,
    isRestoring: false,
    permissions: [],
    canRead: (m) => m === "facility_management" && read,
    canWrite: (m) => m === "facility_management" && write,
  };
}
const FACILITIES_KEY = ["facilities", { page: 1, page_size: 100 }];
const facilitiesPage = {
  items: [
    { id: FAC_A, name: "Harbour View Hotel" },
    { id: FAC_B, name: "Hill Resort (other scope)" },
  ],
  page: 1,
  page_size: 100,
  total: 2,
};
const OVERVIEW_KEY = ["integrations", "overview"];
const count = (html, needle) => html.split(needle).length - 1;
const FORBIDDEN = ["body_masked", "payload", "password", "secret", "Jane", "guest_name", "4111"];
function assertNoSensitive(html) {
  for (const word of FORBIDDEN) assert.ok(!html.includes(word), `rendered output contains "${word}"`);
}
/** What a user can read: markup and attributes removed. */
const visibleText = (html) => html.replace(/<[^>]*>/g, " ").replace(/&[a-z]+;/g, " ").replace(/\s+/g, " ");
// Backend internals that must never reach the screen as visible text.
const INTERNALS = [
  "SQL", "API process", "service process", "this runtime", "backend/", "certification harness", "in-memory",
  "In-memory", "acx-generic", "ACX-SYNTHETIC", "http-soap", "tcp link", "hms_business_rule", "hms_unavailable",
  "read_timeout", "test.guest_arrival", "Correlation", "metadata only", "database_unavailable", "_or_",
];
function assertNoInternals(html) {
  const text = visibleText(html);
  for (const word of INTERNALS) assert.ok(!text.includes(word), `visible text contains internal "${word}"`);
}
/** The value shown in a KPI tile, found by its label. */
function kpi(html, label) {
  const m = html.match(new RegExp(`data-kpi="${label}"[\\s\\S]*?<p class="min-w-0[^"]*"[^>]*>([^<]*)</p>`));
  assert.ok(m, `KPI tile "${label}" not found`);
  return m[1];
}
const headings = (html) => [...html.matchAll(/<h2[^>]*>([^<]*)<\/h2>/g)].map((m) => m[1]);
// The monitoring pages derive their row-list window from Date.now(); pin it.
const FIXED_NOW = Date.parse("2026-11-10T08:10:00.000Z");
const SINCE_24H = new Date(FIXED_NOW - 86400 * 1000).toISOString();
const TZ = -new Date(FIXED_NOW).getTimezoneOffset() || 0;
function atNow(fn) {
  const real = Date.now;
  Date.now = () => FIXED_NOW;
  try {
    return fn();
  } finally {
    Date.now = real;
  }
}

beforeEach(() => signIn());

// ==================================================================== rules
describe("presentation rules", () => {
  test("null is never rendered as zero; zero stays zero", () => {
    assert.equal(P.formatMetric(null, "not_available"), "Unavailable");
    assert.equal(P.formatMetric(undefined, "not_observable"), "Not currently observable");
    assert.equal(P.formatMetric(0, "measured"), "0");
    assert.equal(P.sumMeasured([1, 2]), 3);
    assert.equal(P.sumMeasured([1, null]), null);
    assert.equal(P.formatTimestamp(null, true), "None recorded");
    assert.equal(P.formatTimestamp(null, false), "Unavailable");
    assert.equal(P.formatAge(null), "Unavailable");
  });

  test("not observable is 'unknown', never a failure tone", () => {
    for (const s of ["not_observable", "not_available", "not_reported"]) {
      assert.equal(P.presentStatus(s).tone, "unknown", s);
    }
    assert.equal(P.presentStatus("disconnected").tone, "negative");
    assert.equal(P.presentStatus("pending").label, "Pending");
    assert.equal(P.presentStatus("some_new_state").label, "Some new state");
  });

  test("readiness keeps eight separate dimensions in a fixed order", () => {
    const rows = P.readinessRows(FX.overview_measured.protocols.fias.readiness);
    assert.deepEqual(rows.map((r) => r.key), [
      "transport", "authentication", "processing", "synthetic_certification",
      "vendor_validation", "business_approval", "dba_schema_approval", "production_readiness",
    ]);
    assert.deepEqual(rows[4].details, ["HF-05", "HF-06", "HF-11"]);
  });

  test("readable reasons and compact table timestamps", () => {
    assert.equal(P.reasonLabel("dba_schema_approval_pending"), "DBA / schema approval pending");
    assert.equal(P.reasonLabel("persistence_in_memory"), "Message storage not provisioned");
    assert.equal(P.reasonLabel("something_new"), "Something new");
    const rows = P.readinessRows(FX.overview_measured.protocols.htng.readiness);
    assert.ok(!rows[7].details.some((d) => d.startsWith("Dba")), "no 'Dba' casing");
    assert.ok(!rows[3].note.includes("backend/"), "the harness path is not shown");
    assert.equal(P.formatShortTimestamp(null), "—");
    const thisYear = new Date().getFullYear();
    assert.ok(!P.formatShortTimestamp(`${thisYear}-03-04T10:00:00+00:00`).includes(String(thisYear)));
    assert.ok(P.formatShortTimestamp("2019-03-04T10:00:00+00:00").includes("2019"));
  });

  test("backend identifiers are translated into business wording", () => {
    assert.equal(P.messageTypeLabel("stay.check_in"), "Check-in");
    assert.equal(P.messageTypeLabel("stay.check_out"), "Check-out");
    assert.equal(P.messageTypeLabel("test.guest_arrival"), "Guest arrival");
    assert.equal(P.messageTypeLabel("stay.room_change_v2"), "Room change v2");
    assert.equal(P.failureLabel("hms_business_rule"), "Rejected by HMS business rule");
    assert.equal(P.failureLabel("hms_unavailable"), "HMS temporarily unavailable");
    assert.equal(P.failureLabel("stay_not_found"), "Stay not found");
    assert.equal(P.failureLabel("some_new_code"), "Some new code");
    assert.equal(P.failureLabel(null), "—");
    assert.equal(P.failureCategoryLabel("permanent"), "Permanent");
    assert.equal(P.failureCategoryLabel("transient"), "Temporary");
    assert.equal(P.authFailureLabel("invalid_secret"), "Invalid credentials");
    assert.equal(P.specificationLabel("test_only", "acx-generic-xml-test/0"), "Test specification only");
    assert.equal(P.specificationLabel("blocked", null), "Not received");
    assert.equal(P.presentStatus("DEAD_LETTER").label, "Failed");
    assert.equal(P.presentStatus("RETRY_WAIT").label, "Awaiting retry");
    assert.match(P.explainStatus("transport", "not_observable"), /not reported/);
    assert.equal(P.unavailableExplanation(P.LOAD_FAILED), "Could not be loaded right now.");
    assert.equal(P.unavailableExplanation("not_available"), "Message storage is not available.");
    assert.equal(P.explainStatus("transport", "something_else"), null);
  });

  test("URL filters accept only values the backend accepts", () => {
    const f = P.parseFilters(new URLSearchParams("protocol=test&status=BOGUS&facility=x&from=2026-1-1&page=-3&size=7"));
    assert.deepEqual(f, { protocol: undefined, status: undefined, facilityId: undefined, from: undefined, to: undefined, page: 1, pageSize: 20 });
    const g = P.parseFilters(new URLSearchParams(`protocol=fias&status=DEAD_LETTER&facility=${FAC_A}&page=3&size=50`));
    assert.equal(g.protocol, "fias");
    assert.equal(g.status, "DEAD_LETTER");
    assert.equal(g.facilityId, FAC_A);
    assert.deepEqual([g.page, g.pageSize], [3, 50]);
    assert.deepEqual(P.filtersToSearch(g), { protocol: "fias", status: "DEAD_LETTER", facility: FAC_A, page: "3", size: "50" });
  });

  test("server params carry ISO instants with an offset and a clamped page size", () => {
    const params = P.toQueryParams({ page: 2, pageSize: 500, from: "2026-11-01", to: "2026-11-02", protocol: "htng" });
    assert.equal(params.page_size, 100);
    assert.match(String(params.received_from), /Z$/);
    assert.ok(new Date(params.received_to) > new Date(params.received_from));
    assert.equal(P.toQueryParams({ page: 1, pageSize: 20, status: "PENDING" }, { withStatus: false }).status, undefined);
  });

  test("date range validation mirrors the backend's 31-day limit", () => {
    assert.equal(P.validateDateRange("2026-11-05", "2026-11-01"), "The end date is before the start date.");
    assert.match(P.validateDateRange("2026-01-01", "2026-03-01"), /31 days/);
    assert.equal(P.validateDateRange("2026-01-01", "2026-03-01", null), null);
    assert.equal(P.validateDateRange("2026-11-01", "2026-11-20"), null);
  });

  test("facility choices and filters are restricted to the user's scope", () => {
    const opts = P.facilityOptions(facilitiesPage.items, [FAC_A]);
    assert.deepEqual(opts, [{ id: FAC_A, label: "Harbour View Hotel" }]);
    assert.equal(P.facilityOptions([], [FAC_B])[0].label, "Facility bbbbbbbb");
    const f = { page: 1, pageSize: 20, facilityId: FAC_B };
    assert.equal(P.restrictToScope(f, [FAC_A]).facilityId, undefined);
    assert.equal(P.restrictToScope(f, [FAC_A, FAC_B]).facilityId, FAC_B);
  });
});

// ========================================================= navigation / RBAC
describe("navigation and RBAC", () => {
  const ROUTES = ["/integrations", "/integrations/htng", "/integrations/fias", "/integrations/messages", "/integrations/dlq"];

  test("every Integrations route is guarded by facility_management", () => {
    for (const r of ROUTES) assert.equal(H.moduleForPath(r), "facility_management", r);
  });

  test("routes are registered inside the authenticated layout", () => {
    const app = fs.readFileSync(path.join(ROOT, "src/App.tsx"), "utf8");
    const protectedBlock = app.slice(app.indexOf("<ProtectedRoute>"), app.indexOf('path="*"'));
    for (const r of ROUTES) assert.ok(protectedBlock.includes(`path="${r}"`), r);
  });

  test("sidebar shows the Integrations group and its five screens to a reader", () => {
    const html = H.renderSidebar("/integrations/messages");
    assert.ok(html.includes("Integrations"));
    for (const [href, label] of [
      ["/integrations", "Overview"], ["/integrations/htng", "HTNG Monitoring"], ["/integrations/fias", "FIAS Monitoring"],
      ["/integrations/messages", "Message Logs"], ["/integrations/dlq", "Failed Messages / DLQ"],
    ]) {
      assert.ok(html.includes(`href="${href}"`), href);
      assert.ok(html.includes(label), label);
    }
  });

  test("sidebar hides the group without facility_management read", () => {
    signIn({ read: false });
    const html = H.renderSidebar("/integrations/messages");
    assert.ok(!html.includes("Integrations"));
    assert.ok(!html.includes("/integrations"));
  });

  test("route guard denies the page and requests nothing without the grant", () => {
    signIn({ read: false });
    for (const r of ROUTES) {
      const { html, keys } = H.renderPage(r);
      assert.ok(html.includes("Access denied"), r);
      assert.ok(html.includes("facility_management"), r);
      assert.equal(keys.filter((k) => k[0] === "integrations").length, 0, `${r} issued an integrations query`);
    }
  });
});

// ================================================================= overview
describe("Integration Overview", () => {
  const recentKey = ["integrations", "messages", { page: 1, page_size: 5 }];
  const failedKey = ["integrations", "dlq", { page: 1, page_size: 5 }];

  test("renders HTNG and FIAS independently from the real overview contract", () => {
    const { html, keys } = H.renderPage("/integrations", [[OVERVIEW_KEY, FX.overview_measured]]);
    assert.deepEqual(keys.filter((k) => k[0] === "integrations"), [OVERVIEW_KEY, recentKey, failedKey]);
    assert.equal(count(html, 'data-protocol="htng"'), 1);
    assert.equal(count(html, 'data-protocol="fias"'), 1);
    assert.ok(html.includes("SOAP/XML web service") && html.includes("TCP socket link"));
    for (const label of [
      "Connection", "Authentication", "Processing", "Vendor validation", "Last successful processing",
      "Inbound", "Outbound", "Pending", "Awaiting retry", "Failed (DLQ)", "Latest failure",
    ]) {
      assert.equal(count(html, `>${label}</dt>`), 2, `each protocol panel shows "${label}"`);
    }
    assert.ok(html.includes("Rejected by HMS business rule"), "HTNG latest failure, in business wording");
    assert.ok(html.includes("HMS temporarily unavailable"), "FIAS latest failure, in business wording");
    assert.ok(html.includes('href="/integrations/htng"') && html.includes('href="/integrations/messages?protocol=fias"'));
    assertNoSensitive(html);
    assertNoInternals(html);
  });

  test("page structure: status, KPIs, protocol health, recent activity", () => {
    const { html } = H.renderPage("/integrations", [[OVERVIEW_KEY, FX.overview_measured]]);
    assert.deepEqual(headings(html).filter((h) => h !== "Integration Overview"), [
      "Integration status", "Message activity", "HTNG health", "FIAS health", "Recent messages", "Latest failures",
    ]);
    assert.ok(html.includes("Refresh"));
  });

  test("status accuracy: not observable is shown as such; vendor pending; never production ready", () => {
    const { html } = H.renderPage("/integrations", [[OVERVIEW_KEY, FX.overview_measured]]);
    assert.ok(html.includes('data-status="not_observable"'), "FIAS transport");
    assert.ok(!html.includes('data-status="not_observable" data-tone="negative"'));
    assert.ok(!html.includes('data-status="connected"'), "FIAS is never shown as connected");
    assert.ok(html.includes("Vendor validation pending"));
    assert.equal(count(html, 'data-status="pending"') >= 2, true);
    assert.ok(!html.includes('data-status="ready"'));
    assert.ok(!html.includes('data-status="validated"'));
    assert.ok(!html.includes("Production ready"));
    assert.ok(html.includes("Passing synthetic tests is not vendor certification"));
  });

  test("KPIs: measured counts, derived totals only from measured values", () => {
    const html = H.renderOverviewView(FX.overview_measured);
    // inbound HTNG 4 + FIAS 3; outbound 1 + 0; retry 0 + 1; DLQ 1 inbound + 0 outbound
    for (const [label, value] of [
      ["Inbound", "7"], ["Outbound", "1"], ["Pending", "3"], ["Failed", "1"], ["Awaiting retry", "1"], ["DLQ", "1"],
    ]) {
      assert.equal(kpi(html, label), value, label);
    }
    assert.ok(html.includes("not lifetime totals"));
  });

  test("unavailable telemetry renders as unavailable with a reason, never as 0", () => {
    const html = H.renderOverviewView(FX.overview_unavailable);
    // 6 KPI tiles + 5 counts on each of the 2 protocol panels
    assert.equal(count(html, 'data-unavailable="true"'), 16, "every count is marked unavailable");
    for (const label of ["Inbound", "Outbound", "Pending", "Failed", "Awaiting retry", "DLQ"]) {
      assert.equal(kpi(html, label), "Unavailable", label);
    }
    assert.ok(html.includes("Message storage is not available."), "short explanation on each tile");
    assert.ok(html.includes("Not observable"));
    assert.ok(!html.includes(">0<"), "no zero anywhere when nothing was measured");
    assertNoInternals(html);
  });

  test("recent activity shows the newest messages and failures in business wording", () => {
    const { html } = H.renderPage("/integrations", [
      [OVERVIEW_KEY, FX.overview_measured], [recentKey, FX.messages_page], [failedKey, FX.dlq_page],
      [FACILITIES_KEY, facilitiesPage],
    ]);
    assert.equal(count(html, "data-message-id="), FX.messages_page.items.length + FX.dlq_page.items.length);
    assert.ok(html.includes("Guest arrival"));
    assert.ok(html.includes("Harbour View Hotel"));
    assert.ok(html.includes('href="/integrations/messages"') && html.includes('href="/integrations/dlq"'));
    assertNoSensitive(html);
    assertNoInternals(html);
    const empty = { items: [], page: 1, page_size: 5, total: 0, window: FX.messages_page.window };
    const none = H.renderPage("/integrations", [[OVERVIEW_KEY, FX.overview_measured], [recentKey, empty], [failedKey, empty]]).html;
    assert.ok(none.includes("No messages in the last 7 days") && none.includes("No failed messages"));
  });

  test("loading state while the overview is fetched", () => {
    const { html } = H.renderPage("/integrations");
    assert.ok(html.includes("Loading integration status..."));
  });

  test("responsive layout: panels stack on small screens, two columns on wide", () => {
    const html = H.renderOverviewView(FX.overview_measured);
    assert.ok(html.includes("grid-cols-1") && html.includes("xl:grid-cols-2") && html.includes("md:grid-cols-3"));
    assert.ok(html.includes("grid-cols-2") && html.includes("xl:grid-cols-6"));
    assert.ok(html.includes("rounded-[16px]"), "HMS card radius");
    assert.ok(html.includes("linear-gradient"), "HMS card surface");
  });
});

// ======================================================== protocol screens
describe("HTNG and FIAS monitoring", () => {
  const recentKey = (protocol) => ["integrations", "messages", { protocol, page: 1, page_size: 10, received_from: SINCE_24H }];
  const dlqKey = (protocol) => ["integrations", "dlq", { protocol, page: 1, page_size: 5, received_from: SINCE_24H }];

  test("HTNG page: sections, protocol-filtered requests, links to filtered logs", () => {
    const empty = { items: [], page: 1, page_size: 10, total: 0, window: FX.messages_page.window };
    const { html, keys } = atNow(() => H.renderPage("/integrations/htng", [
      [OVERVIEW_KEY, FX.overview_measured], [recentKey("htng"), empty], [dlqKey("htng"), FX.dlq_page],
      [FACILITIES_KEY, facilitiesPage],
    ]));
    assert.deepEqual(keys.filter((k) => k[0] === "integrations").map((k) => k[1]).sort(), ["dlq", "messages", "metrics", "overview"]);
    assert.ok(html.includes("HTNG Monitoring"));
    assert.equal(count(html, "data-dimension="), 8);
    assert.ok(html.includes('href="/integrations/messages?protocol=htng"'));
    assert.ok(html.includes('href="/integrations/dlq?protocol=htng"'));
    assert.ok(html.includes("No HTNG messages in this period"), "empty state for the selected window");
    // In a protocol context the redundant Protocol column is dropped.
    assert.ok(html.includes(">Reprocessing<") && !html.includes(">Protocol</th>"));
    assert.ok(html.includes("Harbour View Hotel"), "facility name from the facilities list");
    assert.ok(html.includes("HF-07") && html.includes("HF-08"));
    assert.ok(html.includes("Test specification only"));
    assert.ok(html.includes("Rejected by HMS business rule"));
    assertNoSensitive(html);
    assertNoInternals(html);
  });

  test("HTNG and FIAS share the same section structure", () => {
    const htng = atNow(() => H.renderPage("/integrations/htng", [[OVERVIEW_KEY, FX.overview_measured]])).html;
    const fias = atNow(() => H.renderPage("/integrations/fias", [[OVERVIEW_KEY, FX.overview_measured]])).html;
    const sections = (html, label) => headings(html).filter((h) => h !== `${label} Monitoring`).map((h) => h.replace(label, "X"));
    // Metrics not loaded yet: the dashboard shows its loading skeleton, no headings.
    const expected = [
      "Transport and integration health", "Connection", "Authentication", "Processing",
      "Recent messages", "Failed messages", "Vendor validation", "X readiness",
    ];
    assert.deepEqual(sections(htng, "HTNG"), expected);
    assert.deepEqual(sections(fias, "FIAS"), expected);
    assert.ok(htng.includes('data-dashboard-loading="true"') && fias.includes('data-dashboard-loading="true"'));
  });

  test("FIAS page: unobservable link stated accurately, never as connected", () => {
    const { html } = H.renderPage("/integrations/fias", [[OVERVIEW_KEY, FX.overview_measured]]);
    assert.ok(html.includes("TCP socket link"));
    assert.ok(html.includes("Live link state is not reported to this dashboard"));
    assert.ok(!html.includes('data-status="disconnected"'), "unobservable must not read as disconnected");
    assert.ok(!html.includes('data-status="connected"'), "unobservable must not read as connected");
    assertNoInternals(html);
  });

  test("FIAS page: tagged links show per-link state and active connections", () => {
    const { html } = H.renderPage("/integrations/fias", [[OVERVIEW_KEY, FX.overview_fias_links]]);
    assert.ok(html.includes("fias-link-1") && html.includes("fias-link-2"));
    assert.ok(html.includes('data-status="degraded"'));
    assert.ok(html.includes("Read timed out"));
    assertNoInternals(html);
  });
});

// ============================================================ message logs
describe("Message Logs", () => {
  test("filters and page come from the URL and are sent to the server", () => {
    const { keys } = H.renderPage(`/integrations/messages?protocol=fias&status=RETRY_WAIT&facility=${FAC_A}&page=2&size=50`);
    const msgKeys = keys.filter((k) => k[0] === "integrations" && k[1] === "messages");
    assert.equal(msgKeys.length, 1);
    assert.deepEqual(JSON.parse(JSON.stringify(msgKeys[0][2])), {
      page: 2, page_size: 50, protocol: "fias", facility_id: FAC_A, status: "RETRY_WAIT",
    });
  });

  test("a facility outside the user's scope is never requested", () => {
    const { keys } = H.renderPage(`/integrations/messages?facility=${FAC_B}`);
    const params = keys.find((k) => k[1] === "messages")[2];
    assert.equal(params.facility_id, undefined);
  });

  test("server page renders rows and the server total drives pagination", () => {
    const params = { page: 1, page_size: 20, protocol: "fias" };
    const page = { ...FX.messages_page, page_size: 20 };
    const { html } = H.renderPage("/integrations/messages?protocol=fias", [
      [["integrations", "messages", params], page], [FACILITIES_KEY, facilitiesPage],
    ]);
    assert.equal(count(html, "data-message-id="), FX.messages_page.items.length);
    assert.ok(html.includes(`of ${FX.messages_page.total} entries`), "total from the server, not the rows");
    assert.ok(html.includes(`${FX.messages_page.total} messages`), "results count");
    for (const col of ["Message", "Protocol", "Facility", "Status", "Received", "Processed", "Retries", "Failure reason"]) {
      assert.ok(html.includes(`>${col}</th>`), col);
    }
    assert.ok(html.includes("Ref corr-f2") && html.includes("HMS temporarily unavailable") && html.includes("Temporary"));
    assert.ok(html.includes("Guest arrival"), "message type in business wording");
    assert.ok(html.includes("Harbour View Hotel"));
    assert.ok(!html.includes("Hill Resort"), "facility outside scope is not offered");
    assert.ok(html.includes("overflow-x-auto"), "table scrolls horizontally on narrow screens");
    assert.deepEqual(headings(html), ["Filters", "Messages"]);
    assertNoSensitive(html);
    assertNoInternals(html);
  });

  test("empty result and invalid date range", () => {
    const params = { page: 1, page_size: 20 };
    const empty = { items: [], page: 1, page_size: 20, total: 0, window: FX.messages_page.window };
    assert.ok(H.renderPage("/integrations/messages", [[["integrations", "messages", params], empty]]).html
      .includes("No messages match these filters"));
    const bad = H.renderPage("/integrations/messages?from=2026-11-10&to=2026-11-01").html;
    assert.ok(bad.includes('role="alert"') && bad.includes("The end date is before the start date."));
  });

  test("filter bar is accessible and responsive", () => {
    const html = H.renderFilterBar({ page: 1, pageSize: 20 }, [{ id: FAC_A, label: "Harbour View Hotel" }]);
    for (const name of ["Protocol filter", "Status filter", "Facility filter", "Rows per page"]) {
      assert.ok(html.includes(`aria-label="${name}"`), name);
    }
    assert.ok(html.includes('for="t-from"') && html.includes('id="t-from"'));
    assert.ok(html.includes("sm:grid-cols-2") && html.includes("xl:grid-cols-6"));
  });
});

// ===================================================================== DLQ
describe("Failed Messages / DLQ", () => {
  test("renders dead letters read-only with reprocessing eligibility as reported", () => {
    const params = { page: 1, page_size: 20 };
    const { html, keys } = H.renderPage("/integrations/dlq?status=PENDING", [
      [["integrations", "dlq", params], FX.dlq_page], [OVERVIEW_KEY, FX.overview_measured],
    ]);
    const sent = keys.find((k) => k[1] === "dlq")[2];
    assert.equal(sent.status, undefined, "the DLQ screen never sends a status filter");
    for (const col of ["Message", "Facility", "Failure category", "Failure reason", "Retry attempts", "Last attempt", "Reprocessing"]) {
      assert.ok(html.includes(`>${col}</th>`), col);
    }
    assert.ok(html.includes("Permanent") && html.includes("Rejected by HMS business rule"));
    assert.match(visibleText(html), /Received [^—\s]/, "received time shown under the last attempt");
    assert.ok(visibleText(html).includes("HTNG Guest arrival"), "protocol tag beside the message type");
    assert.ok(html.includes("Requires write access"), "fixture caller lacks write");
    assert.ok(!/<button[^>]*>[^<]*(Redrive|Reprocess)/i.test(html), "no redrive action is exposed");
    assert.ok(html.includes("Reprocessing is not available from this screen"));
    assert.deepEqual(headings(html), ["Failure summary", "Filters", "Failed messages"]);
    assert.equal(kpi(html, "Total in DLQ"), "1");
    assert.equal(kpi(html, "HTNG inbound"), "1");
    assert.equal(kpi(html, "FIAS inbound"), "0");
    assert.equal(kpi(html, "Outbound"), "0");
    assertNoSensitive(html);
    assertNoInternals(html);
  });

  test("failure summary is unavailable, not zero, when counts cannot be measured", () => {
    const { html } = H.renderPage("/integrations/dlq", [[OVERVIEW_KEY, FX.overview_unavailable]]);
    for (const label of ["Total in DLQ", "HTNG inbound", "FIAS inbound", "Outbound"]) {
      assert.equal(kpi(html, label), "Unavailable", label);
    }
  });

  test("eligibility wording follows the backend's flags", () => {
    const row = FX.dlq_page.items[0];
    const eligible = H.renderDeadLetterTable([{ ...row, redrive: { state_eligible: true, caller_has_permission: true, eligible: true } }]);
    assert.ok(eligible.includes(">Eligible<"));
    const notState = H.renderDeadLetterTable([{ ...row, redrive: { state_eligible: false, caller_has_permission: true, eligible: false } }]);
    assert.ok(notState.includes(">Not eligible<"));
  });
});

// ============================================================ error states
describe("loading, empty and error states", () => {
  const err = (status, code = "x") => new H.ApiError(status, { code, message: "m" });

  test("403 and 401 render without a retry button", () => {
    const forbidden = H.renderQueryError(err(403));
    assert.ok(forbidden.includes("Access denied") && !forbidden.includes("Retry"));
    const unauth = H.renderQueryError(err(401));
    assert.ok(unauth.includes("Session expired") && !unauth.includes("Retry"));
  });

  test("503 and network failures offer a retry", () => {
    const down = H.renderQueryError(err(503));
    assert.ok(down.includes("Service unavailable") && down.includes("Retry"));
    const net = H.renderQueryError(err(0, "network_error"));
    assert.ok(net.includes("Retry"));
  });

  test("shared loading skeleton and empty state", () => {
    assert.ok(H.renderLoading().includes('aria-label="Loading"'));
    assert.ok(H.renderEmpty("Nothing here").includes("Nothing here"));
  });
});

// ============================================================== API client
describe("API integration", () => {
  function withFetch(responder, fn) {
    const calls = [];
    const saved = { fetch: globalThis.fetch, window: globalThis.window, localStorage: globalThis.localStorage };
    const events = new EventTarget();
    globalThis.window = events;
    globalThis.localStorage = { getItem: () => "test-token", setItem() {}, removeItem() {} };
    globalThis.fetch = async (url, init) => {
      calls.push({ url, init });
      return responder(url);
    };
    return fn(calls, events).finally(() => Object.assign(globalThis, saved));
  }
  const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

  test("overview uses the existing client, base URL and bearer token", () =>
    withFetch(() => json(200, FX.overview_measured), async (calls) => {
      const data = await H.integrationApi.getIntegrationOverview();
      assert.equal(calls[0].url, "/api/v1/integrations/observability/overview");
      assert.equal(calls[0].init.headers.Authorization, "Bearer test-token");
      assert.equal(calls[0].init.method, "GET");
      assert.equal(data.protocols.fias.protocol, "fias");
    }));

  test("search sends only set filters as query parameters", () =>
    withFetch(() => json(200, FX.messages_page), async (calls) => {
      await H.integrationApi.searchIntegrationMessages({ protocol: "htng", page: 2, page_size: 50, status: undefined });
      assert.equal(calls[0].url, "/api/v1/integrations/observability/messages?protocol=htng&page=2&page_size=50");
      await H.integrationApi.listIntegrationDeadLetters({ page: 1, page_size: 20 });
      assert.equal(calls[1].url, "/api/v1/integrations/observability/dlq?page=1&page_size=20");
    }));

  test("401 signs the session out; 403 surfaces as forbidden", () =>
    withFetch((url) => json(url.includes("overview") ? 401 : 403, { error: { code: "x", message: "no" } }), async (_calls, events) => {
      let signedOut = false;
      events.addEventListener("hms:unauthorized", () => { signedOut = true; });
      await assert.rejects(H.integrationApi.getIntegrationOverview(), (e) => e.isUnauthorized);
      assert.ok(signedOut);
      await assert.rejects(H.integrationApi.listIntegrationDeadLetters({ page: 1 }), (e) => e.isForbidden);
    }));
});

// ============================================== operational status truth (backend fixture)
describe("operational status: backlog, outbound and blockers", () => {
  const OP = () => FX.overview_operational;

  test("presentation: distinct labels for every processing and outbound state", () => {
    assert.equal(P.presentStatus("waiting_for_retry").label, "Waiting for scheduled retry");
    assert.equal(P.presentStatus("waiting_for_retry").tone, "neutral", "a scheduled retry is not a failure");
    assert.equal(P.presentStatus("processing").label, "Processing");
    assert.equal(P.presentStatus("queued_no_sender").label, "Queued · no sender");
    assert.equal(P.presentStatus("backlog_stalled").tone, "negative", "a real stall stays red");
    assert.match(P.explainStatus("processing", "waiting_for_retry"), /not a stall/);
    assert.match(P.explainStatus("outbound", "queued_no_sender"), /no vendor delivery is configured/);
    assert.equal(P.blockerLabel("vendor_specification"), "Vendor specification");
    assert.equal(P.blockerLabel("dba_approval"), "DBA approval");
  });

  test("overview: a scheduled retry is not shown as stalled; a real stall still is", () => {
    const { html } = H.renderPage("/integrations", [[OVERVIEW_KEY, OP()]]);
    const op = OP();
    assert.equal(op.protocols.htng.processing.status, "waiting_for_retry");
    assert.equal(op.protocols.fias.processing.status, "backlog_stalled");
    assert.ok(html.includes('data-status="waiting_for_retry"'), "HTNG processing badge");
    assert.ok(html.includes('data-status="backlog_stalled"'), "FIAS genuine stall stays visible");
    assert.ok(!html.includes('data-status="ready"') && !html.includes("Production ready"), "never a false green");
    assertNoInternals(html);
  });

  test("overview: 'Not ready' names what blocks it", () => {
    const { html } = H.renderPage("/integrations", [[OVERVIEW_KEY, OP()]]);
    assert.equal(count(html, "data-blocked-by="), 2, "one blocker list per protocol");
    for (const label of ["Vendor specification", "Business approval", "DBA approval", "Test results not published", "Switched off"]) {
      assert.ok(html.includes(label), label);
    }
  });

  test("protocol page: backlog breakdown and outbound delivery state come from the backend", () => {
    const htng = H.renderPage("/integrations/htng", [[OVERVIEW_KEY, OP()]]).html;
    for (const label of ["Due now", "Oldest due wait", "Retries scheduled later", "Being processed", "Outbound delivery", "Vendor delivery", "Queued outbound"]) {
      assert.ok(htng.includes(`>${label}</dt>`), label);
    }
    assert.ok(htng.includes('data-outbound-status="queued_no_sender"') && htng.includes(">Not configured<"));
    assert.ok(htng.includes("not a stall"), "explanation of a scheduled retry");
    const fias = H.renderPage("/integrations/fias", [[OVERVIEW_KEY, OP()]]).html;
    assert.ok(fias.includes(">Held behind a failed message</dt>"), "ordering-blocked count is surfaced");
    assert.ok(fias.includes("nothing appears to be processing them"));
    assertNoInternals(htng);
    assertNoInternals(fias);
  });

  test("older responses without the breakdown still render (no crash, no invented numbers)", () => {
    const html = H.renderPage("/integrations/htng", [[OVERVIEW_KEY, FX.overview_measured]]).html;
    assert.ok(html.includes(">Oldest pending message</dt>") && !html.includes(">Due now</dt>"));
    assert.ok(!html.includes("data-outbound-status="), "no outbound block when the backend did not send one");
  });
});

// ===================================================== monitoring dashboards (metrics)
describe("HTNG / FIAS monitoring dashboards (windowed metrics)", () => {
  const metricsKey = (protocol, range = "24h", facility) =>
    ["integrations", "metrics", { protocol, range, tz_offset_minutes: TZ, ...(facility ? { facility_id: facility } : {}) }];
  const page = (path, protocol, metrics, range = "24h") =>
    atNow(() => H.renderPage(path, [[OVERVIEW_KEY, FX.overview_measured], [metricsKey(protocol, range), metrics],
      [FACILITIES_KEY, facilitiesPage]]));

  test("HTNG KPI cards come from the metrics endpoint, with documented rates", () => {
    const m = FX.metrics_htng;
    assert.equal(m.kpis.inbound_total, 4); // fixture sanity: generated by the real backend
    const { html } = page("/integrations/htng?range=1h", "htng", m, "1h");
    assert.equal(kpi(html, "Total messages"), "4");
    assert.equal(kpi(html, "Successfully processed"), "2");
    assert.equal(kpi(html, "Failed"), "1");
    assert.equal(kpi(html, "Queued"), "1");
    assert.equal(kpi(html, "Success rate"), "66.7%");
    assert.equal(kpi(html, "Average processing time"), "3.0 s");
    assert.equal(kpi(html, "Needed a retry"), "1");
    assert.equal(kpi(html, "Outbound"), "1");
    assert.ok(html.includes("Activity · Last hour"));
    assertNoInternals(html);
    assertNoSensitive(html);
  });

  test("charts render from real series with accessible value tables", () => {
    const { html } = page("/integrations/htng?range=1h", "htng", FX.metrics_htng, "1h");
    for (const chart of ["traffic", "status", "errors", "latency", "types"]) {
      assert.ok(html.includes(`data-chart="${chart}"`), chart);
    }
    // status donut: only statuses that exist, with counts and shares
    assert.ok(html.includes('data-status-share="SUCCEEDED"') && html.includes('data-status-share="DEAD_LETTER"'));
    assert.ok(!html.includes('data-status-share="RETRY_WAIT"'), "no invented category");
    // traffic table: the interval with 3 received / 2 processed is present
    const traffic = html.slice(html.indexOf('data-chart-table="Messages traffic per interval"'));
    assert.match(traffic, /<td>3<\/td><td>2<\/td><td>1<\/td>/);
    assert.ok(html.includes("Rejected by HMS business rule"), "failure reason in business wording");
    assert.ok(html.includes("Based on 2 completed messages"));
    // hidden value tables must sit inside an sr-only wrapper: a bare table ignores
    // the 1px width and widened the page at 390px (browser check)
    assert.ok(!html.includes('<table class="sr-only"') && html.includes('<div class="sr-only" data-chart-table='));
  });

  test("FIAS counts records and keeps unsupported metrics explicitly unavailable", () => {
    const { html } = page("/integrations/fias?range=1h", "fias", FX.metrics_fias, "1h");
    assert.equal(kpi(html, "Total records"), "3");
    assert.equal(kpi(html, "Failed"), "0", "a measured zero stays zero");
    for (const metric of ["connection_history", "ack_statistics", "timeout_statistics", "parse_failures"]) {
      assert.ok(html.includes(`data-unavailable-metric="${metric}"`), metric);
    }
    assert.ok(html.includes("Not implemented (HF-06)"), "ACK / heartbeat never claimed");
    assert.ok(!html.includes('data-status="connected"'), "never shown as connected");
  });

  test("empty window: zero counts, but no fake rates or latency", () => {
    const html = H.renderDashboard({ protocol: "htng", metrics: FX.metrics_empty });
    assert.equal(kpi(html, "Total messages"), "0");
    assert.equal(kpi(html, "Success rate"), "No completed messages");
    assert.equal(kpi(html, "Average processing time"), "No completions");
    assert.ok(html.includes("No messages in this period."));
    assert.ok(html.includes("No message completed processing in this period."));
    assert.ok(!html.includes("0.0%") && !html.includes(">0 ms<"));
  });

  test("unavailable storage: every KPI is unavailable, never zero, and charts say why", () => {
    const html = H.renderDashboard({ protocol: "fias", metrics: FX.metrics_unavailable });
    assert.equal(count(html, 'data-unavailable="true"'), 8);
    assert.ok(html.includes("Charts unavailable") && html.includes("Message storage is not available"));
    assert.ok(!/data-kpi="[^"]+"[\s\S]*?<p class="min-w-0[^"]*"[^>]*>0<\/p>/.test(html));
  });

  test("loading and error states", () => {
    assert.ok(H.renderDashboard({ protocol: "htng", isLoading: true }).includes('data-dashboard-loading="true"'));
    const err = H.renderDashboard({ protocol: "htng", error: new H.ApiError(503, { code: "x", message: "m" }) });
    assert.ok(err.includes("Service unavailable") && err.includes("Retry"));
  });

  test("filters: range and facility go to the server for KPIs, charts and row lists", () => {
    const { html, keys } = atNow(() =>
      H.renderPage(`/integrations/htng?range=7d&facility=${FAC_A}`, [[OVERVIEW_KEY, FX.overview_measured]]));
    const params = (name) => JSON.parse(JSON.stringify(keys.find((k) => k[1] === name)[2]));
    assert.deepEqual(params("metrics"), { protocol: "htng", range: "7d", facility_id: FAC_A, tz_offset_minutes: TZ });
    const since7d = new Date(FIXED_NOW - 7 * 86400 * 1000).toISOString();
    assert.deepEqual(params("messages"), { protocol: "htng", page: 1, page_size: 10, facility_id: FAC_A, received_from: since7d });
    assert.deepEqual(params("dlq"), { protocol: "htng", page: 1, page_size: 5, facility_id: FAC_A, received_from: since7d });
    assert.ok(/aria-pressed="true"[^>]*>7d</.test(html), "selected range is announced");
    for (const r of ["1h", "24h", "30d"]) assert.ok(html.includes(`>${r}</button>`), r);
  });

  test("filters: unknown range falls back; a facility outside the user's scope is never requested", () => {
    const { keys } = atNow(() => H.renderPage(`/integrations/fias?range=90d&facility=${FAC_B}`, [[OVERVIEW_KEY, FX.overview_measured]]));
    const m = keys.find((k) => k[1] === "metrics")[2];
    assert.equal(m.range, "24h");
    assert.equal(m.facility_id, undefined);
  });

  test("responsive grid and dark theme", () => {
    const light = H.renderDashboard({ protocol: "htng", metrics: FX.metrics_htng });
    assert.ok(light.includes("grid-cols-1") && light.includes("min-[420px]:grid-cols-2") && light.includes("xl:grid-cols-4"));
    assert.ok(light.includes("lg:grid-cols-2"), "two-column charts on wide screens, one column below");
    const dark = H.renderDashboard({ protocol: "htng", metrics: FX.metrics_htng, dark: true });
    assert.ok(dark !== light, "dark theme uses the dark surface tokens");
    assert.ok(dark.includes("#1e2233") || dark.includes("rgba(255,255,255,0.07)"));
  });
});
