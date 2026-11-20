# HTNG / FIAS — Integration Dashboard: Browser Visual QA Report (2026-11-20)

Status: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. This QA checks how the
dashboard renders; it says nothing about vendor certification.

## 1. Repository

| Item | Value |
|---|---|
| Path | `ACX_PLATFORM\ACX-Platform` (git root verified) |
| Branch | `feature/htng-fias-on-develop` (not switched); HEAD `46904fd` unchanged |
| Start / end status | 51 entries at start; at end the same 51 plus this report (`?? docs/HTNG_FIAS_DASHBOARD_VISUAL_QA_REPORT.md`). Dashboard edits are inside the already-untracked `frontend/src/features/integrations/`. Nothing staged, committed or pushed |
| Not touched | `HMS-Frontend\ACX-Platform`; backend; `docker-compose.dev.yml` |

## 2. Browser and tooling

| Item | Value |
|---|---|
| Browser | **Microsoft Edge 157.0.4341.60** (installed on the host), headless (`--headless=new`), fresh profile |
| Automation | Chrome DevTools Protocol, driven from Windows PowerShell 5.1 (`System.Net.WebSockets.ClientWebSocket`). **No package was installed.** Playwright, Puppeteer, Selenium and jsdom are not in the repository. |
| What the browser rendered | The **real production build** of the frontend (`vite build`, `VITE_API_BASE_URL=/api/v1`), i.e. the implemented React components, router, auth context, API client and React Query |
| Interactions | Real input events through CDP (`Input.dispatchMouseEvent`, `Input.dispatchKeyEvent`). Date inputs were set through the native value setter plus an `input` event. |
| Scripts (session scratchpad, not in the repo) | `qa/mockserver.cjs`, `qa/cdp.ps1`, `qa/run.ps1`, `qa/summarize.cjs` |

## 3. Isolation and API mocking

* **Mock server.** A disposable `node:20-alpine` container (`acx-qa-mock`), published on
  `127.0.0.1:4317` only. It serves the build and answers `/api/v1/*` from fixtures, and it has no
  outbound code (no proxy, no fetch, no database driver).
  * Overview responses are the **real backend output** captured from the synthetic test
    environment: measured, all-unavailable and tagged-FIAS-links variants.
  * Message and DLQ lists come from a deterministic synthetic set of 57 messages (no guest data).
    It is filtered and paginated server-side with the backend's rules: `page_size` ≤ 100,
    timezone-aware dates, a 31-day window, newest first, and facility scope.
  * `/auth/me` returns a synthetic operator holding only `facility_management:read`.
  * The QA server seeds the token into `localStorage`; no app code was changed for this.
* **Browser.** Every request except `127.0.0.1:4317` was routed to a dead proxy, loopback
  included (`--proxy-server=127.0.0.1:9 --proxy-bypass-list=<-loopback>;127.0.0.1:4317`). The
  real backend (`:8000`) and the dev frontend proxy (`:8080`) were therefore unreachable.
* **Evidence.**
  * The browser's network log shows hosts `127.0.0.1:4317` and `fonts.googleapis.com` only, and
    the fonts request was blocked.
  * The QA server logged 446 requests, with no unmocked API path.
  * The real backend's log shows **no** HTTP requests to integration or auth endpoints during
    QA.
  * No real database was contacted, and no migration or vendor traffic occurred.
* **Disclosure (previous sprint).** The running dev backend container watches the mounted
  `backend/` folder. Its log shows 5 automatic reloads at 21:38–21:47 UTC, triggered by the
  backend file edits of the observability sprint. This sprint changed no backend file, so it
  caused no reloads.

## 4. Coverage

| Pass | What ran |
|---|---|
| Pages × viewports | 5 pages × 4 viewports: 1440×900, 1366×768, 768×1024, 390×844 (20 records), plus full-length captures at desktop and mobile |
| Phone layout | `/about` (an existing HMS page) at 390 as the shell baseline; all 5 pages at 390 with the sidebar collapsed via the existing header toggle |
| Failure states (1440) | normal, null metrics, unobservable link/worker, tagged FIAS links, empty messages, empty DLQ, empty recent list, 401, 403 (overview and messages), 500 (overview and DLQ), network failure (dropped connection), partial (overview OK, messages 503), no permission; plus null metrics at 390 |
| Interactions (1440) | protocol/status/facility selects, dates, invalid range, Reset, Next page, rows per page, keyboard-only select, links overview→HTNG logs, sidebar→FIAS, FIAS→logs, HTNG→DLQ |

Per-record checks (in the browser): document horizontal overflow, elements extending past the
content edge, clipped text, overlapping grid items, table scroll widths, undersized targets, card
count, unavailable markers and zero counts, ready/validated badges, readiness dimensions, rows,
pager text, alerts, redrive buttons, console errors and network hosts.

## 5. Results

### Correct in the browser

* **Overview.**
  * The shared summary and the HTNG and FIAS cards render separately, with all metrics.
  * "Not observable" and "Data unavailable" render as grey dashed "unknown" badges, not red.
  * Vendor validation shows Pending, and every production badge shows Not ready.
  * No `ready`/`validated` badge appears anywhere, in any scenario.
* **HTNG and FIAS.**
  * Each page shows its protocol identity and SOAP/XML or TCP classification.
  * Transport, authentication and processing are shown as separate states.
  * Also present: statistics, recent inbound messages, the failed-message summary, adapter
    requirements, and 8 readiness dimensions.
  * Links go to the filtered logs (`?protocol=htng|fias`) and to the DLQ.
  * FIAS shows "Not observable" when no link is visible. With tagged links it shows
    "Degraded" with per-link Connected/Disconnected.
* **Null metrics.** 19 unavailable markers on the overview (10 on HTNG, 11 on FIAS), and **0**
  zeros rendered.
* **Message Logs.** Each action changed both the URL and the server request exactly:

  | Action | URL | Server request |
  |---|---|---|
  | Protocol | `?protocol=fias` | `protocol=fias` |
  | Status | `&status=SUCCEEDED` | `status=SUCCEEDED` |
  | Facility | `&facility=<A>` | `facility_id=<A>` |
  | Dates | `from` / `to` | `received_from` / `received_to` as UTC instants |
  | Invalid range | alert shown | **0** requests sent |
  | Next page | `?page=2` | `page=2&page_size=20`; pager "Showing 21 to 40 of 57 entries" |
  | Rows per page | `?size=50` | `page_size=50` |
  | Keyboard (Enter / Arrow / Enter) | `protocol=fias` | — |

  The facility options are only the user's facilities. Empty results show "No messages match
  these filters".
* **DLQ.** Shows failure category and code, attempts, last attempt and redrive eligibility
  ("Needs write access" for a read-only role). **No redrive button anywhere** (0 found in every
  record). Empty DLQ shows its empty state.
* **Errors.**
  * 401 signs the user out and redirects to `/login`.
  * 403 shows "Access denied", with no retry button.
  * 500 shows "Could not load this data" with Retry.
  * A dropped connection (after React Query's retries) shows "Service unavailable" with Retry.
  * Partial: the overview renders while recent messages show their own error with Retry.
  * No permission: "Access denied", the sidebar group is hidden, and no integration request is
    sent.
* **Console.** Every error-level entry is either the expected HTTP status of a deliberate
  scenario, the blocked Google Fonts request, or the header's `/notifications` 403 (§6). There
  were no JavaScript exceptions and no React errors.

### Defects found and fixed (all in integration-dashboard files)

| ID | Page / viewport | Defect | Component | Severity | Fix |
|---|---|---|---|---|---|
| D1 | HTNG/FIAS · 768 | "Last received / successful / sent" row went to 3 columns at `md` (768) and overflowed the 528 px content | `views/ProtocolView.tsx` | Minor | 3 columns from `xl` |
| D1b | HTNG/FIAS · 768 | Long certification note overflowed the readiness grid | `components/ReadinessPanel.tsx` | Minor | `minmax(0,1fr)`, `min-w-0`, `break-words` |
| D2 | HTNG/FIAS · all | Readiness reasons rendered as "Dba schema approval pending" | `lib/presentation.ts` | Cosmetic | `reasonLabel()` map; IDs mono, reasons plain |
| D3 | HTNG/FIAS · all | Authentication note ran two sentences together ("no SQL client store in this runtime Rejection…") | `views/ProtocolView.tsx` | Cosmetic | `asSentence()` |
| D4 | HTNG/FIAS · 1440 | Recent and failed tables were wider than the card (1330/1256 vs 1120 px), hiding Error and Redrive eligibility | `components/MessageTables.tsx`, `pages/ProtocolMonitoring.tsx` | Minor | Compact timestamps (full time in tooltip); Protocol/Direction columns dropped in protocol context. Now fits at 1440 |
| D5 | Overview · 1440 / 390 | "DLQ (inbound + outbound)" label wrapped and misaligned its value; readiness labels wrapped away from their badges | `views/OverviewView.tsx` | Cosmetic | "DLQ total" + hint; label+badge pairs grouped |
| D6 | Overview · 768 / 390 | Subtitle cut mid-phrase by the single-line page header | `pages/IntegrationOverview.tsx` | Cosmetic | Shorter subtitle |
| D7 | FIAS (links) · 1440 | "Since" column clipped in the links table | `views/ProtocolView.tsx` | Cosmetic | Compact timestamp; re-checked in the browser |

After the fixes, the full pass was repeated in the browser (pass 2, 44 records), plus a FIAS-links
re-check. One regression test was added (49 tests total).

### Observed, not fixed (outside the dashboard, or by design)

| Observation | Where | Classification |
|---|---|---|
| At 390 px the expanded sidebar (240 px fixed) leaves 150 px of content; the existing `/about` page shows the same | HMS shell `AppLayout` / `AppSidebar` | **Pre-existing shell behaviour.** With the existing toggle collapsed (64 px) every dashboard page lays out correctly at 390 |
| Pagination row (First…Last) does not wrap at 326 px | shared `core/components/TablePagination.tsx` | Pre-existing shared component; mobile only; not changed |
| Badge text is black in light mode for every tone; tone is carried by background and border | global rule in `index.css` (`html:not(.dark) main … color: rgb(0,0,0) !important`) | Pre-existing global style; "unknown" stays grey-dashed, never red |
| Header requests `/notifications` without the `dashboard` grant (403 in console) and shows a fixed "INSP Admin" label | `components/layout/AppHeader.tsx` | Pre-existing; unrelated to the dashboard |
| Message Logs / DLQ tables scroll horizontally inside their container below about 1300 px; the FIAS links table scrolls inside its card | dashboard tables | By design: page never overflows (`docOverflowX=false` everywhere) |
| Fonts render with fallbacks | Google Fonts blocked by the isolation proxy | QA environment only |

No critical or major visual or navigation defect remains.

## 6. Evidence

Screenshots are kept in the session scratchpad, **not committed**:
`C:\Users\Bhuvii\AppData\Local\Temp\claude\d8827ef51840337f\aa708178-8736-4f51-8711-c4cd8145e15f\scratchpad\qa\`
* `shots\` — pass 2, after fixes: 57 PNGs, e.g. `overview-desktop.png`, `htng-desktop-full.png`,
  `fias-tablet.png`, `messages-mobile-collapsed.png`, `dlq-laptop.png`, `state-nulls-overview.png`,
  `state-e401-overview.png`, `state-timeout-overview.png`, `state-fias_links-fias-recheck.png`,
  `flow-messages-filtered.png`, `about-mobile-shell-baseline.png`.
* `shots-pass1\` — pass 1, before fixes: 51 PNGs.
* `results-pass1.json`, `results-pass2.json` — per-record measurements, console output and
  requests.
* `requests.jsonl` — the QA server's request log.

## 7. Tests and build (frontend container, Node 20)

| Check | Baseline | After this sprint |
|---|---|---|
| `node --test` (existing + integrations) | 48/48 | **49/49** (one regression test added for the QA fixes) |
| `tsc -p tsconfig.app.json --noEmit` | 6 errors in 4 files | **same 6, same files**; none in integration code |
| `eslint .` | 3 errors, 7 warnings | **identical list** (10 findings, none in integration code) |
| `vite build` | success | **success** (2618 modules) |
| gitleaks `features/integrations` | clean | clean |

## 8. Remaining limitations

* Edge (Chromium) only; Firefox and Safari were not tested. There is no real device and no
  touch input; mobile is emulated with `mobile: true`.
* The data is mocked. Overview figures (real backend fixture) and the list data (synthetic set)
  are not meant to reconcile with each other.
* The 1440 timeout record reports "not settled" because of the QA wait heuristic during React
  Query's background refetch. The captured final state is correct ("Service unavailable" with
  Retry).
* Dark mode was not inspected.
* Screenshots were reviewed by the QA engineer (AI) for the key pages. Layout properties were
  measured programmatically on every record; not every screenshot was reviewed by eye.

## 9. Files changed this sprint (frontend, integration dashboard only)

`views/ProtocolView.tsx`, `views/OverviewView.tsx`, `components/ReadinessPanel.tsx`,
`components/MessageTables.tsx`, `pages/ProtocolMonitoring.tsx`, `pages/IntegrationOverview.tsx`,
`lib/presentation.ts`, `__tests__/integrations.test.cjs`, all under
`frontend/src/features/integrations/`, plus this report. No shared HMS component, backend file
or configuration was modified.
