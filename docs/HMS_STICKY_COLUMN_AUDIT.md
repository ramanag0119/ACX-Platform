# HMS Global Table Row Background Standardization & Sticky Column Visual Consistency Audit

**Document:** `docs/HMS_STICKY_COLUMN_AUDIT.md`  
**Date:** October 14, 2026  
**Status:** Implemented & Verified  
**Scope:** HMS Data Tables Across All Modules (Bookings, Tickets, Service Tracking, Service Planning, Occupancy, Reports, User Roles, Employees, Job Order, Facilities, Offers, Holidays, Events)

---

## 1. Executive Summary

A comprehensive design system standardization and visual audit was conducted across the Hotel Management System (HMS) application. The primary objectives were:
1. **Standardize Row Backgrounds to Light Lavender:** Standardize the normal data row background color across all applicable HMS data tables using a single, uniform light lavender token (`#f5f4fb` in Light Mode, matched with `#0e1322` in Dark Mode) derived from the HMS design system reference.
2. **Eliminate Zebra Striping & Inconsistent Alternating Rows:** Completely remove alternating white, grey, or blue stripe variations caused by hardcoded JSX ternaries (e.g., `index % 2 === 0 ? "bg-muted/20" : "bg-background"`) and conflicting CSS rules.
3. **Synchronize Sticky First-Column Styling:** Ensure sticky first-column cells (e.g., "Name" in Booking Management, "Room No" in Service Tracking) have 100% opaque fills that match the row background identically in normal, hover, and selected states, eliminating bleed-through and color mismatches during horizontal scrolling.
4. **Preserve Functionality & Visual Hierarchy:** Maintain distinct header styling (`#eae7f6` / `#090d18`), clean row borders, interactive hover states (`#ede9f8` / `#1a2234`), selected states, and full enterprise table functionality (filtering, sorting, pagination, and action handlers).

---

## 2. Root Cause Analysis of Inconsistent Row Backgrounds

Before this refactoring, four distinct mechanisms caused tables to look patchy and striped:

### A. Hardcoded Alternating Row Ternaries in JSX
Throughout feature modules, table row elements had inline template string ternaries based on row index:
- `Bookings.tsx`: `className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} ...`}`
- `Tickets.tsx`: `className={`${index % 2 === 0 ? "bg-card..." : "bg-muted/10..."} ...`}`
- `Reports.tsx`: `className={`${index % 2 === 0 ? "bg-card..." : "bg-muted/10..."} ...`}`
- `ServicePlanning.tsx`: `className={`${index % 2 === 0 ? "bg-muted/20" : "bg-background"} ...`}`
- `Occupancy.tsx`: `className={`${index % 2 === 0 ? "bg-card..." : "bg-muted/20..."} ...`}`
- `Offers.tsx`, `Holidays.tsx`, `Events.tsx`: `className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} ...`}`
- `JobOrder.tsx`, `UserRoles.tsx`, `LimitConfigAlert.tsx`, `Employees.tsx`: similar alternating ternaries.
- `FacilityManagement.tsx` and `ServicesSetup.tsx`: `index % 2 === 0 ? "bg-muted/30" : "bg-muted/20"`.

**Impact:** Every second row was rendered in white or an arbitrary grey/slate tint, creating jarring zebra stripes and conflicting directly with sticky column backgrounds.

### B. Conflicting Global CSS Zebra-Striping Rules
In `frontend/src/index.css`, legacy rules previously forced:
```css
.dark tbody tr:nth-child(even) {
  background-color: hsl(var(--muted) / 0.2);
}
```
**Impact:** Overrode theme tokens in dark mode and caused dark rows to alternate unpredictably.

### C. Mismatched Sticky Column Background vs. Rest of Row
In earlier iterations, the sticky first cell had fixed styling that did not sync with the rest of the row, leading to the sticky cell appearing white while the rest of the row appeared lavender or grey.

---

## 3. Design Token Definition & Visual Reference Alignment

### Reference Color Determination
- **Reference Image Analysis:** The reference image presents a clean, soft, light-lavender tint for normal table rows, distinct from pure white (`#ffffff`) and cold neutral grey.
- **HMS Design System Synchronization:**
  - In `frontend/src/index.css`, the root theme background is `--background: 240 20% 98%` (`#f4f5fa` - soft lavender-tinted background).
  - In `frontend/src/core/styles/surfaceTokens.ts`, light surface cards use `rgba(245, 242, 255, 0.95)`.
  - Harmonizing these references yielded the canonical light lavender table tokens:
    - Normal Row: `#f5f4fb` (`--hms-table-row-bg`)
    - Hover Row: `#ede9f8` (`--hms-table-row-hover-bg`)
    - Selected Row: `#e0e7ff` (`--hms-table-row-selected-bg`)
    - Table Header: `#eae7f6` (`--hms-table-header-bg`)
    - Border: `rgba(99, 102, 241, 0.12)` (`--hms-table-border`)

### Design Token Architecture

#### 1. CSS Variables (`frontend/src/index.css`):
```css
:root {
  --hms-table-row-bg: #f5f4fb;
  --hms-table-row-hover-bg: #ede9f8;
  --hms-table-row-selected-bg: #e0e7ff;
  --hms-table-header-bg: #eae7f6;
  --hms-table-border: rgba(99, 102, 241, 0.12);
}

.dark {
  --hms-table-row-bg: #0e1322;
  --hms-table-row-hover-bg: #1a2234;
  --hms-table-row-selected-bg: #1e293b;
  --hms-table-header-bg: #090d18;
  --hms-table-border: rgba(255, 255, 255, 0.08);
}
```

#### 2. Surface Design Tokens (`frontend/src/core/styles/surfaceTokens.ts`):
```typescript
export interface SurfaceTokens {
  ...
  tableRowBg: string;
  tableRowHoverBg: string;
  tableHeaderBg: string;
  tableBorder: string;
}

export const SURFACE_TOKENS = {
  DARK: {
    ...
    tableRowBg: "#0e1322",
    tableRowHoverBg: "#1a2234",
    tableHeaderBg: "#090d18",
    tableBorder: "rgba(255, 255, 255, 0.08)",
  },
  LIGHT: {
    ...
    tableRowBg: "#f5f4fb",
    tableRowHoverBg: "#ede9f8",
    tableHeaderBg: "#eae7f6",
    tableBorder: "rgba(99, 102, 241, 0.12)",
  },
};
```

#### 3. Core Component Standardization (`frontend/src/components/ui/table.tsx`):
The `TableRow` component applies the standardized token classes by default:
```tsx
const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn(
        "border-b transition-colors bg-[var(--hms-table-row-bg)] hover:bg-[var(--hms-table-row-hover-bg)] data-[state=selected]:bg-[var(--hms-table-row-selected-bg)]",
        className
      )}
      {...props}
    />
  ),
);
```

#### 4. Global CSS Enforcing Uniformity (`frontend/src/index.css`):
```css
/* All normal table rows: ONE uniform, standardized background across the entire table */
.hms-table-sticky-first tbody tr,
.hms-table-sticky-first tbody tr:nth-child(odd),
.hms-table-sticky-first tbody tr:nth-child(even),
.hms-table-sticky-first tbody td {
  background-color: var(--hms-table-row-bg) !important;
  background: var(--hms-table-row-bg) !important;
  border-bottom: 1px solid var(--hms-table-border) !important;
}

/* Sticky first cell: matches the normal row background identically */
.hms-table-sticky-first tbody td:first-child,
.hms-table-sticky-first tbody tr:nth-child(odd) td:first-child,
.hms-table-sticky-first tbody tr:nth-child(even) td:first-child {
  position: sticky !important;
  left: 0 !important;
  z-index: 20 !important;
  background-color: var(--hms-table-row-bg) !important;
  background: var(--hms-table-row-bg) !important;
  border-right: 1px solid var(--hms-table-border) !important;
  border-bottom: 1px solid var(--hms-table-border) !important;
  box-shadow: none !important;
  white-space: nowrap !important;
}

/* Hover state across the row and its sticky first-column cell */
.hms-table-sticky-first tbody tr:hover td,
.hms-table-sticky-first tbody tr:hover td:first-child {
  background-color: var(--hms-table-row-hover-bg) !important;
  background: var(--hms-table-row-hover-bg) !important;
}

/* Selected state across the row and its sticky first-column cell */
.hms-table-sticky-first tbody tr[data-state="selected"] td,
.hms-table-sticky-first tbody tr[data-state="selected"] td:first-child {
  background-color: var(--hms-table-row-selected-bg) !important;
  background: var(--hms-table-row-selected-bg) !important;
}
```

---

## 4. Module-by-Module Refactoring Summary

Every applicable data table across the application was audited and updated to remove hardcoded alternating row classes and utilize the standardized background:

| Module | File | Table / Tab | Standardized Background | Alternating Stripes Removed | Sticky First Column |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Bookings** | `Bookings.tsx` | Main Booking Management Table | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Name) |
| **Tickets** | `Tickets.tsx` | Service Tickets Table | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Service Type) |
| **Services Tracking** | `ServiceTracking.tsx` | Service Categories & Tasks | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Room No) |
| **Service Planning** | `ServicePlanning.tsx` | Service Schedules Table | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Plan) |
| **Occupancy** | `Occupancy.tsx` | Room Occupancy Table | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Room No) |
| **Reports** | `Reports.tsx` | Reports Log Table | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Entity) |
| **Config: Roles** | `UserRoles.tsx` | User Roles & Matrix | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Role Name) |
| **Config: Employees** | `Employees.tsx` | Depts, Functions, Employees | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (ID / Name) |
| **Config: Job Orders** | `JobOrder.tsx` | Rooms & Job Orders | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Job ID) |
| **Config: Alerts** | `LimitConfigAlert.tsx` | Device Limit Alerts | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Parameter) |
| **Config: Facilities** | `FacilityManagement.tsx` | Facility Setup, Amenities, Packages, Rooms | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Org / Amenity) |
| **Config: Services** | `ServicesSetup.tsx` | Room Services, Travel, Business, Food, Maintenance, Sanitation | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Category / Service) |
| **Marketing: Offers** | `Offers.tsx` | Promotional Offers Table | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Offer Name) |
| **Marketing: Holidays** | `Holidays.tsx` | Holiday Calendar Table | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Start Date) |
| **Marketing: Events** | `Events.tsx` | Hotel Events Table | `#f5f4fb` (Light) / `#0e1322` (Dark) | Yes | Yes (Event Name) |

---

## 5. Verification & Test Results

### 1. TypeScript Static Analysis
- **Command:** `npx tsc --noEmit`
- **Result:** `0 errors` (Clean exit code 0)

### 2. ESLint Code Quality Check
- **Command:** `npm run lint`
- **Result:** `0 errors, 0 warnings` (Clean exit code 0)

### 3. Production Build Validation
- **Command:** `npm run build`
- **Result:** Successful production bundle in 11.23s:
  - `dist/index.html` (1.41 kB)
  - `dist/assets/index-BprD3Drw.css` (149.02 kB)
  - `dist/assets/index-DUvJMFGv.js` (1,337.03 kB)

---

## 6. Summary of Files Modified

1. [frontend/src/index.css](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/index.css):
   - Defined design tokens `--hms-table-row-bg`, `--hms-table-row-hover-bg`, `--hms-table-row-selected-bg`, `--hms-table-header-bg`, and `--hms-table-border` for `:root` and `.dark`.
   - Removed `.dark tbody tr:nth-child(even)` zebra-striping rule.
   - Enforced uniform standardized background for all body rows and sticky first-column cells.
   - Preserved distinct header backgrounds, borders, hover, and selected states.
2. [frontend/src/core/styles/surfaceTokens.ts](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/core/styles/surfaceTokens.ts):
   - Added table surface tokens (`tableRowBg`, `tableRowHoverBg`, `tableHeaderBg`, `tableBorder`) to `SurfaceTokens` interface and both `DARK` and `LIGHT` token maps.
3. [frontend/src/components/ui/table.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/components/ui/table.tsx):
   - Bound `TableRow` default classes directly to `bg-[var(--hms-table-row-bg)] hover:bg-[var(--hms-table-row-hover-bg)] data-[state=selected]:bg-[var(--hms-table-row-selected-bg)]`.
4. [frontend/src/features/bookings/pages/Bookings.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/bookings/pages/Bookings.tsx):
   - Removed alternating zebra class ternary from `TableRow`.
5. [frontend/src/features/tickets/pages/Tickets.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/tickets/pages/Tickets.tsx):
   - Removed alternating zebra class ternary from `TableRow`.
6. [frontend/src/features/reports/pages/Reports.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/reports/pages/Reports.tsx):
   - Removed alternating zebra class ternary from `TableRow`.
7. [frontend/src/features/services/pages/ServicePlanning.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/services/pages/ServicePlanning.tsx):
   - Removed alternating zebra class ternary from `TableRow`.
8. [frontend/src/features/occupancy/pages/Occupancy.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/occupancy/pages/Occupancy.tsx):
   - Removed alternating zebra class ternary from `TableRow`.
9. [frontend/src/features/services/pages/ServiceTracking.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/services/pages/ServiceTracking.tsx):
   - Standardized table rows and header presentation.
10. [frontend/src/features/marketing/pages/Offers.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/marketing/pages/Offers.tsx):
    - Replaced alternating row classes with standardized hover class.
11. [frontend/src/features/marketing/pages/Holidays.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/marketing/pages/Holidays.tsx):
    - Replaced alternating row classes with standardized hover class.
12. [frontend/src/features/marketing/pages/Events.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/marketing/pages/Events.tsx):
    - Replaced alternating row classes with standardized hover class.
13. [frontend/src/features/config/pages/JobOrder.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/config/pages/JobOrder.tsx):
    - Removed alternating row classes on rooms and job orders tables.
14. [frontend/src/features/config/pages/UserRoles.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/config/pages/UserRoles.tsx):
    - Removed alternating row classes on roles and permissions matrix tables.
15. [frontend/src/features/config/pages/LimitConfigAlert.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/config/pages/LimitConfigAlert.tsx):
    - Standardized row backgrounds on parameter limits table.
16. [frontend/src/features/config/pages/Employees.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/config/pages/Employees.tsx):
    - Standardized row backgrounds across departments, functions, and employee tables.
17. [frontend/src/features/config/pages/FacilityManagement.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/config/pages/FacilityManagement.tsx):
    - Standardized row backgrounds across all 6 sub-tables (facilities, amenity types, room amenities, packages, sub-packages, room setup).
18. [frontend/src/features/config/pages/ServicesSetup.tsx](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/config/pages/ServicesSetup.tsx):
    - Standardized row backgrounds across all 10 sub-tables (room services, travel desk, business center, food category, food menu, facility services, facility service types, health & fitness, sanitation services, sanitation service types).

---

## 7. Manual Verification Guide

When verifying in the browser at `http://localhost:8081`:
1. **Normal Row Appearance:**
   - Navigate to `/bookings`.
   - Observe that all normal table rows have the exact same soft light lavender background (`#f5f4fb`).
   - Confirm there are **no alternating white/grey stripes**.
2. **Sticky First Column Alignment:**
   - Observe the first column ("Name").
   - Confirm its background matches the row background (`#f5f4fb`) seamlessly.
   - Scroll horizontally to the right:
     - The "Name" column remains fixed on the left.
     - The background is 100% opaque; columns scrolling underneath (Mobile Number, Email, etc.) never show through.
     - The soft boundary shadow and right border maintain clear visual separation.
3. **Interactive States:**
   - Hover over any row: both the sticky cell and all cells in the row shift smoothly to the hover lavender color (`#ede9f8`).
   - Select a row (or check a box): both the sticky cell and all cells in the row shift to the selected tint (`#e0e7ff`).
4. **Header Visual Distinction:**
   - Confirm the header remains distinct (`#eae7f6`) with dark, high-contrast labels and proper border separation.
5. **Cross-Module Verification:**
   - Check `/tickets`, `/reports`, `/services/tracking`, `/config/employees`, `/config/facility-management`, and `/marketing/offers`.
   - Confirm the exact same uniform background and hover styles apply across every module.
6. **Dark Mode Verification:**
   - Switch to dark mode.
   - Confirm table rows use the dark theme token (`#0e1322`), hover uses `#1a2234`, headers use `#090d18`, and sticky columns remain 100% opaque.

---

## 8. Occupancy Dashboard Table Layout Refinement

### A. Problem Analysis
The Occupancy Dashboard table previously suffered from severe congestion, truncated text (such as single-letter room types like "G" or "S"), squished status badges, and lack of horizontal scrolling because of:
1. `Table className="hms-occupancy-table table-fixed min-w-0"` overriding the standard `min-w-max` auto-scrolling container.
2. Fixed percentage `<colgroup>` columns (`"6.3%", "5.3%", "8.2%", "7.2%", ...`) that squeezed all 11 columns to 100% of the screen width regardless of content.
3. Restrictive `.hms-occupancy-table` CSS rules that forced `white-space: normal !important`, `padding: 4px 6px`, `height: 48px`, and 26px squished buttons.

### B. Implemented Improvements
1. **Enabled Standard Horizontal Scrolling:**
   - Removed `table-fixed min-w-0` and percentage `<colgroup>`.
   - Reconnected the table to the shared `Table` component with `.hms-table-sticky-first-wrapper` and `min-w-max`.
   - Added custom `-webkit-scrollbar` styling (6px height, rounded pill thumb) for smooth, elegant horizontal scrolling.
2. **Content-Tailored Column Sizing (~1510px Total Min-Width):**
   - **Room No:** `min-w-[110px]` (Sticky pinned first column with opaque background and subtle 1px border separator).
   - **Room Type:** `min-w-[140px]` (Restored full category names e.g. "Guest Room", "Deluxe Suite").
   - **Building:** `min-w-[130px]` (Removed truncation; full building names visible).
   - **Floor:** `min-w-[110px]`.
   - **Guest Name:** `min-w-[180px]` (Comfortable space for guest names).
   - **Check-In:** `min-w-[140px]` (Clean 2-line date/time stack).
   - **Check-Out:** `min-w-[160px]` (Date/time stack with Overdue badge).
   - **Generate:** `min-w-[130px]` (Pill/button with ample breathing room).
   - **Status:** `min-w-[220px]` (Housekeeping condition pills with clean spacing and wrapping).
   - **Reassign:** `min-w-[100px]` (Accessible action button).
   - **Invoice:** `min-w-[110px]` (Accessible outline action button).
3. **Preserved Sticky Room No Column:**
   - Anchored to `left: 0`, completely opaque with `--hms-table-row-bg` fill, drop shadow, and seamless scrolling underneath.
4. **Removed Restrictive CSS Overrides:**
   - Eliminated cramped padding and forced 48px row heights from `index.css`.
   - Retained `.hms-overdue-tag` and `.hms-muted` styling.

---

## 9. Sticky First-Column Boundary Highlight & Shadow Reduction

### A. Root Cause Analysis
The prominent vertical highlight/shadow along the right edge of sticky first columns across all HMS data tables was produced by:
```css
box-shadow: 3px 0 8px -2px rgba(0, 0, 0, 0.12) !important;
```
applied to:
- `.hms-table-sticky-first thead th:first-child` (top-left sticky corner header)
- `.hms-table-sticky-first tbody td:first-child` (body sticky first-column cells)

This created an 8px blurred dark band that spread over adjacent column cells (e.g. Mobile Number, Room Type), looking like an artificial glowing/shadowed vertical stripe.

### B. Implemented Refinement
1. **Removed the Heavy Box Shadow:**
   Replaced the 8px blur `box-shadow` with `box-shadow: none !important;` on both header (`th:first-child`) and body (`td:first-child`) sticky cells in `frontend/src/index.css`.
2. **Standardized on Subtle, Neutral 1px Border:**
   Retained the clean, thin 1px border:
   ```css
   border-right: 1px solid var(--hms-table-border) !important;
   ```
   where `--hms-table-border` is:
   - Light Mode: `rgba(99, 102, 241, 0.12)` (a delicate, neutral 12% opacity divider)
   - Dark Mode: `rgba(255, 255, 255, 0.08)` (an 8% opacity dark-mode divider)
3. **Preserved Complete Sticky Functionality:**
   - `position: sticky !important` remains anchored to `left: 0`.
   - The cell background remains 100% solid and opaque (`var(--hms-table-row-bg)` / `var(--hms-table-header-bg)`), completely preventing any underlying text or borders from bleeding through during horizontal scroll.
   - Interactive hover and selected row states remain perfectly synchronized.
   - Colspan / empty-state safety rules remain untouched.

### C. Modules & Tables Covered
Because sticky first-column behavior is standardized centrally through the shared `Table` component (`frontend/src/components/ui/table.tsx`) and global rules in `frontend/src/index.css`, this visual refinement automatically applies to all data tables throughout the entire HMS application:
- **Operations:** Bookings (`/bookings`), Occupancy (`/occupancy`), Tickets (`/tickets`)
- **Services:** Service Planning (`/services/planning`), Service Tracking (`/services/tracking`)
- **Reports:** Reporting and Logs (`/reports`)
- **Configuration:** Employees, Facility Management, Job Orders, Parameter Limit Alerts, Services Setup, User Roles & Permissions Matrix
- **Marketing:** Offers, Holidays, Events

