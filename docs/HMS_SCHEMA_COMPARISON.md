# HMS Schema Comparison: Live HMS vs. Proposed v3 Architecture
**Document Version:** 1.0.0  
**Date:** 2026-10-26  
**Auditor:** Senior Backend Architect & Database Migration Specialist  
**Reference Materials:**
1. Live PostgreSQL `hms_db` (94 tables, Alembic head `0e2687233b59`)
2. `HMS SCHEMA V2 (1).png` (dbdiagram.io schema export, 88 tables)
3. `HMS_OSS_BSS_v3_Architecture_Summary (1).docx` (Executive architecture briefing)

---

## 1. Classification Methodology & Overview

To reconcile the actual running system with the proposed v3 architecture without causing application regression or data loss, every table has been analyzed and categorized into one of eight distinct classifications:

1. **Existing & Correctly Aligned [ALIGNED]:** Table exists in the live database, matches OSS platform ownership, and requires zero structural changes.
2. **Existing but Requiring Modification [EXTEND]:** Table exists in the live database but requires additional reference columns (`bss_*_id`, `module_id`, etc.) to bridge with BSS.
3. **Missing from the Database [MISSING]:** Proposed BSS or Platform table that does not physically exist anywhere in the live database. Must be created in MySQL (or PostgreSQL staging).
4. **Existing but Assigned to Wrong Logical Owner / Hybrid [HYBRID]:** Table currently holds business data in PostgreSQL, but its long-term domain owner is BSS (e.g. `stay`, `invoice`, `promo_code`). Must be preserved during expand-and-contract phase.
5. **Duplicate / Overlapping Responsibility [OVERLAP]:** Tables representing the same real-world concept with different scopes (e.g. `amenity` as a physical room vs `bss_rooms` as a sellable inventory unit).
6. **Deprecated / Legacy [DEPRECATED]:** Proposed or existing table identified for deprecation in v3 (e.g. `bss_users`, which v3 explicitly replaces with `oss_app_user`).
7. **Requires Explicit Architecture Decision [DECISION]:** Discrepancies where business consensus is required before schema changes can be applied (e.g. `occasion` vs `bss_public_holidays`, `promo_code` vs `bss_promotions`).
8. **Retained HMS Operational Subsystem [RETAINED_HMS]:** 65 live HMS tables omitted from the v3 diagram that remain load-bearing for notifications, activity logs, scheduler, and hardware telemetry.

---

## 2. Table-by-Table Alignment & Comparison Matrix

### 2.1 Space & Infrastructure (Physical Building vs Business Properties)

| Live HMS Table | Proposed v3 Table | Classification | Owner | Evidence & Structural Changes Required | Migration Risk & Backward Compatibility |
|---|---|---|---|---|---|
| `organisation` | `oss_organisation` | ALIGNED | OSS | Table exists (1 row). Diagram adds prefix `oss_`. Maintain existing table without renaming in PostgreSQL. | Low. Zero data loss. Code continues to use `organisation`. |
| `facility` | `oss_facility` | ALIGNED | OSS | Table exists (1 row, "Ikanos Grand Chennai"). Referenced by `bss_properties.oss_facility_id`. | Low. Add `oss_facility_id` in BSS property. |
| `property` | `oss_property` | ALIGNED | OSS | Table exists (4 rows). Represents building blocks/wings. | Low. |
| `property_chain`| `oss_property_chain`| ALIGNED | OSS | Table exists (3 rows). | Low. |
| `property_type` | `oss_property_type` | ALIGNED | OSS | Table exists (1 row). | Low. |
| `amenity` | `oss_amenity` | OVERLAP | OSS | Table exists (27 rows). Represents rooms, suites, and public spaces as physical hardware assets. In v3, sellable room inventory is extracted into `bss_rooms`. `amenity.name` is varchar(100) in live DB (diagram typo was `varchar(6)`). | Medium. Ensure `bss_rooms.oss_asset_id` references `amenity.id`. Do NOT drop `amenity`. |
| `amenity_type` | `oss_amenity_type` | ALIGNED | OSS | Table exists (5 rows: Room, Suite, etc.). | Low. |
| `amenity_condition`| `oss_amenity_condition` | ALIGNED | OSS | Table exists (7 rows). Physical sensor parameters (temperature, humidity, noise). | Low. |
| `amenity_condition_status`| `oss_amenity_condition_status` | ALIGNED | OSS | Table exists (6 rows). Real-time condition readings. | Low. |
| *None* | `bss_brands` | MISSING | BSS | Missing from DB. Hotel brand registry (e.g. "Ikanos Hotels & Resorts"). | High priority for BSS. Created in MySQL. |
| *None* | `bss_properties` | MISSING | BSS | Missing from DB. Hotel commercial property entity. Contains `oss_facility_id` bridge column. | High priority for BSS. Created in MySQL. |
| *None* | `bss_floors` | MISSING | BSS | Missing from DB. Floor directory within property. | Created in MySQL. |
| *None* | `bss_room_types` | MISSING | BSS | Missing from DB. Commercial room categories (Deluxe King, Executive Suite) with base occupancy. | Created in MySQL. Bridges commercial rates to room inventory. |
| *None* | `bss_rooms` | MISSING | BSS | Missing from DB. Sellable room inventory, room number, floor, room type, housekeeping status, occupancy state. Contains `oss_asset_id` pointing to `amenity.id`. | Critical BSS table. Resolves the physical asset vs sellable room conflict. |
| *None* | `bss_room_status_history` | MISSING | BSS | Missing from DB. Historical audit of room status changes (Clean, Dirty, Inspected, Out of Order). | Created in MySQL. |
| *None* | `bss_room_device_registry` | MISSING | BSS | Missing from DB. Contains `oss_device_id` and cached `last_known_health_status` snapshot. Enforces Rule 2 (no telemetry duplicate). | Created in MySQL. Serves dashboard device health widgets without PostgreSQL hit. |

---

### 2.2 People, Identity & RBAC

| Live HMS Table | Proposed v3 Table | Classification | Owner | Evidence & Structural Changes Required | Migration Risk & Backward Compatibility |
|---|---|---|---|---|---|
| `app_user` | `oss_app_user` | EXTEND | OSS | Table exists (13 rows). Live DB uses `user_name` for login and bcrypt hash. Proposed v3 adds: `user_type` (varchar 20), `is_hms_staff` (int, default 1), and `bss_legacy_user_id` (bigint). | Low. Additive migration to PostgreSQL `app_user`. Zero breaking changes. |
| `role` | `oss_role` | EXTEND | OSS | Table exists (7 rows). Proposed v3 adds `module_id` to enforce module-aware RBAC (Rule 4). | Low. Additive column `module_id`. |
| `user_role` | `oss_user_role` | EXTEND | OSS | Table exists (13 rows). Live DB has composite PK `(facility_id, app_user_id, role_id)`. Diagram adds surrogate `id`, `module_id`, `granted_by`, `granted_at`. | Medium. Maintain composite PK or add surrogate ID smoothly. |
| `department` | `oss_department` | ALIGNED | OSS | Table exists (5 rows). | Low. |
| `job_function`| `oss_job_function`| ALIGNED | OSS | Table exists (5 rows). | Low. |
| `country` | `oss_country` | ALIGNED | OSS | Table exists (239 rows). ISO reference data. | Low. |
| `user_document`| `oss_user_document`| ALIGNED | OSS | Table exists (3 rows). | Low. |
| `role_module` | `platform_modules` | DECISION | Platform | Live DB has `role_module` (18 modules, smallint ID). Proposed v3 introduces `platform_modules`. | Maintain `role_module` as source of truth for the 18 active modules; map codes directly. |
| `role_module_permission`| `platform_permissions` / `platform_role_permissions` | DECISION | Platform | Live DB has `role_module_permission` (65 grants). Proposed v3 splits into catalog `platform_permissions` and bridge `platform_role_permissions`. | Low. Existing RBAC checks in `app/api/deps.py` continue to read `role_module_permission`. |
| *None* | `bss_users` | DEPRECATED | - | Proposed in early v2 diagram, but v3 Rule 1 explicitly states: "oss_app_user is the single user record. bss_users is deprecated and will be removed." | **DO NOT IMPLEMENT.** Use `oss_app_user` directly across BSS. |
| *None* | `bss_roles` | DEPRECATED | - | Duplicates platform roles. v3 unifies roles under `oss_role` with module scoping. | Defer or keep only for commercial channel staff if required. |
| *None* | `bss_audit_trail`| MISSING | BSS | Missing from DB. Tracks business entity mutations, referencing `oss_app_user.id`. | Created in MySQL. |
| *None* | `bss_pii_access_log`| MISSING | BSS | Missing from DB. Tracks who accessed guest PII (`bss_guest_pii`), referencing `oss_app_user.id`. | Critical compliance table. Created in MySQL. |

---

### 2.3 Guest Management & Commercial Bookings

| Live HMS Table | Proposed v3 Table | Classification | Owner | Evidence & Structural Changes Required | Migration Risk & Backward Compatibility |
|---|---|---|---|---|---|
| *None* | `bss_guests` | MISSING | BSS | Missing from DB. Commercial guest profile (loyalty tier, VIP flag, total stays, lifetime spend). | High priority. Created in MySQL. |
| *None* | `bss_guest_pii` | MISSING | BSS | Missing from DB. Encrypted/isolated PII (first_name, last_name, email, phone, passport, address). Enforces GDPR/data privacy. | High priority. Created in MySQL. |
| *None* | `bss_corporate_accounts` | MISSING | BSS | Missing from DB. B2B corporate contracts, credit limits, negotiated rates. | Created in MySQL. |
| *None* | `bss_reservations` | MISSING | BSS | Missing from DB. Primary booking entity (confirmation code, channel, dates, deposit, total amount, status). | **Critical Architectural Gap.** Frontend Bookings page currently reads `stay`. Must transition to `bss_reservations`. |
| *None* | `bss_reservation_rooms` | MISSING | BSS | Missing from DB. Specific room types and allocations assigned to a reservation. Contains `oss_room_allocation_id`. | Created in MySQL. |
| *None* | `bss_reservation_guests` | MISSING | BSS | Missing from DB. Guests associated with each reservation room. | Created in MySQL. |
| *None* | `bss_group_blocks` | MISSING | BSS | Missing from DB. Corporate / event room blocks and cutoff dates. | Created in MySQL. |
| *None* | `bss_availability_calendar` | MISSING | BSS | Missing from DB. Daily room type inventory counts, booked count, out-of-order count. | High performance value for booking engine. |
| `stay` | `bss_stays` / `oss_stay` | HYBRID | BSS / OSS | Table exists in PostgreSQL (6 rows). In live HMS, `stay` serves both commercial check-in and IoT access control. In v3: `bss_stays` is the authoritative check-in record; `oss_stay` is a lightweight IoT context record carrying `bss_stay_id`. | High. Add `bss_stay_id` to PostgreSQL `stay`. Create `bss_stays` in MySQL. Sync actual check-in/out across the bridge. |
| `room_allocation` | `oss_room_allocation` | EXTEND | OSS | Table exists (5 rows). Add `bss_reservation_room_id` (varchar 36) to link physical room assignment to BSS booking. | Low. Additive migration in PostgreSQL. |
| `stay_user` | `oss_stay_user` | EXTEND | OSS | Table exists (8 rows). Add `bss_stay_id` to link occupants to BSS stay. | Low. Additive migration in PostgreSQL. |

---

### 2.4 Pricing, Distribution & Marketing

| Live HMS Table | Proposed v3 Table | Classification | Owner | Evidence & Structural Changes Required | Migration Risk & Backward Compatibility |
|---|---|---|---|---|---|
| *None* | `bss_rate_plans` | MISSING | BSS | Missing from DB. BAR, Non-Refundable, Corporate, Breakfast-Inclusive rate plans. | Created in MySQL. |
| *None* | `bss_rate_plan_room_types` | MISSING | BSS | Missing from DB. Rate plan binding per room type. | Created in MySQL. |
| *None* | `bss_seasonal_rates` | MISSING | BSS | Missing from DB. Date-range pricing multipliers (Peak, Christmas, Monsoon). | Created in MySQL. |
| *None* | `bss_cancellation_policies` | MISSING | BSS | Missing from DB. Cancellation rules and fee structures. | Created in MySQL. |
| *None* | `bss_booking_channels` | MISSING | BSS | Missing from DB. Direct web, walk-in, corporate channels. | Created in MySQL. |
| *None* | `bss_ota_channels` | MISSING | BSS | Missing from DB. Agoda, Booking.com, Expedia integrations. | Created in MySQL. |
| *None* | `bss_property_channel_configs` | MISSING | BSS | Missing from DB. Channel credentials and rate mapping per property. | Created in MySQL. |
| *None* | `bss_channel_inbound_reservations` | MISSING | BSS | Missing from DB. Inbound webhook audit log from OTAs. | Created in MySQL. |
| `promo_code` | `bss_promotions` | DECISION | BSS | Table exists in PostgreSQL (3 rows). Used by frontend "Offers" screen. Proposed v3 has `bss_promotions` with 8 extra fields (eligibility, stackable, guest limits). | Keep `promo_code` for in-stay service offers; create `bss_promotions` in MySQL for commercial booking discounts. |
| `promo_code_amenity`| `bss_promo_redemptions` | DECISION | BSS | Table exists (8 rows). | Redemptions tracked in BSS. |
| `occasion` | `bss_public_holidays` | DECISION | BSS | Table exists in PostgreSQL (4 rows). Used by frontend "Holidays" screen. Proposed v3 has `bss_public_holidays`. | Retain `occasion` in PostgreSQL for facility operations; bridge to `bss_public_holidays` for rate calculations. |
| `package` / `sub_package` | `bss_packages` | HYBRID | OSS / BSS | Tables exist in PostgreSQL (8 rows). Packages bundle room and amenities. | Preserve in PostgreSQL; mirror pricing rules to BSS. |

---

### 2.5 Revenue, Billing & Folios

| Live HMS Table | Proposed v3 Table | Classification | Owner | Evidence & Structural Changes Required | Migration Risk & Backward Compatibility |
|---|---|---|---|---|---|
| `invoice` | `oss_invoice` / `bss_invoices` | HYBRID | BSS / OSS | Table exists in PostgreSQL (2 rows). In v3, billing is strictly owned by BSS. Live `invoice` table needs `bss_invoice_id` to link with commercial invoices. | Low. Add `bss_invoice_id` to PostgreSQL `invoice`. Create full folio/invoice subsystem in BSS. |
| *None* | `bss_folios` | MISSING | BSS | Missing from DB. Master billing folio per reservation/stay. | High priority. Created in MySQL. |
| *None* | `bss_folio_charges` | MISSING | BSS | Missing from DB. Itemized room charges, tax, food, laundry, services. | Created in MySQL. |
| *None* | `bss_payments` | MISSING | BSS | Missing from DB. Payment transactions (Credit Card, UPI, Cash, Wire). | Created in MySQL. |
| *None* | `bss_orders` | MISSING | BSS | Missing from DB. Point of sale (POS) restaurant & spa orders. | Created in MySQL. |
| *None* | `bss_revenue_categories` | MISSING | BSS | Missing from DB. General ledger revenue categorization (Room, F&B, Wellness). | Created in MySQL. |
| *None* | `bss_payment_methods_config` | MISSING | BSS | Missing from DB. Merchant account and gateway configuration. | Created in MySQL. |

---

### 2.6 Operations, Housekeeping, Services & Maintenance

| Live HMS Table | Proposed v3 Table | Classification | Owner | Evidence & Structural Changes Required | Migration Risk & Backward Compatibility |
|---|---|---|---|---|---|
| *None* | `bss_housekeeping_tasks` | MISSING | BSS | Missing from DB. Housekeeping work management. Points to `oss_amenity.id` and `assigned_to` (`oss_app_user.id`). | High priority for operations. Created in MySQL. |
| `service_request` | `oss_service_request` / `bss_service_requests` | HYBRID | BSS / OSS | Table exists in PostgreSQL (7 rows). Proposed v3 adds `bss_service_request_id` to PostgreSQL table. Commercial service management moves to BSS. | Add `bss_service_request_id` (varchar 36) to PostgreSQL `service_request`. |
| `maintenance_request`| `oss_maintenance_request` / `bss_maintenance_work_orders` | HYBRID | BSS / OSS | Table exists in PostgreSQL (4 rows). In v3, repairs and vendor work orders belong to BSS, while hardware diagnostics remain in OSS. `bss_maintenance_work_orders` carries `oss_alert_id`. | Add `bss_work_order_id` to PostgreSQL `maintenance_request`. |
| *None* | `bss_room_conditions` | MISSING | BSS | Missing from DB. Captures room readiness discrepancies, referencing `oss_device_alert_id`. | Created in MySQL. |
| *None* | `bss_automation_events` | MISSING | BSS | Missing from DB. Audits automated triggers (e.g. Check-out -> Housekeeping task created). | Created in MySQL. |
| *None* | `bss_events` | MISSING | BSS | Missing from DB. Conference, banquet and wedding event bookings. | Created in MySQL. |

---

### 2.7 IoT, Devices, Telemetry & Smart Access (Strict OSS Ownership)

| Live HMS Table | Proposed v3 Table | Classification | Owner | Evidence & Structural Changes Required | Migration Risk & Backward Compatibility |
|---|---|---|---|---|---|
| `device` | `oss_device` | ALIGNED | OSS | Table exists (14 rows). Hardware identity, MAC, firmware, room binding. | Rule 2: Strictly retained in PostgreSQL. Never duplicated in BSS. |
| `device_type` | `oss_device_type` | ALIGNED | OSS | Table exists (4 rows). | Retained in PostgreSQL. |
| `device_command`| `oss_device_command`| ALIGNED | OSS | Table exists (7 rows). Outbound MQTT commands. | Retained in PostgreSQL. |
| `device_alert` | `oss_device_alert` | ALIGNED | OSS | Table exists (9 rows). Referenced by BSS work orders. | Retained in PostgreSQL. |
| `device_stat` | `oss_device_stat` | EXTEND | OSS | Table exists (504 rows). In v3, add `unit_id` pointing to `measurement_units`. Ready for TimescaleDB hypertable. | Additive migration to add `unit_id`. |
| `mqtt_broker` | `oss_mqtt_broker` | ALIGNED | OSS | Table exists (1 row). | Retained in PostgreSQL. |
| `mqtt_topic` | `oss_mqtt_topic` | ALIGNED | OSS | Table exists (12 rows). | Retained in PostgreSQL. |
| `access_key` | `oss_access_key` | EXTEND | OSS | Table exists (5 rows). Smart lock keys. Proposed v3 adds `bss_digital_key_id` (bigint). | Additive migration in PostgreSQL. |
| `lock_activity_log`| `oss_lock_activity_log`| ALIGNED | OSS | Table exists (5 rows). Lock open/close events. | Retained in PostgreSQL. |
| *None* | `bss_digital_keys` | MISSING | BSS | Missing from DB. Commercial guest digital key issuance and mobile check-in passes. | Created in MySQL. |
| *None* | `bss_smart_access_log` | MISSING | BSS | Missing from DB. Guest-facing smart access audit log. | Created in MySQL. |
| *None* | `bss_iot_control_events` | MISSING | BSS | Missing from DB. Guest app IoT commands (AC adjust, lights) before passing to OSS. | Created in MySQL. |

---

### 2.8 Loyalty, Campaigns & Sustainability

| Live HMS Table | Proposed v3 Table | Classification | Owner | Evidence & Structural Changes Required | Migration Risk & Backward Compatibility |
|---|---|---|---|---|---|
| *None* | `bss_loyalty_programs` | MISSING | BSS | Missing from DB. Hotel loyalty tier definitions. | Created in MySQL. |
| *None* | `bss_loyalty_tiers` | MISSING | BSS | Missing from DB. Silver, Gold, Platinum tiers and multiplier benefits. | Created in MySQL. |
| *None* | `bss_loyalty_accounts` | MISSING | BSS | Missing from DB. Member points balance and tier status per guest. | Created in MySQL. |
| *None* | `bss_loyalty_transactions` | MISSING | BSS | Missing from DB. Points earned from stays/dining and redemptions. | Created in MySQL. |
| *None* | `bss_campaigns` | MISSING | BSS | Missing from DB. Marketing campaigns. | Created in MySQL. |
| *None* | `bss_campaign_enrollments`| MISSING | BSS | Missing from DB. Guest enrollment in marketing campaigns. | Created in MySQL. |
| *None* | `measurement_units` | MISSING | OSS / Shared | Missing from DB. Standard units (kWh, °C, Litres, kgCO2e). | High value for telemetry normalization. |
| *None* | `emission_factors` | MISSING | Sustainability| Missing from DB. Grid emission factors per region/year. | Created in BSS / Sustainability module. |
| *None* | `carbon_calculations` | MISSING | Sustainability| Missing from DB. Per-stay or per-room carbon footprint. | Created in BSS / Sustainability module. |
| *None* | `cm_points_ledger` | MISSING | Sustainability| Missing from DB. Carbon offset / green stay loyalty points. | Created in BSS / Sustainability module. |

---

## 3. Retained HMS Operational Subsystem (65 Tables)

The v3 architecture diagram focuses heavily on the new BSS layer and simplifies the OSS domain to 27 tables. However, a forensic inspection of the codebase reveals that **65 existing HMS tables** are actively utilized by backend services and APIs:

1. **Hardware & Configuration:** `device_param`, `command_type`, `firmware`, `other_device`, `user_device`, `user_device_acl`.
2. **Telemetry Aggregations:** `sensor_operation_stat`, `device_health_stat`, `device_current_stat`, `battery_life_stat`, `energy_stat`, `daily_dual_data_point`.
3. **Alerts & Incidents:** `alert_type`, `incident_status`, `incident_event`, `device_incident`, `incident_history`, `value_alert`, `value_alert_limit_config`.
4. **Maintenance & Job Orders:** `maintenance_request_amenity`, `maintenance_request_assignee`, `maintenance_request_recurrence`, `job_order`, `job_order_amenity`, `job_order_device`.
5. **Activity & Notifications:** `activity_type`, `activity`, `activity_notifier`, `activity_role_association`, `notification_template`, `notification`, `notification_receiver`, `notification_result`.
6. **Background Tasks & System Administration:** `scheduler_job`, `scheduler_job_execution`, `import_job`, `attachment`, `entity_type`, `user_token`.
7. **Service Catalogs & Add-ons:** `service_category`, `service_category_item`, `service_type`, `service_status`, `service_request_item`, `room_service_request`, `room_service_request_item`.

**Architectural Ruling:** In accordance with Non-Negotiable Rule 14, **NONE of these 65 tables will be dropped, altered destructively, or abandoned**. They remain in PostgreSQL `hms_db` as vital components of the OSS platform.
