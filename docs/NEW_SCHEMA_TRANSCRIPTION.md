# New Platform Schema — Table Transcription

**Date:** 2026-10-10
**Source:** the dbdiagram.io schema image shared on 2026-10-10 (10429 × 7287 px), read in zoomed tiles.
**Companion to:** [HMS_NEW_SCHEMA_INTEGRATION_APPROACH.md](HMS_NEW_SCHEMA_INTEGRATION_APPROACH.md)

This is a reading of an image, not an export. Flags: **PK** key icon, **FK** link icon, **UQ** unique icon, **NN** not null.
FK targets are recorded only where the relationship line could be followed. "likely" means the line was ambiguous.

**Known gaps.** These cannot be read from the image; the source `.dbml` export resolves them:

- `bss_promotions`: 8 column names are covered by the `bss_roles` box. Their types still show.
- `bss_maintenance_work_orders`: about 7 trailing rows are covered by the `cm_points_ledger` box.
- `bss_room_device_registry`: a trailing column (e.g. `updated_at`) may be hidden.
- `bss_service_requests`: the header is partly hidden. The name is the best reading; the columns are clear.
- `oss_amenity.name` reads as `varchar(6)`. Confirm it against the source.

---

## OSS tables (27) — existing HMS tables

### oss_access_key

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| device_id | varchar(36) | FK |
| stay_id | varchar(36) | FK -> oss_stay.id |
| app_key | varchar(10) | NN |
| keypad_key | varchar(10) | NN |
| key_type | int | |
| maintenance_request_id | varchar(36) | |
| bss_digital_key_id | bigint | |
| status | int | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_amenity

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| name | varchar(6) | NN |
| amenity_type_id | varchar(36) | FK, NN |
| facility_id | varchar(36) | FK |
| property_chain_id | varchar(36) | FK |
| package_id | varchar(36) | FK |
| parent_amenity_id | varchar(36) | FK (self-ref -> oss_amenity.id, line visible) |
| status | int | |
| is_dnd | int | |
| power_save_mode | int | |
| metadata | json | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

Note: name type reads "varchar(6)" — verify, may be a rendering of a larger length.

### oss_amenity_type

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| name | varchar(50) | NN |
| facility_id | varchar(36) | FK -> oss_facility.id (likely) |
| amenity_category | varchar(20) | |
| status | int | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_app_user

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| user_uid | varchar(72) | UQ |
| first_name | varchar(100) | NN |
| last_name | varchar(100) | |
| email | varchar(256) | |
| phone_number | varchar(15) | NN |
| gender | varchar(10) | |
| dob | date | |
| is_staff | int | |
| is_child | int | |
| nationality | int | |
| marital_status | varchar(20) | |
| job_function_id | varchar(36) | |
| department_id | varchar(36) | FK |
| emp_id | varchar(20) | |
| user_name | varchar(100) | |
| password_hash | varchar(100) | |
| supervisor | varchar(36) | FK (likely self-reference to oss_app_user.id; line loops back on the right side — not fully certain) |
| metadata | json | |
| user_type | varchar(20) | |
| is_hms_staff | int | NN |
| bss_legacy_user_id | bigint | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_department

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| facility_id | varchar(36) | FK -> oss_facility.id (likely) |
| department_name | varchar(255) | NN |
| department_key | varchar(20) | |
| status | int | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_device

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| device_uid | varchar(16) | UQ |
| device_name | varchar(100) | |
| device_type | int | FK, NN |
| facility_id | varchar(36) | FK, NN |
| amenity_id | varchar(36) | FK, NN (-> oss_amenity.id, line visible) |
| parent_device_id | varchar(36) | FK (self-ref -> oss_device.id, line visible) |
| health_status | varchar(10) | |
| device_config_status | varchar(30) | |
| current_firmware_version | varchar(36) | |
| is_power_off | boolean | |
| installed_on | datetime | |
| operational_mode | int | |
| metadata | json | |
| status | int | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_device_alert

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| device_id | varchar(36) | FK, NN (-> oss_device.id) |
| amenity_id | varchar(36) | FK, NN (target not clearly traceable; likely oss_amenity) |
| alert_type | int | NN |
| alert_severity | varchar(10) | |
| alert_data | json | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_device_command

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| device_id | varchar(36) | FK, NN (-> oss_device.id) |
| command_type | int | NN |
| command_data | json | NN |
| processing_status | varchar(20) | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_device_stat

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| device_id | varchar(36) | FK, NN (-> oss_device.id) |
| timestamp | datetime | NN |
| device_param_id | integer | NN |
| device_param_value | varchar(500) | NN |
| unit_id | int | FK |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_device_type

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| name | varchar(50) | NN |
| device_short_code | varchar(10) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_facility

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| org_id | varchar(36) | FK, NN -> oss_organisation.id |
| facility_uid | varchar(3) | UQ, NN |
| name | varchar(100) | NN |
| currency_id | int | |
| city | varchar(100) | |
| state | varchar(100) | |
| guest_rooms | integer | |
| email | varchar(500) | |
| cloud_details | json | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_invoice

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| invoice_number | varchar(20) | UQ, NN |
| stay_id | varchar(36) | FK -> oss_stay.id |
| facility_id | varchar(36) | FK |
| billing_user_id | varchar(36) | FK |
| billing_user_name | varchar(100) | |
| billing_address | varchar(500) | |
| net_amount | decimal(10,2) | |
| total_tax | decimal(10,2) | |
| total_amount | decimal(10,2) | |
| bss_invoice_id | bigint | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_lock_activity_log

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| timestamp | datetime | NN |
| app_user_id | varchar(36) | FK |
| event | varchar(10) | |
| unlock_mode | varchar(10) | |
| lock_id | varchar(36) | FK |
| amenity_id | varchar(36) | FK |
| stay_id | varchar(36) | FK -> oss_stay.id |
| facility_id | varchar(36) | FK |
| key_type | int | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_maintenance_request

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| facility_id | varchar(36) | FK |
| maintenance_request_type | varchar(20) | |
| maintenance_start_date | date | |
| maintenance_end_date | date | |
| department_id | varchar(36) | FK |
| category_id | varchar(36) | |
| is_recurring | int | |
| under_maintenance | boolean | |
| maintenance_request_status | int | |
| bss_work_order_id | bigint | |
| status | int | |
| created_by | varchar(36) | |
| updated_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_mqtt_broker

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| facility_id | varchar(36) | FK -> oss_facility.id (likely) |
| broker_name | varchar(50) | NN |
| broker_ip | varchar(40) | |
| broker_port | integer | |
| broker_user_name | varchar(50) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_mqtt_topic

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| mqtt_broker_id | varchar(36) | FK |
| device_id | varchar(36) | FK (-> oss_device.id) |
| topic_name | varchar(50) | |
| topic_type | varchar(30) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_organisation

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| name | varchar(100) | NN |
| org_uid | varchar(3) | UQ, NN |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_package

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| facility_id | varchar(36) | FK |
| name | varchar(100) | NN |
| description | text | |
| amenity_type | varchar(36) | FK |
| is_sub_package | boolean | |
| status | int | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_property

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| property_name | varchar(200) | NN |
| property_type_id | varchar(36) | FK |
| facility_id | varchar(36) | FK |
| status | int | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_property_chain

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| level_one_id | varchar(36) | FK |
| level_two_id | varchar(36) | FK |
| level_three_id | varchar(36) | FK |
| facility_id | varchar(36) | FK |
| status | int | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_property_type

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| property_type_name | varchar(200) | NN |
| levels | int | |
| facility_id | varchar(36) | FK -> oss_facility.id (likely; line traced from oss_facility.id) |
| status | int | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_role

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| facility_id | varchar(36) | FK -> oss_facility.id (likely) |
| name | varchar(50) | NN |
| role_type | varchar(20) | NN |
| module_id | bigint | FK (target not traced; probably platform_modules.id) |
| status | int | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_room_allocation

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| stay_id | varchar(36) | FK -> oss_stay.id |
| room_id | varchar(36) | FK |
| package_id | varchar(36) | FK |
| bss_reservation_room_id | bigint | |
| status | int | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_service_request

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| facility_id | varchar(36) | FK |
| stay_id | varchar(36) | FK -> oss_stay.id |
| amenity_id | varchar(36) | FK |
| app_user_id | varchar(36) | FK |
| service_type | int | |
| ref_number | varchar(20) | |
| description | text | |
| assigned_to | varchar(36) | FK |
| department_id | varchar(36) | FK |
| category_id | varchar(36) | |
| net_amount | decimal(10,2) | |
| total_amount | decimal(10,2) | |
| bss_service_request_id | bigint | |
| status | int | |
| request_source | varchar(20) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_stay

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| internal_stay_ref_number | varchar(100) | UQ |
| external_stay_ref_number | varchar(100) | |
| booking_user_id | varchar(36) | FK |
| no_of_rooms | int | |
| no_of_guests | int | |
| expected_checkin_time | datetime | |
| expected_checkout_time | datetime | |
| actual_checkin_time | datetime | |
| actual_checkout_time | datetime | |
| document_approval_status | varchar(20) | |
| status | varchar(30) | |
| request_source | varchar(20) | |
| gst | varchar(20) | |
| bss_stay_id | bigint | FK |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

Relationships: oss_stay.id is the target of the varchar stay_id FKs in oss_room_allocation, oss_stay_user, oss_access_key, oss_lock_activity_log, oss_service_request, oss_invoice (line from id runs right to the shared vertical bus feeding those stay_id columns).

### oss_stay_user

| column | type | flags |
|---|---|---|
| id | varchar(36) | PK |
| stay_id | varchar(36) | FK -> oss_stay.id |
| app_user_id | varchar(36) | FK |
| room_id | varchar(36) | FK |
| bss_stay_id | bigint | |
| is_key_required | int | |
| status | int | |
| created_by | varchar(36) | |
| created_on | datetime | NN |
| updated_on | datetime | NN |

### oss_user_role

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| facility_id | varchar(36) | FK |
| app_user_id | varchar(36) | FK |
| role_id | varchar(36) | FK |
| module_id | bigint | FK |
| granted_by | varchar(36) | |
| granted_at | datetime | NN |
| created_on | datetime | NN |
| updated_on | datetime | NN |

---

## Platform RBAC (3)

### platform_modules

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| module_code | varchar(30) | UQ, NN |
| module_name | varchar(100) | NN |
| description | text | |
| is_active | int | NN |
| created_at | datetime | NN |

### platform_permissions

| column | type | flags |
|---|---|---|
| permission_id | bigint | PK |
| module_id | bigint | FK, NN -> platform_modules.id |
| resource | varchar(60) | NN |
| action | varchar(30) | NN |
| description | varchar(255) | |
| created_at | datetime | NN |

### platform_role_permissions

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| role_id | varchar(36) | FK, NN |
| permission_id | bigint | FK, NN |
| facility_id | varchar(36) | FK |
| granted_by | varchar(36) | FK |
| granted_at | datetime | NN |

---

## BSS tables (54)

### bss_audit_trail

| column | type | flags |
|---|---|---|
| audit_id | bigint | PK |
| table_name | varchar(80) | NN |
| record_id | bigint | NN |
| action | varchar(15) | NN |
| old_values | json | |
| new_values | json | |
| changed_fields | json | |
| user_id | varchar(36) | FK |
| ip_address | varchar(45) | |
| request_id | char(36) | |
| performed_at | datetime | NN |

### bss_automation_events

| column | type | flags |
|---|---|---|
| event_id | bigint | PK |
| trigger_type | varchar(50) | NN |
| source_table | varchar(60) | NN |
| source_id | bigint | NN |
| target_table | varchar(60) | NN |
| target_id | bigint | |
| property_id | bigint | FK, NN (target not traced) |
| triggered_at | datetime | NN |
| processed_at | datetime | |
| status | varchar(20) | |
| error_message | text | |

### bss_availability_calendar

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| property_id | bigint | FK, NN |
| room_type_id | bigint | FK, NN |
| stay_date | date | NN |
| total_inventory | int | NN |
| rooms_blocked | int | NN |
| rooms_sold | int | NN |
| rooms_available | int | |
| is_stop_sell | int | NN |
| updated_at | datetime | NN |

### bss_booking_channels

| column | type | flags |
|---|---|---|
| channel_id | bigint | PK |
| channel_code | varchar(20) | UQ, NN |
| channel_name | varchar(100) | NN |
| channel_type | varchar(30) | |
| commission_rate | decimal(5,4) | NN |
| is_active | int | NN |
| created_at | datetime | NN |

### bss_brands

| column | type | flags |
|---|---|---|
| brand_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| brand_code | varchar(20) | UQ, NN |
| brand_name | varchar(100) | NN |
| base_currency | char(3) | NN |
| is_active | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_campaign_enrollments

| column | type | flags |
|---|---|---|
| enrollment_id | bigint | PK |
| campaign_id | bigint | FK, NN (likely bss_campaigns.campaign_id; not traced) |
| guest_id | bigint | FK, NN (likely bss_guests.guest_id; not traced) |
| status | varchar(20) | |
| sent_at | datetime | |
| opened_at | datetime | |
| clicked_at | datetime | |
| converted_at | datetime | |
| event_timestamps | json | |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_campaigns

| column | type | flags |
|---|---|---|
| campaign_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK (target off-tile) |
| campaign_name | varchar(150) | NN |
| campaign_type | varchar(30) | |
| subject | varchar(255) | |
| template_code | varchar(60) | |
| linked_promo_id | bigint | FK (target off-tile) |
| target_segment_json | json | |
| scheduled_at | datetime | |
| status | varchar(20) | |
| total_targeted | int | NN |
| total_sent | int | NN |
| total_delivered | int | NN |
| total_opened | int | NN |
| total_clicked | int | NN |
| total_converted | int | NN |
| sent_at | datetime | |
| completed_at | datetime | |
| created_at | datetime | NN |
| created_by | varchar(36) | |

### bss_cancellation_policies

| column | type | flags |
|---|---|---|
| policy_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK |
| policy_name | varchar(100) | NN |
| policy_code | varchar(30) | NN |
| policy_type | varchar(30) | |
| penalty_type | varchar(20) | |
| penalty_value | decimal(10,4) | NN |
| hours_before_checkin | int | NN |
| is_active | int | NN |
| created_at | datetime | NN |

### bss_channel_inbound_reservations

Complete (finished from tiles_extra/r4_c5).
| column | type | flags |
|---|---|---|
| inbound_id | bigint | PK |
| property_id | bigint | FK, NN |
| ota_channel_id | bigint | FK, NN |
| channel_booking_ref | varchar(150) | NN |
| message_type | varchar(10) | |
| raw_payload | json | NN |
| received_at | datetime | NN |
| processing_status | varchar(20) | |
| reservation_id | bigint | FK (line runs up the same x~707 trunk that feeds the reservation_id FKs from bss_reservations, so probably -> bss_reservations.reservation_id) |
| created_at | datetime | NN |

### bss_corporate_accounts

| column | type | flags |
|---|---|---|
| account_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| account_code | varchar(20) | UQ, NN |
| account_name | varchar(150) | NN |
| account_type | varchar(30) | |
| credit_limit | decimal(15,4) | |
| payment_terms_days | int | NN |
| contract_start_date | date | |
| contract_end_date | date | |
| is_active | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_digital_keys

| column | type | flags |
|---|---|---|
| key_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| stay_id | bigint | FK, NN |
| room_id | bigint | FK, NN |
| guest_id | bigint | FK, NN |
| key_type | varchar(20) | |
| key_credential_hash | varchar(255) | NN |
| valid_from | datetime | NN |
| valid_until | datetime | NN |
| is_active | int | NN |
| oss_device_id | varchar(36) | FK |
| issued_at | datetime | NN |
| deactivated_at | datetime | |

### bss_events

| column | type | flags |
|---|---|---|
| event_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN (target not traced) |
| event_name | varchar(150) | NN |
| event_type | varchar(30) | |
| venue_room_id | bigint | FK (target not traced) |
| organiser_name | varchar(150) | NN |
| organiser_phone | varchar(20) | |
| corporate_account_id | bigint | FK -> bss_corporate_accounts.account_id |
| expected_attendees | int | NN |
| start_datetime | datetime | NN |
| end_datetime | datetime | NN |
| status | varchar(20) | NN |
| cancellation_reason | text | |
| cancelled_at | datetime | |
| folio_id | bigint | FK (target not traced) |
| total_amount | decimal(15,4) | NN |
| notes | text | |
| created_by | varchar(36) | |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_floors

| column | type | flags |
|---|---|---|
| floor_id | bigint | PK |
| property_id | bigint | FK, NN |
| floor_number | int | NN |
| floor_name | varchar(50) | NN |
| is_active | int | NN |
| created_at | datetime | NN |

### bss_folio_charges

| column | type | flags |
|---|---|---|
| charge_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| folio_id | bigint | FK, NN |
| rev_cat_id | bigint | FK, NN |
| order_id | bigint | FK -> bss_orders.order_id |
| charge_type | varchar(30) | |
| description | varchar(255) | NN |
| charge_date | date | NN |
| gross_amount | decimal(15,4) | NN |
| tax_amount | decimal(15,4) | NN |
| net_amount | decimal(15,4) | NN |
| is_void | int | NN |
| created_at | datetime | NN |

### bss_folios

| column | type | flags |
|---|---|---|
| folio_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| stay_id | bigint | FK |
| reservation_id | bigint | FK, NN |
| guest_id | bigint | FK, NN |
| folio_number | varchar(20) | UQ, NN |
| folio_type | varchar(20) | |
| status | varchar(20) | |
| total_charges | decimal(15,4) | NN |
| total_credits | decimal(15,4) | NN |
| total_payments | decimal(15,4) | NN |
| balance | decimal(15,4) | |
| currency_code | char(3) | NN |
| opened_at | datetime | NN |
| closed_at | datetime | |
| settled_at | datetime | |

Relationships: bss_folios.folio_id is the target of bss_orders.folio_id, bss_payments.folio_id and bss_invoices.folio_id (shared vertical bus).

### bss_group_blocks

| column | type | flags |
|---|---|---|
| block_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN (target off-tile) |
| block_name | varchar(150) | NN |
| corporate_account_id | bigint | FK -> bss_corporate_accounts.account_id |
| room_type_id | bigint | FK, NN (target off-tile) |
| rate_plan_id | bigint | FK, NN (target off-tile) |
| rooms_blocked | int | NN |
| rooms_picked_up | int | NN |
| arrival_date | date | NN |
| departure_date | date | NN |
| cutoff_date | date | |
| status | varchar(20) | |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_guest_pii

| column | type | flags |
|---|---|---|
| pii_id | bigint | PK |
| guest_id | bigint | FK, UQ, NN -> bss_guests.guest_id (one-to-one) |
| email_encrypted | text | |
| email_hash | char(64) | |
| phone_encrypted | text | |
| date_of_birth_encrypted | text | |
| passport_number_encrypted | text | |
| passport_country | char(2) | |
| national_id_encrypted | text | |
| marketing_consent | int | NN |
| data_processing_consent | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_guests

| column | type | flags |
|---|---|---|
| guest_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| guest_code | varchar(20) | UQ, NN |
| title | varchar(10) | |
| first_name | varchar(100) | NN |
| last_name | varchar(100) | NN |
| nationality_code | char(2) | |
| vip_status | varchar(20) | |
| total_stays | int | NN |
| total_nights | int | NN |
| total_revenue_lifetime | decimal(15,4) | NN |
| last_stay_date | date | |
| is_blacklisted | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_housekeeping_tasks

| column | type | flags |
|---|---|---|
| task_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| room_id | bigint | FK, NN |
| stay_id | bigint | FK |
| task_type | varchar(30) | |
| priority | varchar(10) | |
| status | varchar(20) | |
| assigned_to | varchar(36) | FK |
| scheduled_for_date | date | NN |
| started_at | datetime | |
| completed_at | datetime | |
| created_at | datetime | NN |

### bss_invoices

Complete (merged r5_c7 + tiles_extra r6_c7).
| column | type | flags |
|---|---|---|
| invoice_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| folio_id | bigint | FK -> bss_folios.folio_id |
| guest_id | bigint | FK |
| corporate_account_id | bigint | FK |
| invoice_number | varchar(30) | UQ, NN |
| invoice_type | varchar(20) | |
| status | varchar(20) | |
| subtotal | decimal(15,4) | NN |
| tax_amount | decimal(15,4) | NN |
| total_amount | decimal(15,4) | NN |
| issue_date | date | NN |
| due_date | date | |
| billing_name | varchar(150) | NN |
| created_at | datetime | NN |

(tiles_extra r7_c7 and r7_c8 are blank apart from the dbdiagram.io watermark.)

### bss_iot_control_events

| column | type | flags |
|---|---|---|
| event_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| stay_id | bigint | FK |
| room_id | bigint | FK, NN |
| oss_device_id | varchar(36) | FK, NN |
| registry_id | bigint | FK |
| command_type | varchar(30) | |
| command_payload | json | NN |
| initiated_by | varchar(20) | |
| status | varchar(20) | |
| created_at | datetime | NN |
| executed_at | datetime | |

### bss_loyalty_accounts

| column | type | flags |
|---|---|---|
| loyalty_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| guest_id | bigint | FK, NN |
| program_id | bigint | FK, NN |
| tier_id | bigint | FK, NN |
| member_number | varchar(20) | UQ, NN |
| status | varchar(20) | |
| points_balance | int | NN |
| points_lifetime | int | NN |
| stays_lifetime | int | NN |
| revenue_lifetime | decimal(15,4) | NN |
| enrolled_at | date | NN |
| tier_review_date | date | |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_loyalty_programs

| column | type | flags |
|---|---|---|
| program_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| brand_id | bigint | FK, NN -> bss_brands.brand_id |
| program_name | varchar(100) | NN |
| program_code | varchar(20) | UQ, NN |
| earn_rate | decimal(8,4) | NN |
| redemption_rate | decimal(8,4) | NN |
| is_active | int | NN |
| created_at | datetime | NN |

### bss_loyalty_tiers

| column | type | flags |
|---|---|---|
| tier_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| program_id | bigint | FK, NN -> bss_loyalty_programs.program_id |
| tier_name | varchar(60) | NN |
| tier_code | varchar(20) | NN |
| tier_level | int | NN |
| min_points_to_qualify | int | NN |
| min_nights_to_qualify | int | NN |
| points_earn_multiplier | decimal(5,2) | NN |
| early_checkin_enabled | int | NN |
| late_checkout_enabled | int | NN |
| complimentary_upgrade | int | NN |
| is_active | int | NN |
| created_at | datetime | NN |

### bss_loyalty_transactions

| column | type | flags |
|---|---|---|
| transaction_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| loyalty_id | bigint | FK, NN |
| stay_id | bigint | FK |
| transaction_type | varchar(30) | |
| points | int | NN |
| balance_after | int | NN |
| description | varchar(255) | NN |
| expiry_date | date | |
| created_at | datetime | NN |

### bss_maintenance_work_orders

PARTIAL — the lower rows are hidden behind the overlapping cm_points_ledger box.
| column | type | flags |
|---|---|---|
| work_order_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| room_id | bigint | FK |
| origin | varchar(30) | |
| oss_alert_id | varchar(36) | FK |
| service_request_id | bigint | FK -> bss_service_requests.request_id |
| category | varchar(30) | |
| priority | varchar(10) | |
| status | varchar(20) | |
| description | text | NN |
| resolution_notes | text | |
| assigned_to | varchar(36) | FK |
| assigned_at | datetime | |
| scheduled_date | date | |
| started_at | datetime | |
| completed_at (partly obscured) | datetime | |
| (about 7 more rows hidden; visible type fragments: "...)", "...)", "...N", "...e", "...e", "...N", "...N") | ? | ? |

### bss_orders

| column | type | flags |
|---|---|---|
| order_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| stay_id | bigint | FK, NN |
| room_id | bigint | FK, NN |
| folio_id | bigint | FK -> bss_folios.folio_id |
| order_type | varchar(20) | |
| status | varchar(20) | |
| placed_at | datetime | NN |
| promised_at | datetime | |
| delivered_at | datetime | |
| total_amount | decimal(15,4) | NN |
| is_charged_to_folio | int | NN |
| created_at | datetime | NN |

### bss_ota_channels

| column | type | flags |
|---|---|---|
| ota_channel_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| channel_name | varchar(100) | NN |
| channel_code | varchar(30) | UQ, NN |
| channel_type | varchar(30) | |
| is_active | int | NN |
| created_at | datetime | NN |

### bss_packages

| column | type | flags |
|---|---|---|
| package_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK |
| rate_plan_id | bigint | FK |
| package_code | varchar(30) | NN |
| package_name | varchar(150) | NN |
| package_type | varchar(30) | |
| valid_from | date | |
| valid_to | date | |
| min_nights | int | NN |
| package_price | decimal(15,4) | |
| is_active | int | NN |
| created_at | datetime | NN |

### bss_payment_methods_config

| column | type | flags |
|---|---|---|
| method_id | bigint | PK |
| method_code | varchar(30) | UQ, NN |
| method_name | varchar(100) | NN |
| method_type | varchar(30) | |
| is_active | int | NN |
| created_at | datetime | NN |

### bss_payments

| column | type | flags |
|---|---|---|
| payment_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| folio_id | bigint | FK -> bss_folios.folio_id, NN |
| property_id | bigint | FK, NN |
| guest_id | bigint | FK, NN |
| payment_method_id | bigint | FK, NN |
| amount | decimal(15,4) | NN |
| currency_code | char(3) | NN |
| status | varchar(20) | |
| card_last_four | char(4) | |
| gateway_name | varchar(50) | |
| gateway_transaction_id | varchar(150) | |
| payment_datetime | datetime | NN |
| created_at | datetime | NN |

### bss_pii_access_log

| column | type | flags |
|---|---|---|
| log_id | bigint | PK |
| accessed_by | varchar(36) | FK, NN |
| access_type | varchar(20) | |
| entity_type | varchar(60) | NN |
| entity_id | bigint | NN |
| fields_accessed | json | NN |
| access_purpose | varchar(255) | NN |
| ip_address | varchar(45) | |
| accessed_at | datetime | NN |

### bss_promo_redemptions

| column | type | flags |
|---|---|---|
| redemption_id | bigint | PK |
| promo_id | bigint | FK, NN (target off-tile) |
| reservation_id | bigint | FK, NN (target off-tile) |
| guest_id | bigint | FK, NN (target not traced; likely bss_guests) |
| discount_applied | decimal(15,4) | NN |
| currency_code | char(3) | NN |
| redeemed_at | datetime | NN |

### bss_promotions

NOTE: the bss_roles box is drawn on top of this table in the image; 8 column names (between min_booking_amount and is_active) are hidden. Only their types/flags are visible on the right edge.
| column | type | flags |
|---|---|---|
| promo_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK |
| promo_code | varchar(50) | UQ, NN |
| promo_name | varchar(150) | NN |
| promo_type | varchar(30) | |
| discount_value | decimal(10,4) | NN |
| description | text | |
| terms_and_conditions | text | |
| valid_from | date | NN |
| valid_to | date | NN |
| min_stay_nights | int | NN |
| min_booking_amount | decimal(15,4) | NN |
| applicable_room_types (name partly hidden) | json | |
| (hidden) | json | |
| (hidden) | json | |
| (hidden) | int | |
| (hidden) | int | NN |
| (hidden) | int | NN |
| (hidden) | bigint | |
| requires_corporate_account (name partly hidden) | int | NN |
| is_active | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |
| deleted_at | datetime | |

(Confirmed via r6_c2: deleted_at is the last column. The hidden column names are obscured by bss_roles in the source image itself and cannot be recovered from any tile.)

### bss_properties

| column | type | flags |
|---|---|---|
| property_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| brand_id | bigint | FK, NN -> bss_brands.brand_id |
| property_code | varchar(20) | UQ, NN |
| property_name | varchar(150) | NN |
| property_type | varchar(20) | |
| star_rating | decimal(2,1) | |
| city | varchar(100) | NN |
| country_code | char(2) | NN |
| timezone | varchar(60) | NN |
| base_currency | char(3) | NN |
| check_in_time | varchar(10) | NN |
| check_out_time | varchar(10) | NN |
| total_rooms | int | NN |
| oss_facility_id | varchar(36) | FK -> oss_facility.id (likely) |
| is_active | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_property_channel_configs

| column | type | flags |
|---|---|---|
| config_id | bigint | PK |
| property_id | bigint | FK, NN |
| ota_channel_id | bigint | FK, NN |
| channel_property_id | varchar(100) | |
| api_key_encrypted | text | |
| commission_rate | decimal(5,4) | NN |
| is_active | int | NN |
| last_sync_at | datetime | |
| created_at | datetime | NN |

### bss_public_holidays

| column | type | flags |
|---|---|---|
| holiday_id | bigint | PK |
| property_id | bigint | FK (target not traced; likely bss_properties) |
| holiday_name | varchar(150) | NN |
| holiday_date | date | NN |
| holiday_type | varchar(30) | |
| country_code | char(2) | NN |
| source | varchar(60) | |
| created_at | datetime | NN |

### bss_rate_plan_room_types

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| rate_plan_id | bigint | FK, NN |
| room_type_id | bigint | FK, NN |
| base_rate | decimal(15,4) | NN |
| extra_adult_rate | decimal(15,4) | NN |
| extra_child_rate | decimal(15,4) | NN |
| currency_code | char(3) | NN |
| effective_from | date | NN |
| effective_to | date | |
| created_at | datetime | NN |

### bss_rate_plans

| column | type | flags |
|---|---|---|
| rate_plan_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK |
| rate_plan_code | varchar(30) | NN |
| rate_plan_name | varchar(150) | NN |
| rate_plan_type | varchar(20) | |
| cancellation_policy_id | bigint | FK, NN |
| meal_plan | varchar(5) | |
| min_stay_nights | int | NN |
| is_refundable | int | NN |
| is_publicly_visible | int | NN |
| is_active | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_reservation_guests

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| reservation_id | bigint | FK, NN (-> bss_reservations.reservation_id) |
| guest_id | bigint | FK, NN |
| is_primary | int | NN |
| created_at | datetime | NN |

### bss_reservation_rooms

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| reservation_id | bigint | FK, NN (-> bss_reservations.reservation_id) |
| room_type_id | bigint | FK, NN |
| room_id | bigint | FK (-> bss_rooms.room_id) |
| adults | int | NN |
| rate_per_night | decimal(15,4) | NN |
| is_primary | int | NN |
| created_at | datetime | NN |

### bss_reservations

| column | type | flags |
|---|---|---|
| reservation_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| reservation_number | varchar(20) | UQ, NN |
| channel_id | bigint | FK, NN |
| channel_booking_ref | varchar(100) | |
| guest_id | bigint | FK, NN |
| corporate_account_id | bigint | FK |
| group_block_id | bigint | FK |
| rate_plan_id | bigint | FK, NN |
| package_id | bigint | FK (-> bss_packages.package_id, line visible) |
| status | varchar(20) | |
| arrival_date | date | NN |
| departure_date | date | NN |
| nights | int | |
| adults | int | NN |
| children | int | NN |
| currency_code | char(3) | NN |
| total_amount | decimal(15,4) | NN |
| payment_status | varchar(20) | |
| guaranteed_by | varchar(20) | |
| status_cancelled | varchar(20) | |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_revenue_categories

| column | type | flags |
|---|---|---|
| rev_cat_id | bigint | PK |
| rev_cat_code | varchar(30) | UQ, NN |
| rev_cat_name | varchar(100) | NN |
| revenue_type | varchar(20) | |
| department | varchar(60) | |
| gl_account_code | varchar(30) | |
| is_active | int | NN |

### bss_roles

| column | type | flags |
|---|---|---|
| role_id | bigint | PK |
| role_code | varchar(30) | UQ, NN |
| role_name | varchar(80) | NN |
| is_system_role | int | NN |
| property_id | bigint | FK |
| created_at | datetime | NN |

### bss_room_conditions

| column | type | flags |
|---|---|---|
| condition_id | bigint | PK |
| property_id | bigint | FK, NN |
| room_id | bigint | FK, NN |
| oss_device_alert_id | varchar(36) | FK, NN |
| condition_type | varchar(30) | |
| severity | varchar(10) | |
| status | varchar(20) | |
| description | text | |
| work_order_id | bigint | FK -> bss_maintenance_work_orders.work_order_id (likely; line runs right and drops to work_order_id) |
| assigned_to | varchar(36) | FK |
| resolved_at | datetime | |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_room_device_registry

POSSIBLY PARTIAL: the table appears only in r3_c5. The extra tiles (r3_c4, r4_c4, r4_c5, r5_c4, r5_c5) don't show it, and its bottom is still covered by the bss_channel_inbound_reservations header, so a column after created_at (e.g. updated_at) could be hidden. This can't be resolved from the tiles; the source diagram is needed.
| column | type | flags |
|---|---|---|
| registry_id | bigint | PK |
| property_id | bigint | FK, NN |
| room_id | bigint | FK, NN (-> bss_rooms.room_id) |
| oss_device_id | varchar(36) | FK, NN (-> oss_device.id) |
| oss_device_uid | varchar(100) | |
| device_role | varchar(30) | |
| device_name | varchar(100) | NN |
| is_controllable | int | NN |
| is_active | int | NN |
| last_known_health_status | varchar(20) | |
| last_known_device_state | json | |
| health_synced_at | datetime | |
| last_sync_at | datetime | |
| created_at | datetime | NN |

### bss_room_status_history

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| room_id | bigint | FK, NN (target off-tile) |
| property_id | bigint | FK, NN (target off-tile) |
| previous_hk_status | varchar(20) | |
| new_hk_status | varchar(20) | |
| previous_occ_status | varchar(20) | |
| new_occ_status | varchar(20) | |
| changed_by | varchar(36) | |
| change_reason | varchar(100) | |
| stay_id | bigint | FK (target off-tile) |
| changed_at | datetime | NN |

### bss_room_types

| column | type | flags |
|---|---|---|
| room_type_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| type_code | varchar(20) | NN |
| type_name | varchar(100) | NN |
| max_adults | int | NN |
| max_children | int | NN |
| max_occupancy | int | NN |
| area_sqft | decimal(7,2) | |
| bed_configuration | varchar(100) | |
| view_type | varchar(20) | |
| is_smoking_allowed | int | NN |
| is_accessible | int | NN |
| is_active | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_rooms

| column | type | flags |
|---|---|---|
| room_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| floor_id | bigint | FK, NN |
| room_type_id | bigint | FK, NN |
| room_number | varchar(10) | NN |
| housekeeping_status | varchar(20) | |
| occupancy_status | varchar(20) | |
| is_accessible | int | NN |
| oss_facility_id | varchar(36) | (no FK icon) |
| oss_asset_id | varchar(36) | FK |
| is_active | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_seasonal_rates

| column | type | flags |
|---|---|---|
| id | bigint | PK |
| rate_plan_id | bigint | FK, NN (target off-tile) |
| room_type_id | bigint | FK, NN (target off-tile) |
| rate_name | varchar(100) | NN |
| date_from | date | NN |
| date_to | date | NN |
| nightly_rate | decimal(15,4) | NN |
| currency_code | char(3) | NN |
| priority | int | NN |
| is_active | int | NN |
| created_at | datetime | NN |

### bss_service_requests

(Header text is mostly hidden behind bss_room_conditions; name read as "bss_service_requests" — uncertain.)
| column | type | flags |
|---|---|---|
| request_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| property_id | bigint | FK, NN |
| stay_id | bigint | FK |
| room_id | bigint | FK |
| request_category | varchar(30) | |
| priority | varchar(10) | |
| status | varchar(20) | |
| description | text | NN |
| sla_response_minutes | int | NN |
| sla_resolution_minutes | int | NN |
| sla_breached | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

Relationships: request_id is the target of bss_maintenance_work_orders.service_request_id.

### bss_smart_access_log

| column | type | flags |
|---|---|---|
| log_id | bigint | PK |
| property_id | bigint | FK, NN |
| room_id | bigint | FK, NN |
| stay_id | bigint | FK |
| digital_key_id | bigint | FK (probably -> bss_digital_keys.key_id; line path ambiguous) |
| oss_device_id | varchar(36) | FK, NN |
| event_type | varchar(30) | |
| access_method | varchar(20) | |
| denial_reason | varchar(100) | |
| access_timestamp | datetime | NN |
| created_at | datetime | NN |

### bss_stays

| column | type | flags |
|---|---|---|
| stay_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| reservation_id | bigint | FK, NN (-> bss_reservations.reservation_id) |
| property_id | bigint | FK, NN |
| room_id | bigint | FK, NN (-> bss_rooms.room_id) |
| guest_id | bigint | FK, NN |
| folio_id | bigint | FK (target off-tile to the right) |
| planned_check_in | datetime | NN |
| planned_check_out | datetime | NN |
| actual_check_in | datetime | |
| actual_check_out | datetime | |
| status | varchar(20) | |
| do_not_disturb | int | NN |
| created_at | datetime | NN |
| updated_at | datetime | NN |

### bss_users

(Completed from tiles_extra/r3_c3.)
| column | type | flags |
|---|---|---|
| user_id | bigint | PK |
| uuid | char(36) | UQ, NN |
| primary_property_id | bigint | FK |
| role_id | bigint | FK, NN |
| username | varchar(50) | UQ, NN |
| password_hash | varchar(255) | NN |
| first_name | varchar(60) | NN |
| last_name | varchar(60) | NN |
| email_encrypted | text | NN |
| email_hash | char(64) | UQ, NN |
| is_mfa_enabled | int | NN |
| mfa_secret_encrypted | text | |
| is_active | int | NN |
| last_login_at | datetime | |
| failed_login_attempts | int | NN |
| locked_until | datetime | |
| created_at | datetime | NN |
| updated_at | datetime | NN |

---

## Sustainability (4)

### carbon_calculations

| column | type | flags |
|---|---|---|
| calculation_id | bigint | PK |
| property_id | bigint | FK, NN |
| room_id | bigint | FK |
| stay_id | bigint | FK |
| period_from | date | NN |
| period_to | date | NN |
| energy_consumed | decimal(15,4) | NN |
| energy_unit | varchar(20) | NN |
| energy_source | varchar(50) | NN |
| emission_factor_id | int | FK, NN |
| carbon_kg | decimal(15,4) | NN |
| calculation_version | varchar(20) | |
| cm_points_awarded | int | NN |
| calculated_at | datetime | NN |
| calculated_by | varchar(36) | |

Relationships: calculation_id is the target of cm_points_ledger.calculation_id.

### cm_points_ledger

| column | type | flags |
|---|---|---|
| ledger_id | bigint | PK |
| property_id | bigint | FK, NN |
| room_id | bigint | FK |
| stay_id | bigint | FK |
| calculation_id | bigint | FK -> carbon_calculations.calculation_id |
| transaction_type | varchar(30) | |
| points | int | NN |
| balance_after | int | NN |
| description | varchar(255) | NN |
| created_at | datetime | NN |

### emission_factors

| column | type | flags |
|---|---|---|
| factor_id | int | PK |
| standard_name | varchar(100) | NN |
| region_code | varchar(10) | |
| energy_source | varchar(50) | |
| factor_value | decimal(15,8) | NN |
| unit_basis | varchar(20) | NN |
| valid_from | date | NN |
| valid_to | date | |
| version | varchar(20) | |
| source_url | varchar(500) | |
| created_at | datetime | NN |

### measurement_units

| column | type | flags |
|---|---|---|
| unit_id | int | PK |
| unit_code | varchar(20) | UQ, NN |
| unit_name | varchar(60) | NN |
| quantity_type | varchar(30) | |
| si_conversion_factor | decimal(15,8) | |
| created_at | datetime | NN |
