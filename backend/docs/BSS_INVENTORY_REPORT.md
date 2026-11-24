# BSS Database Inventory Report

**Database:** `inspironics_app` (MySQL) &nbsp;|&nbsp; **Generated:** 2026-11-03 07:35 UTC

> **READ-ONLY.** Nothing was modified, deleted, truncated or migrated. Structure is derived from the SQLAlchemy models; row counts come from `COUNT(*)` on a session opened `READ ONLY`.

## Summary

- **Total tables:** 95
- **Total columns:** 957
- **Total foreign key relationships:** 250
- **Total rows:** 1,798 across 93 non-empty tables

### Tables per functional module

- **A. Organisation, Facility & Identity** — 9 tables — 270 rows
- **B. Rooms, Amenities & Packages** — 10 tables — 83 rows
- **C. Guests, Stays & Billing** — 7 tables — 33 rows
- **D. Service Requests & Catalogue** — 8 tables — 69 rows
- **E. Job Orders & Workforce** — 3 tables — 9 rows
- **F. Maintenance** — 4 tables — 14 rows
- **G. Devices, Telemetry & IoT** — 15 tables — 841 rows
- **H. Alerts & Incidents** — 8 tables — 60 rows
- **I. Access Control & Digital Keys** — 4 tables — 19 rows
- **J. Marketing, Offers & Holidays** — 5 tables — 22 rows
- **K. People, Roles & Permissions** — 9 tables — 139 rows
- **L. Activity & Audit** — 9 tables — 120 rows
- **M. Scheduling & Tasks** — 2 tables — 11 rows
- **N. Reporting & Analytics** — 2 tables — 107 rows

## A. Organisation, Facility & Identity

### `attachment`

- **Rows:** 8
- **Columns:** 8
- **Primary key:** `id`
- **Foreign keys (2):**
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`

### `country`

- **Rows:** 239
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys:** *none*

### `currency`  ⚠️ *not in APPROVED_TABLES*

- **Rows:** unavailable
- **Columns:** 8
- **Primary key:** `id`
- **Foreign keys:** *none*

### `facility`

- **Rows:** 1
- **Columns:** 19
- **Primary key:** `id`
- **Foreign keys (5):**
  - `created_by` -> `app_user.id`
  - `currency_id` -> `currency.id`
  - `default_key_user` -> `app_user.id`
  - `facility_image_id` -> `attachment.id`
  - `org_id` -> `organisation.id`

### `facility_user`

- **Rows:** 13
- **Columns:** 6
- **Primary key:** `facility_id`, `app_user_id`
- **Foreign keys (3):**
  - `app_user_id` -> `app_user.id`
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`

### `organisation`

- **Rows:** 1
- **Columns:** 7
- **Primary key:** `id`
- **Foreign keys (1):**
  - `created_by` -> `app_user.id`

### `property`

- **Rows:** 4
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (3):**
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`
  - `property_type_id` -> `property_type.id`

### `property_chain`

- **Rows:** 3
- **Columns:** 10
- **Primary key:** `id`
- **Foreign keys (5):**
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`
  - `level_one_id` -> `property.id`
  - `level_three_id` -> `property.id`
  - `level_two_id` -> `property.id`

### `property_type`

- **Rows:** 1
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (2):**
  - `facility_id` -> `facility.id`
  - `property_type_image_id` -> `attachment.id`

## B. Rooms, Amenities & Packages

### `amenity`

- **Rows:** 27
- **Columns:** 15
- **Primary key:** `id`
- **Foreign keys (7):**
  - `amenity_type_id` -> `amenity_type.id`
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`
  - `package_id` -> `package.id`
  - `parent_amenity_id` -> `amenity.id`
  - `property_chain_id` -> `property_chain.id`
  - `status` -> `amenity_status.id`

### `amenity_condition`

- **Rows:** 5
- **Columns:** 8
- **Primary key:** `id`
- **Foreign keys:** *none*

### `amenity_condition_status`

- **Rows:** 4
- **Columns:** 5
- **Primary key:** `amenity_id`, `amenity_condition_id`
- **Foreign keys (2):**
  - `amenity_condition_id` -> `amenity_condition.id`
  - `amenity_id` -> `amenity.id`

### `amenity_status`

- **Rows:** 4
- **Columns:** 4
- **Primary key:** `id`
- **Foreign keys:** *none*

### `amenity_type`

- **Rows:** 5
- **Columns:** 10
- **Primary key:** `id`
- **Foreign keys (3):**
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`
  - `image_id` -> `attachment.id`

### `feature`

- **Rows:** 6
- **Columns:** 10
- **Primary key:** `id`
- **Foreign keys (3):**
  - `created_by` -> `app_user.id`
  - `device_type` -> `device_type.id`
  - `facility_id` -> `facility.id`

### `package`

- **Rows:** 8
- **Columns:** 14
- **Primary key:** `id`
- **Foreign keys (5):**
  - `amenity_type` -> `amenity_type.id`
  - `created_by` -> `app_user.id`
  - `currency_id` -> `currency.id`
  - `facility_id` -> `facility.id`
  - `image_id` -> `attachment.id`

### `package_feature`

- **Rows:** 17
- **Columns:** 8
- **Primary key:** `id`
- **Foreign keys (3):**
  - `created_by` -> `app_user.id`
  - `feature_id` -> `feature.id`
  - `package_id` -> `package.id`

### `room_status_condition_applicability`  ⚠️ *not in APPROVED_TABLES*

- **Rows:** unavailable
- **Columns:** 10
- **Primary key:** `id`
- **Foreign keys (2):**
  - `amenity_status_id` -> `amenity_status.id`
  - `condition_id` -> `amenity_condition.id`

### `sub_package`

- **Rows:** 7
- **Columns:** 5
- **Primary key:** `parent_package_id`, `sub_package_id`
- **Foreign keys (3):**
  - `created_by` -> `app_user.id`
  - `parent_package_id` -> `package.id`
  - `sub_package_id` -> `package.id`

## C. Guests, Stays & Billing

### `import_job`

- **Rows:** 3
- **Columns:** 14
- **Primary key:** `id`
- **Foreign keys (1):**
  - `created_by` -> `app_user.id`

### `invoice`

- **Rows:** 2
- **Columns:** 20
- **Primary key:** `id`
- **Foreign keys (6):**
  - `billing_user_id` -> `app_user.id`
  - `created_by` -> `app_user.id`
  - `currency_id` -> `currency.id`
  - `facility_id` -> `facility.id`
  - `facility_image_id` -> `attachment.id`
  - `stay_id` -> `stay.id`

### `room_allocation`

- **Rows:** 5
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (4):**
  - `created_by` -> `app_user.id`
  - `package_id` -> `package.id`
  - `room_id` -> `amenity.id`
  - `stay_id` -> `stay.id`

### `stay`

- **Rows:** 6
- **Columns:** 21
- **Primary key:** `id`
- **Foreign keys (4):**
  - `booking_user_id` -> `app_user.id`
  - `checkout_initiated_by` -> `app_user.id`
  - `created_by` -> `app_user.id`
  - `modified_by` -> `app_user.id`

### `stay_package`

- **Rows:** 6
- **Columns:** 7
- **Primary key:** `id`
- **Foreign keys (2):**
  - `package_id` -> `package.id`
  - `stay_id` -> `stay.id`

### `stay_user`

- **Rows:** 8
- **Columns:** 10
- **Primary key:** `id`
- **Foreign keys (4):**
  - `app_user_id` -> `app_user.id`
  - `created_by` -> `app_user.id`
  - `room_id` -> `amenity.id`
  - `stay_id` -> `stay.id`

### `user_document`

- **Rows:** 3
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (3):**
  - `app_user_id` -> `app_user.id`
  - `attachment_id` -> `attachment.id`
  - `stay_id` -> `stay.id`

## D. Service Requests & Catalogue

### `room_service_request`

- **Rows:** 3
- **Columns:** 11
- **Primary key:** `id`
- **Foreign keys (4):**
  - `assigned_to` -> `app_user.id`
  - `created_by` -> `app_user.id`
  - `guest_room_id` -> `amenity.id`
  - `stay_id` -> `stay.id`

### `room_service_request_item`

- **Rows:** 4
- **Columns:** 7
- **Primary key:** `id`
- **Foreign keys (2):**
  - `room_service_request_id` -> `room_service_request.id`
  - `service_category_item_id` -> `service_category_item.id`

### `service_category`

- **Rows:** 13
- **Columns:** 12
- **Primary key:** `id`
- **Foreign keys (4):**
  - `category_icon` -> `attachment.id`
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`
  - `service_type` -> `service_type.id`

### `service_category_item`

- **Rows:** 22
- **Columns:** 15
- **Primary key:** `id`
- **Foreign keys (6):**
  - `amenity_id` -> `amenity.id`
  - `category_id` -> `service_category.id`
  - `created_by` -> `app_user.id`
  - `currency_id` -> `currency.id`
  - `facility_id` -> `facility.id`
  - `item_icon` -> `attachment.id`

### `service_request`

- **Rows:** 7
- **Columns:** 25
- **Primary key:** `id`
- **Foreign keys (12):**
  - `amenity_id` -> `amenity.id`
  - `app_user_id` -> `app_user.id`
  - `assigned_to` -> `app_user.id`
  - `category_id` -> `service_category.id`
  - `created_by` -> `app_user.id`
  - `department_id` -> `department.id`
  - `facility_id` -> `facility.id`
  - `promo_code_id` -> `promo_code.id`
  - `service_type` -> `service_type.id`
  - `status` -> `service_status.id`
  - `stay_id` -> `stay.id`
  - `updated_by` -> `app_user.id`

### `service_request_item`

- **Rows:** 8
- **Columns:** 11
- **Primary key:** `id`
- **Foreign keys (5):**
  - `assigned_to` -> `app_user.id`
  - `category_id` -> `service_category.id`
  - `item_id` -> `service_category_item.id`
  - `service_request_id` -> `service_request.id`
  - `status` -> `service_status.id`

### `service_status`

- **Rows:** 5
- **Columns:** 4
- **Primary key:** `id`
- **Foreign keys:** *none*

### `service_type`

- **Rows:** 7
- **Columns:** 4
- **Primary key:** `id`
- **Foreign keys:** *none*

## E. Job Orders & Workforce

### `job_order`

- **Rows:** 3
- **Columns:** 15
- **Primary key:** `id`
- **Foreign keys (2):**
  - `assigned_to` -> `app_user.id`
  - `created_by` -> `app_user.id`

### `job_order_amenity`

- **Rows:** 4
- **Columns:** 4
- **Primary key:** `job_order_id`, `amenity_id`
- **Foreign keys (2):**
  - `amenity_id` -> `amenity.id`
  - `job_order_id` -> `job_order.id`

### `job_order_device`

- **Rows:** 2
- **Columns:** 4
- **Primary key:** `job_order_id`, `device_id`
- **Foreign keys (2):**
  - `device_id` -> `device.id`
  - `job_order_id` -> `job_order.id`

## F. Maintenance

### `maintenance_request`

- **Rows:** 3
- **Columns:** 25
- **Primary key:** `id`
- **Foreign keys (8):**
  - `category_id` -> `service_category.id`
  - `created_by` -> `app_user.id`
  - `department_id` -> `department.id`
  - `facility_id` -> `facility.id`
  - `item_id` -> `service_category_item.id`
  - `maintenance_request_status` -> `service_status.id`
  - `parent_id` -> `maintenance_request.id`
  - `updated_by` -> `app_user.id`

### `maintenance_request_amenity`

- **Rows:** 6
- **Columns:** 8
- **Primary key:** `id`
- **Foreign keys (3):**
  - `amenity_id` -> `amenity.id`
  - `created_by` -> `app_user.id`
  - `maintenance_request_id` -> `maintenance_request.id`

### `maintenance_request_assignee`

- **Rows:** 4
- **Columns:** 8
- **Primary key:** `id`
- **Foreign keys (3):**
  - `app_user_id` -> `app_user.id`
  - `created_by` -> `app_user.id`
  - `maintenance_request_id` -> `maintenance_request.id`

### `maintenance_request_recurrence`

- **Rows:** 1
- **Columns:** 6
- **Primary key:** `maintenance_request_id`
- **Foreign keys (1):**
  - `maintenance_request_id` -> `maintenance_request.id`

## G. Devices, Telemetry & IoT

### `battery_life_stat`

- **Rows:** 12
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (1):**
  - `device_id` -> `device.id`

### `command_type`

- **Rows:** 10
- **Columns:** 5
- **Primary key:** `id`
- **Foreign keys (1):**
  - `device_type_id` -> `device_type.id`

### `device`

- **Rows:** 14
- **Columns:** 28
- **Primary key:** `id`
- **Foreign keys (7):**
  - `amenity_id` -> `amenity.id`
  - `created_by` -> `app_user.id`
  - `current_firmware_version` -> `firmware.id`
  - `device_type` -> `device_type.id`
  - `expected_firmware_version` -> `firmware.id`
  - `facility_id` -> `facility.id`
  - `parent_device_id` -> `device.id`

### `device_command`

- **Rows:** 7
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (3):**
  - `command_type` -> `command_type.id`
  - `created_by` -> `app_user.id`
  - `device_id` -> `device.id`

### `device_current_stat`

- **Rows:** 14
- **Columns:** 7
- **Primary key:** `id`
- **Foreign keys (1):**
  - `device_id` -> `device.id`

### `device_health_stat`

- **Rows:** 168
- **Columns:** 7
- **Primary key:** `id`
- **Foreign keys (1):**
  - `device_id` -> `device.id`

### `device_param`

- **Rows:** 35
- **Columns:** 7
- **Primary key:** `id`
- **Foreign keys (1):**
  - `device_type` -> `device_type.id`

### `device_stat`

- **Rows:** 504
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (2):**
  - `device_id` -> `device.id`
  - `device_param_id` -> `device_param.id`

### `device_type`

- **Rows:** 4
- **Columns:** 5
- **Primary key:** `id`
- **Foreign keys:** *none*

### `firmware`

- **Rows:** 6
- **Columns:** 17
- **Primary key:** `id`
- **Foreign keys (4):**
  - `created_by` -> `app_user.id`
  - `device_type_id` -> `device_type.id`
  - `updated_by` -> `app_user.id`
  - `uploaded_by` -> `app_user.id`

### `mqtt_broker`

- **Rows:** 1
- **Columns:** 11
- **Primary key:** `id`
- **Foreign keys (1):**
  - `facility_id` -> `facility.id`

### `mqtt_topic`

- **Rows:** 12
- **Columns:** 8
- **Primary key:** `id`
- **Foreign keys (2):**
  - `device_id` -> `device.id`
  - `mqtt_broker_id` -> `mqtt_broker.id`

### `other_device`

- **Rows:** 12
- **Columns:** 18
- **Primary key:** `id`
- **Foreign keys (1):**
  - `device_id` -> `device.id`

### `room_device_map`

- **Rows:** 0
- **Columns:** 7
- **Primary key:** `id`
- **Foreign keys (2):**
  - `amenity_id` -> `amenity.id`
  - `created_by` -> `app_user.id`

### `sensor_operation_stat`

- **Rows:** 42
- **Columns:** 6
- **Primary key:** `device_id`, `stats_date`
- **Foreign keys (2):**
  - `amenity_id` -> `amenity.id`
  - `device_id` -> `device.id`

## H. Alerts & Incidents

### `alert_type`

- **Rows:** 16
- **Columns:** 4
- **Primary key:** `id`
- **Foreign keys:** *none*

### `device_alert`

- **Rows:** 9
- **Columns:** 10
- **Primary key:** `id`
- **Foreign keys (4):**
  - `alert_type` -> `alert_type.id`
  - `amenity_id` -> `amenity.id`
  - `created_by` -> `app_user.id`
  - `device_id` -> `device.id`

### `device_incident`

- **Rows:** 5
- **Columns:** 14
- **Primary key:** `id`
- **Foreign keys (8):**
  - `alert_type` -> `alert_type.id`
  - `amenity_id` -> `amenity.id`
  - `assigned_to` -> `app_user.id`
  - `current_incident_status` -> `incident_status.id`
  - `device_id` -> `device.id`
  - `facility_id` -> `facility.id`
  - `latest_alert_id` -> `device_alert.id`
  - `updated_by` -> `app_user.id`

### `incident_event`

- **Rows:** 5
- **Columns:** 4
- **Primary key:** `id`
- **Foreign keys:** *none*

### `incident_history`

- **Rows:** 14
- **Columns:** 8
- **Primary key:** `id`
- **Foreign keys (3):**
  - `created_by` -> `app_user.id`
  - `incident_event_id` -> `incident_event.id`
  - `incident_id` -> `device_incident.id`

### `incident_status`

- **Rows:** 4
- **Columns:** 4
- **Primary key:** `id`
- **Foreign keys:** *none*

### `value_alert`

- **Rows:** 3
- **Columns:** 16
- **Primary key:** `id`
- **Foreign keys (5):**
  - `amenity_id` -> `amenity.id`
  - `device_id` -> `device.id`
  - `device_type_id` -> `device_type.id`
  - `facility_id` -> `facility.id`
  - `limit_config_id` -> `value_alert_limit_config.id`

### `value_alert_limit_config`

- **Rows:** 4
- **Columns:** 16
- **Primary key:** `id`
- **Foreign keys (2):**
  - `device_id` -> `device.id`
  - `facility_id` -> `facility.id`

## I. Access Control & Digital Keys

### `access_key`

- **Rows:** 5
- **Columns:** 13
- **Primary key:** `id`
- **Foreign keys (6):**
  - `created_by` -> `app_user.id`
  - `device_id` -> `device.id`
  - `key_type` -> `key_type.id`
  - `maintenance_request_id` -> `maintenance_request.id`
  - `stay_id` -> `stay.id`
  - `user_device_acl_id` -> `user_device_acl.id`

### `key_type`

- **Rows:** 4
- **Columns:** 4
- **Primary key:** `id`
- **Foreign keys:** *none*

### `lock_activity_log`

- **Rows:** 5
- **Columns:** 13
- **Primary key:** `id`
- **Foreign keys (6):**
  - `amenity_id` -> `amenity.id`
  - `app_user_id` -> `app_user.id`
  - `facility_id` -> `facility.id`
  - `key_type` -> `key_type.id`
  - `lock_id` -> `device.id`
  - `stay_id` -> `stay.id`

### `user_device_acl`

- **Rows:** 5
- **Columns:** 14
- **Primary key:** `id`
- **Foreign keys (7):**
  - `amenity_id` -> `amenity.id`
  - `amenity_type_id` -> `amenity_type.id`
  - `app_user_id` -> `app_user.id`
  - `created_by` -> `app_user.id`
  - `device_id` -> `device.id`
  - `device_type_id` -> `device_type.id`
  - `stay_id` -> `stay.id`

## J. Marketing, Offers & Holidays

### `facility_event`

- **Rows:** 3
- **Columns:** 17
- **Primary key:** `id`
- **Foreign keys (3):**
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`
  - `image_id` -> `attachment.id`

### `occasion`

- **Rows:** 4
- **Columns:** 17
- **Primary key:** `id`
- **Foreign keys (4):**
  - `app_user_id` -> `app_user.id`
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`
  - `occasion_type` -> `occasion_type.id`

### `occasion_type`

- **Rows:** 4
- **Columns:** 5
- **Primary key:** `id`
- **Foreign keys:** *none*

### `promo_code`

- **Rows:** 3
- **Columns:** 16
- **Primary key:** `id`
- **Foreign keys (2):**
  - `created_by` -> `app_user.id`
  - `promo_code_icon` -> `attachment.id`

### `promo_code_amenity`

- **Rows:** 8
- **Columns:** 6
- **Primary key:** `promo_code_id`, `amenity_id`
- **Foreign keys (3):**
  - `amenity_id` -> `amenity.id`
  - `created_by` -> `app_user.id`
  - `promo_code_id` -> `promo_code.id`

## K. People, Roles & Permissions

### `app_user`

- **Rows:** 16
- **Columns:** 29
- **Primary key:** `id`
- **Foreign keys (6):**
  - `country` -> `country.id`
  - `created_by` -> `app_user.id`
  - `department_id` -> `department.id`
  - `job_function_id` -> `job_function.id`
  - `nationality` -> `country.id`
  - `supervisor` -> `app_user.id`

### `department`

- **Rows:** 5
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (2):**
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`

### `job_function`

- **Rows:** 5
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (2):**
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`

### `role`

- **Rows:** 7
- **Columns:** 11
- **Primary key:** `id`
- **Foreign keys (2):**
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`

### `role_module`

- **Rows:** 18
- **Columns:** 6
- **Primary key:** `id`
- **Foreign keys:** *none*

### `role_module_permission`

- **Rows:** 65
- **Columns:** 6
- **Primary key:** `role_id`, `module_id`
- **Foreign keys (2):**
  - `module_id` -> `role_module.id`
  - `role_id` -> `role.id`

### `user_device`

- **Rows:** 4
- **Columns:** 12
- **Primary key:** `id`
- **Foreign keys (3):**
  - `app_user_id` -> `app_user.id`
  - `stay_id` -> `stay.id`
  - `user_token_id` -> `user_token.id`

### `user_role`

- **Rows:** 16
- **Columns:** 6
- **Primary key:** `facility_id`, `app_user_id`, `role_id`
- **Foreign keys (4):**
  - `app_user_id` -> `app_user.id`
  - `created_by` -> `app_user.id`
  - `facility_id` -> `facility.id`
  - `role_id` -> `role.id`

### `user_token`

- **Rows:** 3
- **Columns:** 8
- **Primary key:** `id`
- **Foreign keys (1):**
  - `app_user_id` -> `app_user.id`

## L. Activity & Audit

### `activity`

- **Rows:** 10
- **Columns:** 13
- **Primary key:** `id`
- **Foreign keys (5):**
  - `activity_type_id` -> `activity_type.id`
  - `actor_id` -> `app_user.id`
  - `entity_type_id` -> `entity_type.id`
  - `facility_id` -> `facility.id`
  - `stay_id` -> `stay.id`

### `activity_notifier`

- **Rows:** 15
- **Columns:** 7
- **Primary key:** `activity_id`, `app_user_id`
- **Foreign keys (2):**
  - `activity_id` -> `activity.id`
  - `app_user_id` -> `app_user.id`

### `activity_role_association`

- **Rows:** 34
- **Columns:** 4
- **Primary key:** `activity_type_id`, `role_id`
- **Foreign keys (2):**
  - `activity_type_id` -> `activity_type.id`
  - `role_id` -> `role.id`

### `activity_type`

- **Rows:** 22
- **Columns:** 7
- **Primary key:** `id`
- **Foreign keys (1):**
  - `entity_type_id` -> `entity_type.id`

### `entity_type`

- **Rows:** 5
- **Columns:** 4
- **Primary key:** `id`
- **Foreign keys:** *none*

### `notification`

- **Rows:** 6
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (1):**
  - `template_id` -> `notification_template.id`

### `notification_receiver`

- **Rows:** 6
- **Columns:** 11
- **Primary key:** `id`
- **Foreign keys (2):**
  - `app_user_id` -> `app_user.id`
  - `notification_id` -> `notification.id`

### `notification_result`

- **Rows:** 6
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (1):**
  - `receiver_id` -> `notification_receiver.id`

### `notification_template`

- **Rows:** 16
- **Columns:** 7
- **Primary key:** `id`
- **Foreign keys:** *none*

## M. Scheduling & Tasks

### `scheduler_job`

- **Rows:** 5
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys:** *none*

### `scheduler_job_execution`

- **Rows:** 6
- **Columns:** 9
- **Primary key:** `id`
- **Foreign keys (1):**
  - `scheduler_job_id` -> `scheduler_job.id`

## N. Reporting & Analytics

### `daily_dual_data_point`

- **Rows:** 35
- **Columns:** 7
- **Primary key:** `metric_date`, `metric_type`
- **Foreign keys (1):**
  - `facility_id` -> `facility.id`

### `energy_stat`

- **Rows:** 72
- **Columns:** 8
- **Primary key:** `device_name`, `facility_id`, `amenity_id`, `hour`
- **Foreign keys (3):**
  - `amenity_id` -> `amenity.id`
  - `device_id` -> `device.id`
  - `facility_id` -> `facility.id`
