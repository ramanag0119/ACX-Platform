# HMS OSS/BSS Ownership Matrix & Integration Boundary Specification
**Document Version:** 1.0.0  
**Date:** 2026-10-26  
**Auditor:** Senior Backend Architect & Database Migration Specialist  
**Architecture Reference:** HMS OSS/BSS v3 Architecture Blueprint  

---

## 1. Domain Ownership Principles

The fundamental architectural principle of HMS v3 is: **Two databases, one unified platform.**

```
+--------------------------------------------------------------------------+
|                       HMS UNIFIED DASHBOARD / STAFF UI                   |
|                       (React 18 + TypeScript + Vite)                    |
+--------------------------------------------------------------------------+
                                     |
              +----------------------+----------------------+
              |                                             |
              v                                             v
+-------------------------------+             +-------------------------------+
|     OSS BACKEND SERVICE       |             |     BSS BACKEND SERVICE       |
|    (FastAPI / Python 3.13)    |             |    (FastAPI / Python 3.13)    |
|   Platform & Infrastructure   |             |    Commercial PMS Operations  |
+-------------------------------+             +-------------------------------+
              |                                             |
              v                                             v
+-------------------------------+             +-------------------------------+
|    POSTGRESQL 18 / TIMESCALE  |             |           MYSQL 8.0           |
|       Database: hms_db        |             |       Database: hms_bss       |
|   Physical Assets, Identity,  |             |   Guests, Rates, Bookings,    |
|   IoT Telemetry, MQTT, Locks  |             |   Folios, Payments, Orders    |
+-------------------------------+             +-------------------------------+
```

### Core Separation Rules:
1. **Rule 1 — Single User Identity (Platform Truth):**  
   `oss_app_user` (PostgreSQL `app_user`) is the single authoritative source of user identity for all platform actors (hotel staff, corporate administrators, maintenance technicians, and registered guests). BSS references `oss_app_user.id` using `varchar(36)`. `bss_users` is deprecated and excluded.
2. **Rule 2 — Telemetry Boundary (Zero Duplication):**  
   All raw time-series sensor readings remain exclusively in `oss_device_stat` (TimescaleDB hypertable in PostgreSQL). BSS **never** ingests or copies raw sensor data. BSS stores only an asynchronous health snapshot in `bss_room_device_registry.last_known_health_status`.
3. **Rule 3 — Stay Lifecycle (Authoritative Commercial Record):**  
   `bss_stays` (MySQL) is the authoritative commercial check-in record owning scheduled check-in/out, actual timestamps, rate plan, and financial folio binding. `oss_stay` (PostgreSQL `stay`) is an auxiliary IoT context record holding `bss_stay_id` used strictly for door lock key validity and smart room automation.
4. **Rule 4 — Module-Aware RBAC:**  
   Roles are defined in `oss_role` with an explicit `module_id`. Permissions in `role_module_permission` / `platform_role_permissions` ensure that HMS hotel operational roles cannot access industrial FleetExplorer features.
5. **Rule 5 — Cross-System Alert Linking:**  
   HMS staff dashboards display alert counts from BSS work orders. When a user inspects an alert, HMS references `oss_device_alert.id` via direct API or URL deep-link to FleetExplorer, rather than duplicating incident payloads.

---

## 2. Authoritative Ownership Matrix

### 2.1 OSS Domain (PostgreSQL 16/18 + TimescaleDB)

| Functional Group | Table Name(s) | Primary Purpose | Authoritative For |
|---|---|---|---|
| **Enterprise & Facility Identity** | `organisation`, `facility` | Organization hierarchy, legal entity, building identity | Building metadata, geographic location, operational timezone |
| **Physical Infrastructure Tree** | `property_chain`, `property_type`, `property`, `amenity_type`, `amenity` | Spatial tree: Campus → Building → Floor → Physical Room Asset | Physical room layout, square footage, hardware boundaries, architectural assets |
| **Physical Room State** | `amenity_condition`, `amenity_condition_status`, `room_status_condition_applicability` | Hardware sensor conditions: Air Quality, HVAC setpoint, DND, Power-save mode | Real-time physical ambient telemetry, physical readiness |
| **Platform Identity & Scoping** | `app_user`, `user_document`, `country`, `facility_user` | Global user directory, login authentication, bcrypt passwords | User login credentials, staff employee IDs, facility assignments |
| **Platform RBAC** | `role`, `user_role`, `department`, `job_function`, `role_module`, `role_module_permission` | Security permissions, system role definitions, feature access grants | Authentication tokens, JWT claims, module access gates |
| **IoT Hardware & Gateways** | `device_type`, `device`, `device_param`, `firmware`, `other_device`, `user_device`, `user_device_acl` | Hardware registry, MAC addresses, device models, serial numbers | Hardware configuration, controller firmware, peripheral devices |
| **IoT Protocols & MQTT** | `mqtt_broker`, `mqtt_topic` | Broker connectivity, TLS certs, pub/sub topic patterns | Inbound telemetry ingestion topics, outbound command topics |
| **Actuators & Device Commands** | `command_type`, `device_command` | Outbound hardware control commands (Lock door, set AC, dim lights) | Actuator queue status, gateway dispatch confirmation |
| **Telemetry & Time-Series** | `device_stat`, `device_health_stat`, `device_current_stat`, `battery_life_stat`, `energy_stat`, `sensor_operation_stat`, `daily_dual_data_point` | Raw timestamped telemetry, battery levels, energy consumption (kWh) | Scientific sensor history, Timescale hypertable partitions |
| **Hardware Alerts & Failures** | `alert_type`, `device_alert`, `incident_status`, `incident_event`, `device_incident`, `incident_history`, `value_alert`, `value_alert_limit_config` | Sensor threshold violations, offline gateways, hardware tampering | Incident lifecycle, hardware diagnostics, telemetry alarms |
| **Smart Locks & Physical Access** | `key_type`, `access_key`, `lock_activity_log`, `user_token` | Digital door locks, NFC credentials, keypad PINs, physical access logs | Door unlock events, NFC card authentication, battery status |
| **Platform Activity & Alerts** | `activity_type`, `activity`, `activity_notifier`, `activity_role_association`, `notification_template`, `notification`, `notification_receiver`, `notification_result` | System-wide audit stream, administrative alerts, email/SMS dispatch | System administrative events, delivery audit trails |
| **Job Execution & Schedulers** | `scheduler_job`, `scheduler_job_execution`, `import_job`, `attachment`, `entity_type` | Recurring cron tasks, batch import jobs, binary attachments | Automation schedules, file asset storage |

---

### 2.2 BSS Domain (MySQL 8.0)

| Functional Group | Table Name(s) | Primary Purpose | Authoritative For |
|---|---|---|---|
| **Commercial Hotel Structure** | `bss_brands`, `bss_properties`, `bss_floors`, `bss_room_types` | Commercial brand portfolio, marketing property names, room classes | Public hotel brand, commercial descriptions, room capacity |
| **Sellable Room Inventory** | `bss_rooms`, `bss_room_status_history` | Sellable rooms, housekeeping lifecycle (Clean, Dirty, Inspected, OOO) | Room availability, commercial readiness, room assignments |
| **Device Health Snapshot** | `bss_room_device_registry` | Cached snapshot of device health per room (Rule 2) | Fast staff UI dashboard rendering without cross-DB queries |
| **Commercial Guests & Accounts** | `bss_guests`, `bss_corporate_accounts` | Guest profile, VIP tier, total stays, lifetime spend, B2B company accounts | Commercial customer relationship, credit limits, negotiated rates |
| **Protected Guest PII** | `bss_guest_pii`, `bss_pii_access_log` | Encrypted guest PII (phone, email, passport, home address), access audit log | Compliance with privacy regulations (GDPR, DPDP), PII access audit |
| **Rates, Yield & Distribution** | `bss_rate_plans`, `bss_rate_plan_room_types`, `bss_seasonal_rates`, `bss_cancellation_policies`, `bss_packages` | Pricing matrices, seasonal multipliers, refund policies, package bundles | Base room rates, peak season pricing overrides, cancellation fees |
| **Distribution Channels & OTAs** | `bss_booking_channels`, `bss_ota_channels`, `bss_property_channel_configs`, `bss_channel_inbound_reservations` | Channel manager, Agoda/Booking.com sync, inbound reservation logs | External channel mappings, inbound XML/JSON reservation payloads |
| **Inventory Availability** | `bss_availability_calendar`, `bss_group_blocks` | Daily inventory count, booked count, group room block cutoff dates | Real-time booking engine availability, block hold releases |
| **Reservations & Booking Lifecycle**| `bss_reservations`, `bss_reservation_rooms`, `bss_reservation_guests` | Central booking records, confirmation numbers, deposit status | Commercial reservation lifecycle (Booked, Confirmed, Cancelled, No-Show) |
| **Commercial Stays & Check-In** | `bss_stays`, `bss_automation_events` | Authoritative guest check-in/out record, checkout-to-cleaning automation | Actual check-in/out timestamps, folio linkage, automation audit |
| **Smart Mobile Keys (Commercial)** | `bss_digital_keys`, `bss_smart_access_log`, `bss_iot_control_events` | Guest app mobile key pass, guest-facing access history, in-app room control | Mobile key validity period, guest-initiated room adjustment requests |
| **Housekeeping & Work Orders** | `bss_housekeeping_tasks`, `bss_maintenance_work_orders`, `bss_room_conditions` | Room cleaning queues, repair tickets, room inspection condition reports | Staff work assignments, maintenance vendor costs, cleaning status |
| **Guest Services & Dining** | `bss_service_requests`, `bss_orders` | Guest service orders (laundry, extra bed, room dining, spa) | Billable guest service orders, fulfillment tracking |
| **Billing, Folios & Revenue** | `bss_folios`, `bss_folio_charges`, `bss_payments`, `bss_invoices`, `bss_revenue_categories`, `bss_payment_methods_config` | Guest folios, line-item charges, tax calculation, payment transactions | Financial accounts receivable, payment reconciliation, tax invoices |
| **Hotel Events & Banquets** | `bss_events`, `bss_public_holidays` | Banquets, conferences, weddings, hotel holiday calendar | Event space reservations, banquet billing, holiday pricing triggers |
| **Loyalty & Rewards** | `bss_loyalty_programs`, `bss_loyalty_tiers`, `bss_loyalty_accounts`, `bss_loyalty_transactions` | Points accrual, tier benefits (Silver, Gold, Platinum), redemptions | Loyalty points ledger, member reward balances |
| **Marketing & Promotions** | `bss_promotions`, `bss_promo_redemptions`, `bss_campaigns`, `bss_campaign_enrollments` | Commercial promo codes, campaign enrollments, discount redemption limits | Marketing campaigns, promo discount validation |
| **Sustainability & Carbon** | `measurement_units`, `emission_factors`, `carbon_calculations`, `cm_points_ledger` | Energy-to-carbon calculation, green stay eco-points ledger | Sustainability reporting, ESG compliance, eco-loyalty credits |

---

## 3. Physical Room vs. Sellable Room: Definitive Resolution

One of the most critical ambiguities in the legacy HMS schema is the dual representation of rooms.

| Dimension | OSS Physical Asset (`oss_amenity` / `amenity`) | BSS Sellable Room (`bss_rooms`) |
|---|---|---|
| **What it represents** | The physical built space, electrical circuit, door lock, hardware boundary | The commercial inventory unit that can be booked, priced, sold, and billed |
| **Lifecycle** | Permanent architectural existence (demolition or remodeling changes it) | Highly dynamic operational status (Clean, Dirty, Out of Order, Inspected) |
| **Database Engine** | PostgreSQL (`hms_db`) | MySQL (`hms_bss`) |
| **Primary Key** | `id` (UUID as text/UUID) | `room_id` (bigint auto-increment + `room_uuid` char(36)) |
| **Room Type / Category** | `amenity_type_id` (e.g. "Room", "Suite", "Corridor", "Lobby") | `room_type_id` (`bss_room_types`: Deluxe King, Presidential Suite) |
| **IoT Association** | Direct foreign key: `device.amenity_id -> amenity.id` | Indirect: `bss_room_device_registry.oss_device_id` |
| **Pricing & Rate Plans** | Unaware of money or pricing | Linked to `bss_rate_plans` through `room_type_id` |
| **Housekeeping** | Unaware of linen, cleaning, or turn-down | Core driver of `bss_housekeeping_tasks` |
| **Integration Link** | Authoritative target of `bss_rooms.oss_asset_id` | References `oss_asset_id -> oss_amenity.id` |

**Architectural Contract:**  
1. When a hotel configures a new room, an `oss_amenity` row is created in OSS representing the physical space.  
2. Simultaneously, a corresponding `bss_rooms` record is created in BSS with `oss_asset_id = oss_amenity.id`.  
3. FleetExplorer manages hardware attached to `oss_amenity.id`.  
4. HMS staff manage reservations, cleaning, and check-in against `bss_rooms.room_id`.

---

## 4. Cross-System Integration Bridge Reference Columns

No cross-database foreign keys exist. All connections are maintained via verified reference columns validated through application services:

```
+------------------------------------+          +------------------------------------+
|            BSS (MySQL)             |          |          OSS (PostgreSQL)          |
+------------------------------------+          +------------------------------------+
| bss_properties                     |          | oss_facility                       |
|   oss_facility_id (char 36) -------+--------->|   id (uuid)                        |
|                                    |          |                                    |
| bss_rooms                          |          | oss_amenity                        |
|   oss_asset_id (char 36) ----------+--------->|   id (uuid)                        |
|                                    |          |                                    |
| bss_room_device_registry           |          | oss_device                         |
|   oss_device_id (char 36) ---------+--------->|   id (uuid)                        |
|                                    |          |                                    |
| bss_maintenance_work_orders        |          | oss_device_alert                   |
|   oss_alert_id (char 36) ----------+--------->|   id (uuid)                        |
|                                    |          |                                    |
| bss_room_conditions                |          | oss_device_alert                   |
|   oss_device_alert_id (char 36) ---+--------->|   id (uuid)                        |
|                                    |          |                                    |
| bss_housekeeping_tasks             |          | oss_app_user                       |
|   assigned_to (varchar 36) --------+--------->|   id (uuid)                        |
|                                    |          |                                    |
| bss_audit_trail / pii_access_log   |          | oss_app_user                       |
|   accessed_by (varchar 36) --------+--------->|   id (uuid)                        |
|                                    |          |                                    |
| bss_stays                          |          | oss_stay                           |
|   stay_id (bigint) <---------------+----------+-- bss_stay_id (bigint/char 36)     |
+------------------------------------+          +------------------------------------+
```

### Integration Guarantees & Constraints:
1. **Identifier Formatting:** All UUIDs passed across the bridge are formatted as lowercase 36-character strings (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
2. **Referential Integrity Validation:** The backend validation layer (`app/services/bridge/`) verifies that referenced OSS entities exist prior to persisting BSS records.
3. **Graceful Degradation:** If OSS is temporarily unreachable when fetching device status for room cards, BSS serves the cached `last_known_health_status` from `bss_room_device_registry`.
4. **Idempotency:** Cross-system commands (e.g. Issuing digital lock PIN, dispatching maintenance order from alert) require a unique `idempotency_key` to prevent duplicate actions during network retries.

---

## 5. Architectural Decisions & Open Items

| # | Topic | Dilemma | Resolution / Architectural Ruling |
|---|---|---|---|
| **D1** | Single User vs Dual User | Early diagram included `bss_users`. Architecture summary Rule 1 deprecated it. | **Adopt Rule 1.** Unified user record in `oss_app_user`. Zero implementation of `bss_users`. BSS references `oss_app_user.id`. |
| **D2** | Room Entity Distinction | Current schema only has `amenity`. | **Dual model approved.** Retain `amenity` for physical/IoT assets; introduce `bss_rooms` for commercial sellable inventory with `oss_asset_id` link. |
| **D3** | Reservation Lifecycle Transition | Current HMS Bookings page reads directly from `stay`. | **Expand-and-contract.** Create `bss_reservations`. During transition, auto-generate a lightweight reservation for existing stays. Update frontend Bookings to read `bss_reservations`. |
| **D4** | Promotions vs Promo Codes | Live DB has `promo_code` (3 rows) used by Offers screen. v3 proposes `bss_promotions`. | Keep `promo_code` for operational in-stay discounts (food & beverage, spa); implement `bss_promotions` for commercial room booking discount codes. |
| **D5** | Occasions vs Public Holidays | Live DB has `occasion` (4 rows) used by Holidays screen. v3 proposes `bss_public_holidays`. | Retain `occasion` for property events/celebrations; implement `bss_public_holidays` for automated rate yield seasonal pricing triggers. |
| **D6** | 65 Unaccounted HMS Tables | Diagram omitted 65 tables currently in PostgreSQL `hms_db`. | Retain all 65 tables in PostgreSQL. They belong to the OSS platform subsystem. Zero tables dropped. |
