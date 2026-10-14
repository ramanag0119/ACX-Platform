# HMS → OSS/BSS Integration — Executive Summary

**Date:** 2026-10-10 · **For:** project manager and technical lead · **Type:** analysis only. Nothing in the application or the database was changed.

## The short version

- **Today HMS runs on one PostgreSQL database.** The target in the v3 architecture uses **two**: PostgreSQL for the platform (OSS) and MySQL for the hotel business (BSS). **The BSS database, its 54 business tables, the new permission model and the API link to the platform do not exist yet.**
- **A good part of the platform side already exists and can be reused.** The current database already holds almost every table the v3 summary lists for OSS, under names without the `oss_` prefix. The current backend already has about 70 read/write APIs for facilities, rooms, users, roles, devices, alerts and telemetry.
- **The business side is mostly new.** HMS has bookings, check-in/out, service requests, maintenance, offers, events and holidays. It has **no** rates, availability calendar, guest profiles, folios, payments, loyalty, channels or sustainability.
- **One question blocks everything:** is the OSS the separate **FleetExplorer** platform with its own API, or does the current HMS database become the OSS? Neither the repository nor this machine contains a FleetExplorer API, address or contract.

## What was actually found (verified)

| Item | Finding |
|---|---|
| Databases | **1**: PostgreSQL **18.6**, database `hms_db`, schema `public`, 92 tables, Alembic at the latest revision. The docs say version 16 |
| MySQL | **None** on this machine, and no MySQL code in the project |
| TimescaleDB | Not installed |
| Data | **Demo seed data only**: 1 hotel, 24 rooms, 14 devices, 7 bookings, 15 user accounts, 1,805 rows in total |
| Code vs database | **Match exactly** (no missing tables or columns) |
| How HMS reads data | The backend queries **all** data directly, including device and alert data. The v3 rule says platform data must come through an API |
| Security | Permissions are checked per screen module ✔. Data is **not** restricted to the user's own hotel ✘ (no impact today with one hotel). Guest contact details are stored unencrypted and returned by the users API ✘. Two modules (`tickets`, `default_key`) are not checked by the backend ✘ |

## Recommended approach

1. **Keep one HMS backend** and extend it rather than adding new services. It owns the new MySQL BSS database. It reaches platform data **only through an API adapter**, so the answer to the FleetExplorer question changes one component rather than the whole design.
2. **Write the business change and an "event" row together in MySQL.** A background step then calls the platform for side effects such as door keys and room context, with retries. A platform outage never loses a check-in or checkout.
3. **The dashboard reads one summary.** Room and device health come from a BSS snapshot, plus one cached platform call for alerts. Today it sends about 15 requests. Alerts link straight to FleetExplorer.
4. **Fix security before scaling to more hotels:** restrict data to the user's hotels, encrypt guest personal data with an access log, and check every module on the server.

## Decisions needed (top 5)

| # | Decision | Why it matters |
|---|---|---|
| D-01 | Who owns and serves the OSS platform (FleetExplorer vs the current HMS database)? | Everything platform-related depends on it |
| D-07 | Who issues logins/tokens, and how HMS staff are identified | Affects every screen |
| D-02 | Confirm the two-database target. An earlier internal document recommended one PostgreSQL database | Avoids teams building to different targets |
| B-25 | Which of the 54 BSS tables are in the first release (rates? folios? loyalty?) | Most have no screen today; it drives cost |
| D-14 / B-18 | Obtain the machine-readable schema export, and fix the ID-type mismatches in the diagram | The diagram image cannot be built from safely |

## Proposed sequence

| Phase | Outcome |
|---|---|
| 1. Baseline | This audit accepted; a clean test baseline recorded |
| 2. Ownership and schema | Decisions signed; corrected schema export |
| 3. API contracts | Agreed platform API and BSS API definitions |
| 4. Backend build | MySQL BSS, platform adapter, check-in/out, housekeeping and work-order flows, security fixes |
| 5. Screens | Bookings, Occupancy, Dashboard and Service Planning moved to the new sources |
| 6. Testing | Integrity, security, failure and regression testing |
| 7. Go-live readiness | Rollback by feature flag, runbooks, sign-off |

**No effort estimate is given yet.** That needs the D-01 answer, the first-release scope, the team size and the MySQL hosting model.

## What could not be checked

MySQL/BSS (it does not exist here), the FleetExplorer API (no address or contract), other environments' data, and the existing automated tests (they modify the database, which this audit was not allowed to do).

## Documents

[Current state](HMS_DATABASE_CURRENT_STATE.md) · [Schema comparison](HMS_OSS_BSS_SCHEMA_COMPARISON.md) · [Module mapping](HMS_MODULE_DATABASE_MAPPING.md) · [Integration approach and roadmap](HMS_PLATFORM_INTEGRATION_APPROACH.md) · [Gap and blocker register](HMS_GAP_AND_BLOCKER_REGISTER.md) · [Test plan](HMS_INTEGRATION_TEST_PLAN.md) · Consolidated: `HMS_INTEGRATION_ANALYSIS_REPORT.md` / `.pdf`
