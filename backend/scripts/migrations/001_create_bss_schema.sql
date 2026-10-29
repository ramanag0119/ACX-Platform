-- ============================================================================
-- HMS BSS (Business Support System) MySQL 8.0 Baseline Schema DDL
-- Database: hms_bss
-- Standard: MySQL 8.0 / InnoDB / utf8mb4 / utf8mb4_unicode_ci
-- Date: 2026-10-26
-- Description: 54 BSS Tables covering PMS, Rates, Reservations, Folios, 
--              Housekeeping, Events, Loyalty, Marketing & Sustainability.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `hms_bss`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `hms_bss`;

-- ----------------------------------------------------------------------------
-- 1. Brands, Properties & Room Inventory
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `bss_brands` (
  `brand_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `brand_uuid` CHAR(36) NOT NULL UNIQUE,
  `name` VARCHAR(100) NOT NULL,
  `code` VARCHAR(20) NOT NULL UNIQUE,
  `description` TEXT NULL,
  `logo_url` VARCHAR(255) NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_properties` (
  `property_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `property_uuid` CHAR(36) NOT NULL UNIQUE,
  `brand_id` BIGINT NOT NULL,
  `oss_facility_id` CHAR(36) NOT NULL, -- Cross-system bridge to oss_facility.id
  `name` VARCHAR(150) NOT NULL,
  `code` VARCHAR(30) NOT NULL UNIQUE,
  `currency` VARCHAR(3) NOT NULL DEFAULT 'INR',
  `timezone` VARCHAR(50) NOT NULL DEFAULT 'Asia/Kolkata',
  `check_in_time` TIME NOT NULL DEFAULT '14:00:00',
  `check_out_time` TIME NOT NULL DEFAULT '11:00:00',
  `status` VARCHAR(20) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `ix_bss_properties_brand` (`brand_id`),
  INDEX `ix_bss_properties_oss_facility` (`oss_facility_id`),
  CONSTRAINT `fk_bss_properties_brand` FOREIGN KEY (`brand_id`) REFERENCES `bss_brands` (`brand_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_floors` (
  `floor_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `floor_uuid` CHAR(36) NOT NULL UNIQUE,
  `property_id` BIGINT NOT NULL,
  `floor_number` INT NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `description` VARCHAR(255) NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_bss_floors_prop_num` (`property_id`, `floor_number`),
  CONSTRAINT `fk_bss_floors_property` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_room_types` (
  `room_type_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `room_type_uuid` CHAR(36) NOT NULL UNIQUE,
  `property_id` BIGINT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `code` VARCHAR(30) NOT NULL,
  `base_occupancy` INT NOT NULL DEFAULT 2,
  `max_occupancy` INT NOT NULL DEFAULT 4,
  `base_price` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
  `description` TEXT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_bss_room_types_prop_code` (`property_id`, `code`),
  CONSTRAINT `fk_bss_room_types_property` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_rooms` (
  `room_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `room_uuid` CHAR(36) NOT NULL UNIQUE,
  `property_id` BIGINT NOT NULL,
  `floor_id` BIGINT NOT NULL,
  `room_type_id` BIGINT NOT NULL,
  `room_number` VARCHAR(20) NOT NULL,
  `oss_asset_id` CHAR(36) NOT NULL, -- Cross-system bridge to oss_amenity.id
  `status` VARCHAR(30) NOT NULL DEFAULT 'available', -- available, occupied, maintenance, dirty, out_of_order
  `housekeeping_status` VARCHAR(30) NOT NULL DEFAULT 'clean', -- clean, dirty, inspected
  `is_smoking` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_bss_rooms_prop_num` (`property_id`, `room_number`),
  INDEX `ix_bss_rooms_oss_asset` (`oss_asset_id`),
  CONSTRAINT `fk_bss_rooms_property` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_rooms_floor` FOREIGN KEY (`floor_id`) REFERENCES `bss_floors` (`floor_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bss_rooms_type` FOREIGN KEY (`room_type_id`) REFERENCES `bss_room_types` (`room_type_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_room_status_history` (
  `history_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `room_id` BIGINT NOT NULL,
  `previous_status` VARCHAR(30) NOT NULL,
  `new_status` VARCHAR(30) NOT NULL,
  `changed_by_user_id` VARCHAR(36) NOT NULL, -- oss_app_user.id
  `reason` VARCHAR(255) NULL,
  `changed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `ix_bss_room_history_room` (`room_id`),
  CONSTRAINT `fk_bss_room_history_room` FOREIGN KEY (`room_id`) REFERENCES `bss_rooms` (`room_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_room_device_registry` (
  `registry_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `room_id` BIGINT NOT NULL,
  `oss_device_id` CHAR(36) NOT NULL, -- Cross-system bridge to oss_device.id
  `device_role` VARCHAR(50) NOT NULL DEFAULT 'general', -- thermostat, door_lock, light_controller
  `last_known_health_status` VARCHAR(20) NOT NULL DEFAULT 'unknown', -- online, offline, degraded
  `last_checked_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_bss_room_device` (`room_id`, `oss_device_id`),
  INDEX `ix_bss_room_device_oss_device` (`oss_device_id`),
  CONSTRAINT `fk_bss_room_device_room` FOREIGN KEY (`room_id`) REFERENCES `bss_rooms` (`room_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 2. Guests, Protected PII & Accounts
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `bss_guests` (
  `guest_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `guest_uuid` CHAR(36) NOT NULL UNIQUE,
  `oss_user_id` CHAR(36) NULL, -- Optional link to oss_app_user.id if registered
  `vip_tier` VARCHAR(20) NOT NULL DEFAULT 'standard',
  `total_stays` INT NOT NULL DEFAULT 0,
  `total_spend` DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  `loyalty_points` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(20) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `ix_bss_guests_oss_user` (`oss_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_guest_pii` (
  `pii_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `guest_id` BIGINT NOT NULL UNIQUE,
  `first_name` VARCHAR(100) NOT NULL,
  `last_name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(255) NULL,
  `phone_number` VARCHAR(30) NULL,
  `passport_number` VARCHAR(50) NULL,
  `id_document_number` VARCHAR(50) NULL,
  `address_line1` VARCHAR(255) NULL,
  `address_line2` VARCHAR(255) NULL,
  `city` VARCHAR(100) NULL,
  `postal_code` VARCHAR(20) NULL,
  `country_code` VARCHAR(3) NULL,
  `dob` DATE NULL,
  `gender` VARCHAR(10) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_guest_pii_guest` FOREIGN KEY (`guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_pii_access_log` (
  `log_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `guest_id` BIGINT NOT NULL,
  `accessed_by` VARCHAR(36) NOT NULL, -- oss_app_user.id
  `access_reason` VARCHAR(255) NOT NULL,
  `accessed_fields` TEXT NOT NULL,
  `ip_address` VARCHAR(45) NULL,
  `accessed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `ix_bss_pii_log_guest` (`guest_id`),
  INDEX `ix_bss_pii_log_user` (`accessed_by`),
  CONSTRAINT `fk_bss_pii_log_guest` FOREIGN KEY (`guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_corporate_accounts` (
  `corporate_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `corporate_uuid` CHAR(36) NOT NULL UNIQUE,
  `company_name` VARCHAR(150) NOT NULL,
  `tax_id` VARCHAR(50) NULL,
  `credit_limit` DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  `current_balance` DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  `payment_terms_days` INT NOT NULL DEFAULT 30,
  `status` VARCHAR(20) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 3. Pricing, Distribution & Marketing
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `bss_rate_plans` (
  `rate_plan_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `rate_plan_uuid` CHAR(36) NOT NULL UNIQUE,
  `property_id` BIGINT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `code` VARCHAR(30) NOT NULL,
  `is_refundable` TINYINT(1) NOT NULL DEFAULT 1,
  `meals_included` VARCHAR(50) NOT NULL DEFAULT 'none',
  `status` VARCHAR(20) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_bss_rate_plans_prop_code` (`property_id`, `code`),
  CONSTRAINT `fk_bss_rate_plans_property` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_rate_plan_room_types` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `rate_plan_id` BIGINT NOT NULL,
  `room_type_id` BIGINT NOT NULL,
  `price_adjustment_percent` DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
  `fixed_price_override` DECIMAL(12, 2) NULL,
  UNIQUE KEY `uq_bss_rate_room_type` (`rate_plan_id`, `room_type_id`),
  CONSTRAINT `fk_bss_rprt_rate` FOREIGN KEY (`rate_plan_id`) REFERENCES `bss_rate_plans` (`rate_plan_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_rprt_room_type` FOREIGN KEY (`room_type_id`) REFERENCES `bss_room_types` (`room_type_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_seasonal_rates` (
  `seasonal_rate_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `property_id` BIGINT NOT NULL,
  `room_type_id` BIGINT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `rate_multiplier` DECIMAL(4, 2) NOT NULL DEFAULT 1.00,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_seasonal_property` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_seasonal_room_type` FOREIGN KEY (`room_type_id`) REFERENCES `bss_room_types` (`room_type_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_cancellation_policies` (
  `policy_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `property_id` BIGINT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `free_cancellation_hours` INT NOT NULL DEFAULT 24,
  `penalty_percent` DECIMAL(5, 2) NOT NULL DEFAULT 100.00,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_cancel_policy_prop` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_booking_channels` (
  `channel_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL,
  `code` VARCHAR(20) NOT NULL UNIQUE,
  `channel_type` VARCHAR(30) NOT NULL DEFAULT 'direct', -- direct, ota, gds, corporate
  `status` VARCHAR(20) NOT NULL DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_ota_channels` (
  `ota_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `channel_id` BIGINT NOT NULL,
  `ota_name` VARCHAR(100) NOT NULL,
  `api_endpoint` VARCHAR(255) NULL,
  CONSTRAINT `fk_bss_ota_channel` FOREIGN KEY (`channel_id`) REFERENCES `bss_booking_channels` (`channel_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_property_channel_configs` (
  `config_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `property_id` BIGINT NOT NULL,
  `channel_id` BIGINT NOT NULL,
  `channel_property_id` VARCHAR(100) NOT NULL,
  `is_enabled` TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY `uq_bss_prop_channel` (`property_id`, `channel_id`),
  CONSTRAINT `fk_bss_pcc_property` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_pcc_channel` FOREIGN KEY (`channel_id`) REFERENCES `bss_booking_channels` (`channel_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_channel_inbound_reservations` (
  `inbound_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `channel_id` BIGINT NOT NULL,
  `external_reservation_id` VARCHAR(100) NOT NULL,
  `payload` JSON NOT NULL,
  `process_status` VARCHAR(30) NOT NULL DEFAULT 'received',
  `received_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `ix_bss_inbound_ext_id` (`external_reservation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_availability_calendar` (
  `calendar_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `property_id` BIGINT NOT NULL,
  `room_type_id` BIGINT NOT NULL,
  `calendar_date` DATE NOT NULL,
  `total_rooms` INT NOT NULL DEFAULT 0,
  `booked_rooms` INT NOT NULL DEFAULT 0,
  `out_of_order_rooms` INT NOT NULL DEFAULT 0,
  UNIQUE KEY `uq_bss_avail_calendar` (`property_id`, `room_type_id`, `calendar_date`),
  CONSTRAINT `fk_bss_avail_property` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_avail_room_type` FOREIGN KEY (`room_type_id`) REFERENCES `bss_room_types` (`room_type_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_group_blocks` (
  `block_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `property_id` BIGINT NOT NULL,
  `group_name` VARCHAR(150) NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `cutoff_date` DATE NOT NULL,
  `rooms_blocked` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(20) NOT NULL DEFAULT 'tentative',
  CONSTRAINT `fk_bss_group_block_prop` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_packages` (
  `package_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `property_id` BIGINT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `code` VARCHAR(30) NOT NULL,
  `price` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT `fk_bss_packages_property` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 4. Reservations & Stays
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `bss_reservations` (
  `reservation_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `reservation_uuid` CHAR(36) NOT NULL UNIQUE,
  `property_id` BIGINT NOT NULL,
  `guest_id` BIGINT NOT NULL,
  `channel_id` BIGINT NOT NULL,
  `confirmation_number` VARCHAR(30) NOT NULL UNIQUE,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `total_rooms` INT NOT NULL DEFAULT 1,
  `total_amount` DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  `deposit_paid` DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  `status` VARCHAR(30) NOT NULL DEFAULT 'confirmed', -- confirmed, checked_in, checked_out, cancelled, no_show
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `ix_bss_res_guest` (`guest_id`),
  INDEX `ix_bss_res_dates` (`start_date`, `end_date`),
  CONSTRAINT `fk_bss_res_property` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bss_res_guest` FOREIGN KEY (`guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bss_res_channel` FOREIGN KEY (`channel_id`) REFERENCES `bss_booking_channels` (`channel_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_reservation_rooms` (
  `reservation_room_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `reservation_id` BIGINT NOT NULL,
  `room_type_id` BIGINT NOT NULL,
  `assigned_room_id` BIGINT NULL,
  `rate_plan_id` BIGINT NOT NULL,
  `room_price_per_night` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
  `oss_room_allocation_id` CHAR(36) NULL, -- Cross-system bridge to oss_room_allocation.id
  INDEX `ix_bss_res_room_assign` (`assigned_room_id`),
  CONSTRAINT `fk_bss_res_rooms_res` FOREIGN KEY (`reservation_id`) REFERENCES `bss_reservations` (`reservation_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_res_rooms_type` FOREIGN KEY (`room_type_id`) REFERENCES `bss_room_types` (`room_type_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bss_res_rooms_room` FOREIGN KEY (`assigned_room_id`) REFERENCES `bss_rooms` (`room_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_bss_res_rooms_rate` FOREIGN KEY (`rate_plan_id`) REFERENCES `bss_rate_plans` (`rate_plan_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_reservation_guests` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `reservation_id` BIGINT NOT NULL,
  `guest_id` BIGINT NOT NULL,
  `is_primary` TINYINT(1) NOT NULL DEFAULT 0,
  CONSTRAINT `fk_bss_res_guests_res` FOREIGN KEY (`reservation_id`) REFERENCES `bss_reservations` (`reservation_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_res_guests_guest` FOREIGN KEY (`guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_stays` (
  `stay_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `stay_uuid` CHAR(36) NOT NULL UNIQUE,
  `reservation_id` BIGINT NOT NULL,
  `room_id` BIGINT NOT NULL,
  `primary_guest_id` BIGINT NOT NULL,
  `planned_check_in` DATETIME NOT NULL,
  `planned_check_out` DATETIME NOT NULL,
  `actual_check_in` DATETIME NULL,
  `actual_check_out` DATETIME NULL,
  `status` VARCHAR(30) NOT NULL DEFAULT 'active', -- active, completed, extended
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `ix_bss_stays_reservation` (`reservation_id`),
  INDEX `ix_bss_stays_room` (`room_id`),
  CONSTRAINT `fk_bss_stays_reservation` FOREIGN KEY (`reservation_id`) REFERENCES `bss_reservations` (`reservation_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bss_stays_room` FOREIGN KEY (`room_id`) REFERENCES `bss_rooms` (`room_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bss_stays_guest` FOREIGN KEY (`primary_guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_automation_events` (
  `event_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `event_type` VARCHAR(50) NOT NULL, -- checkout_housekeeping_dispatched, digital_key_revoked
  `stay_id` BIGINT NULL,
  `room_id` BIGINT NULL,
  `payload` JSON NULL,
  `dispatched_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `ix_bss_auto_stay` (`stay_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 5. Folios, Charges, Payments & Billing
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `bss_revenue_categories` (
  `category_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL,
  `code` VARCHAR(20) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_folios` (
  `folio_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `folio_uuid` CHAR(36) NOT NULL UNIQUE,
  `stay_id` BIGINT NOT NULL,
  `folio_number` VARCHAR(30) NOT NULL UNIQUE,
  `total_charges` DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  `total_payments` DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  `balance` DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  `status` VARCHAR(20) NOT NULL DEFAULT 'open', -- open, closed, voided
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `ix_bss_folios_stay` (`stay_id`),
  CONSTRAINT `fk_bss_folios_stay` FOREIGN KEY (`stay_id`) REFERENCES `bss_stays` (`stay_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_folio_charges` (
  `charge_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `folio_id` BIGINT NOT NULL,
  `category_id` BIGINT NOT NULL,
  `description` VARCHAR(255) NOT NULL,
  `amount` DECIMAL(12, 2) NOT NULL,
  `tax_amount` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
  `charged_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_charges_folio` FOREIGN KEY (`folio_id`) REFERENCES `bss_folios` (`folio_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_charges_cat` FOREIGN KEY (`category_id`) REFERENCES `bss_revenue_categories` (`category_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_payment_methods_config` (
  `method_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL,
  `code` VARCHAR(20) NOT NULL UNIQUE,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_payments` (
  `payment_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `payment_uuid` CHAR(36) NOT NULL UNIQUE,
  `folio_id` BIGINT NOT NULL,
  `method_id` BIGINT NOT NULL,
  `amount` DECIMAL(14, 2) NOT NULL,
  `transaction_reference` VARCHAR(100) NULL,
  `payment_status` VARCHAR(20) NOT NULL DEFAULT 'successful',
  `received_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_payments_folio` FOREIGN KEY (`folio_id`) REFERENCES `bss_folios` (`folio_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bss_payments_method` FOREIGN KEY (`method_id`) REFERENCES `bss_payment_methods_config` (`method_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_invoices` (
  `invoice_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `invoice_uuid` CHAR(36) NOT NULL UNIQUE,
  `folio_id` BIGINT NOT NULL,
  `invoice_number` VARCHAR(50) NOT NULL UNIQUE,
  `total_amount` DECIMAL(14, 2) NOT NULL,
  `tax_total` DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
  `issued_date` DATE NOT NULL,
  `pdf_url` VARCHAR(255) NULL,
  CONSTRAINT `fk_bss_invoices_folio` FOREIGN KEY (`folio_id`) REFERENCES `bss_folios` (`folio_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_orders` (
  `order_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `order_uuid` CHAR(36) NOT NULL UNIQUE,
  `stay_id` BIGINT NOT NULL,
  `order_type` VARCHAR(30) NOT NULL DEFAULT 'room_service', -- room_service, spa, dining
  `total_amount` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_orders_stay` FOREIGN KEY (`stay_id`) REFERENCES `bss_stays` (`stay_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 6. Operations, Housekeeping & Maintenance
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `bss_housekeeping_tasks` (
  `task_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `task_uuid` CHAR(36) NOT NULL UNIQUE,
  `room_id` BIGINT NOT NULL,
  `task_type` VARCHAR(50) NOT NULL DEFAULT 'routine_clean', -- routine_clean, deep_clean, inspection
  `priority` VARCHAR(20) NOT NULL DEFAULT 'normal',
  `assigned_to` VARCHAR(36) NULL, -- oss_app_user.id
  `status` VARCHAR(30) NOT NULL DEFAULT 'pending', -- pending, in_progress, completed
  `scheduled_at` DATETIME NOT NULL,
  `completed_at` DATETIME NULL,
  INDEX `ix_bss_hk_room` (`room_id`),
  INDEX `ix_bss_hk_assigned` (`assigned_to`),
  CONSTRAINT `fk_bss_hk_room` FOREIGN KEY (`room_id`) REFERENCES `bss_rooms` (`room_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_service_requests` (
  `service_request_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `service_request_uuid` CHAR(36) NOT NULL UNIQUE,
  `stay_id` BIGINT NOT NULL,
  `request_type` VARCHAR(50) NOT NULL,
  `description` TEXT NULL,
  `assigned_to` VARCHAR(36) NULL, -- oss_app_user.id
  `status` VARCHAR(30) NOT NULL DEFAULT 'open',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` DATETIME NULL,
  CONSTRAINT `fk_bss_sr_stay` FOREIGN KEY (`stay_id`) REFERENCES `bss_stays` (`stay_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_maintenance_work_orders` (
  `work_order_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `work_order_uuid` CHAR(36) NOT NULL UNIQUE,
  `room_id` BIGINT NOT NULL,
  `oss_alert_id` CHAR(36) NULL, -- Cross-system bridge to oss_device_alert.id
  `title` VARCHAR(150) NOT NULL,
  `description` TEXT NULL,
  `priority` VARCHAR(20) NOT NULL DEFAULT 'medium',
  `assigned_technician_id` VARCHAR(36) NULL, -- oss_app_user.id
  `cost_estimate` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
  `status` VARCHAR(30) NOT NULL DEFAULT 'open',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `resolved_at` DATETIME NULL,
  INDEX `ix_bss_wo_room` (`room_id`),
  INDEX `ix_bss_wo_oss_alert` (`oss_alert_id`),
  CONSTRAINT `fk_bss_wo_room` FOREIGN KEY (`room_id`) REFERENCES `bss_rooms` (`room_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_room_conditions` (
  `condition_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `room_id` BIGINT NOT NULL,
  `oss_device_alert_id` CHAR(36) NULL, -- Cross-system bridge to oss_device_alert.id
  `issue_category` VARCHAR(50) NOT NULL, -- HVAC, Plumbing, Electrical, Lock
  `severity` VARCHAR(20) NOT NULL DEFAULT 'minor',
  `reported_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `ix_bss_cond_room` (`room_id`),
  INDEX `ix_bss_cond_alert` (`oss_device_alert_id`),
  CONSTRAINT `fk_bss_cond_room` FOREIGN KEY (`room_id`) REFERENCES `bss_rooms` (`room_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_digital_keys` (
  `digital_key_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `stay_id` BIGINT NOT NULL,
  `guest_id` BIGINT NOT NULL,
  `key_pass_code` VARCHAR(50) NOT NULL,
  `valid_from` DATETIME NOT NULL,
  `valid_until` DATETIME NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'active', -- active, revoked, expired
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `ix_bss_keys_stay` (`stay_id`),
  CONSTRAINT `fk_bss_keys_stay` FOREIGN KEY (`stay_id`) REFERENCES `bss_stays` (`stay_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_keys_guest` FOREIGN KEY (`guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_smart_access_log` (
  `access_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `digital_key_id` BIGINT NOT NULL,
  `room_id` BIGINT NOT NULL,
  `access_result` VARCHAR(20) NOT NULL, -- granted, denied
  `unlocked_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_access_key` FOREIGN KEY (`digital_key_id`) REFERENCES `bss_digital_keys` (`digital_key_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_access_room` FOREIGN KEY (`room_id`) REFERENCES `bss_rooms` (`room_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_iot_control_events` (
  `control_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `stay_id` BIGINT NOT NULL,
  `room_id` BIGINT NOT NULL,
  `target_device_role` VARCHAR(50) NOT NULL, -- thermostat, lights, dnd
  `command_payload` JSON NOT NULL,
  `requested_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_iot_stay` FOREIGN KEY (`stay_id`) REFERENCES `bss_stays` (`stay_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_iot_room` FOREIGN KEY (`room_id`) REFERENCES `bss_rooms` (`room_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 7. Events, Loyalty, Marketing & Governance
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `bss_events` (
  `event_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `property_id` BIGINT NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `event_type` VARCHAR(50) NOT NULL, -- banquet, conference, wedding
  `start_datetime` DATETIME NOT NULL,
  `end_datetime` DATETIME NOT NULL,
  `attendee_count` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(20) NOT NULL DEFAULT 'confirmed', -- confirmed, cancelled (cancel-only lifecycle)
  CONSTRAINT `fk_bss_events_prop` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_public_holidays` (
  `holiday_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `property_id` BIGINT NOT NULL,
  `holiday_date` DATE NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `is_recurring` TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY `uq_bss_holiday_date` (`property_id`, `holiday_date`),
  CONSTRAINT `fk_bss_holiday_prop` FOREIGN KEY (`property_id`) REFERENCES `bss_properties` (`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_loyalty_programs` (
  `program_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL,
  `code` VARCHAR(20) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_loyalty_tiers` (
  `tier_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `program_id` BIGINT NOT NULL,
  `tier_name` VARCHAR(50) NOT NULL,
  `min_points` INT NOT NULL DEFAULT 0,
  `point_multiplier` DECIMAL(3, 2) NOT NULL DEFAULT 1.00,
  CONSTRAINT `fk_bss_tier_program` FOREIGN KEY (`program_id`) REFERENCES `bss_loyalty_programs` (`program_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_loyalty_accounts` (
  `account_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `guest_id` BIGINT NOT NULL UNIQUE,
  `program_id` BIGINT NOT NULL,
  `tier_id` BIGINT NOT NULL,
  `points_balance` INT NOT NULL DEFAULT 0,
  CONSTRAINT `fk_bss_la_guest` FOREIGN KEY (`guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_la_program` FOREIGN KEY (`program_id`) REFERENCES `bss_loyalty_programs` (`program_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bss_la_tier` FOREIGN KEY (`tier_id`) REFERENCES `bss_loyalty_tiers` (`tier_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_loyalty_transactions` (
  `transaction_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `account_id` BIGINT NOT NULL,
  `points` INT NOT NULL,
  `transaction_type` VARCHAR(30) NOT NULL, -- earned_stay, earned_fnb, redeemed
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_lt_account` FOREIGN KEY (`account_id`) REFERENCES `bss_loyalty_accounts` (`account_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_promotions` (
  `promotion_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `code` VARCHAR(30) NOT NULL UNIQUE,
  `title` VARCHAR(150) NOT NULL,
  `discount_type` VARCHAR(20) NOT NULL DEFAULT 'percentage', -- percentage, fixed_amount
  `discount_value` DECIMAL(10, 2) NOT NULL,
  `valid_from` DATE NOT NULL,
  `valid_until` DATE NOT NULL,
  `is_stackable` TINYINT(1) NOT NULL DEFAULT 0,
  `per_guest_limit` INT NOT NULL DEFAULT 1,
  `max_redemptions` INT NOT NULL DEFAULT 1000,
  `status` VARCHAR(20) NOT NULL DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_promo_redemptions` (
  `redemption_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `promotion_id` BIGINT NOT NULL,
  `reservation_id` BIGINT NOT NULL,
  `guest_id` BIGINT NOT NULL,
  `discount_applied` DECIMAL(10, 2) NOT NULL,
  `redeemed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_pr_promo` FOREIGN KEY (`promotion_id`) REFERENCES `bss_promotions` (`promotion_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bss_pr_res` FOREIGN KEY (`reservation_id`) REFERENCES `bss_reservations` (`reservation_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_pr_guest` FOREIGN KEY (`guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_campaigns` (
  `campaign_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(150) NOT NULL,
  `channel` VARCHAR(50) NOT NULL DEFAULT 'email',
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_campaign_enrollments` (
  `enrollment_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `campaign_id` BIGINT NOT NULL,
  `guest_id` BIGINT NOT NULL,
  `enrolled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_bss_campaign_guest` (`campaign_id`, `guest_id`),
  CONSTRAINT `fk_bss_ce_camp` FOREIGN KEY (`campaign_id`) REFERENCES `bss_campaigns` (`campaign_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_ce_guest` FOREIGN KEY (`guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bss_audit_trail` (
  `audit_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `entity_name` VARCHAR(50) NOT NULL,
  `entity_id` BIGINT NOT NULL,
  `action` VARCHAR(20) NOT NULL, -- create, update, delete
  `user_id` VARCHAR(36) NOT NULL, -- oss_app_user.id
  `changes` JSON NULL,
  `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `ix_bss_audit_entity` (`entity_name`, `entity_id`),
  INDEX `ix_bss_audit_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 8. Sustainability & Carbon Accounting
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `measurement_units` (
  `unit_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL,
  `symbol` VARCHAR(15) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `emission_factors` (
  `factor_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `region_code` VARCHAR(20) NOT NULL,
  `source_type` VARCHAR(50) NOT NULL DEFAULT 'electricity',
  `factor_value` DECIMAL(10, 6) NOT NULL, -- kgCO2e per unit
  `unit_id` BIGINT NOT NULL,
  `effective_year` INT NOT NULL,
  CONSTRAINT `fk_bss_ef_unit` FOREIGN KEY (`unit_id`) REFERENCES `measurement_units` (`unit_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `carbon_calculations` (
  `calc_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `stay_id` BIGINT NOT NULL,
  `total_energy_kwh` DECIMAL(12, 3) NOT NULL DEFAULT 0.000,
  `calculated_co2_kg` DECIMAL(12, 3) NOT NULL DEFAULT 0.000,
  `calculated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_carbon_stay` FOREIGN KEY (`stay_id`) REFERENCES `bss_stays` (`stay_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cm_points_ledger` (
  `entry_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `guest_id` BIGINT NOT NULL,
  `stay_id` BIGINT NOT NULL,
  `green_points_awarded` INT NOT NULL DEFAULT 0,
  `carbon_saved_kg` DECIMAL(10, 3) NOT NULL DEFAULT 0.000,
  `awarded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_bss_cm_guest` FOREIGN KEY (`guest_id`) REFERENCES `bss_guests` (`guest_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bss_cm_stay` FOREIGN KEY (`stay_id`) REFERENCES `bss_stays` (`stay_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
