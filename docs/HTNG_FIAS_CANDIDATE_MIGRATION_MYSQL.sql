-- CANDIDATE DDL -- NOT APPROVED (HF-39). DO NOT RUN AGAINST THE HMS DATABASE WITHOUT DBA SIGN-OFF.
-- Regenerated 2026-11-20 from backend/app/integrations/processing/sql_models.py (MySQL dialect).
-- Applied only to a disposable MySQL 8.4 container by tests/integrations (incl. test_migration_candidate.py).
-- Depends on the existing table facility(id CHAR(36)).

CREATE TABLE integration_clients (
	id CHAR(36) NOT NULL,
	client_code VARCHAR(64) NOT NULL,
	secret_hash VARCHAR(80) NOT NULL,
	secondary_secret_hash VARCHAR(80),
	secondary_expires_on DATETIME(6),
	enabled BOOL NOT NULL DEFAULT 0,
	protocols VARCHAR(64) NOT NULL,
	created_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	updated_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	CONSTRAINT pk_integration_clients PRIMARY KEY (id),
	CONSTRAINT uq_integration_clients_client_code UNIQUE (client_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE integration_facility_mappings (
	id CHAR(36) NOT NULL,
	client_id CHAR(36) NOT NULL,
	external_property_code VARCHAR(32) NOT NULL,
	normalized_property_code VARCHAR(32) COLLATE utf8mb4_bin NOT NULL,
	facility_id CHAR(36) NOT NULL,
	enabled BOOL NOT NULL DEFAULT 0,
	created_by VARCHAR(64),
	created_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	updated_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	CONSTRAINT pk_integration_facility_mappings PRIMARY KEY (id),
	CONSTRAINT uq_integration_facility_mappings_client_id_normalized_pr_dc42 UNIQUE (client_id, normalized_property_code),
	CONSTRAINT fk_integration_facility_mappings_client_id_integration_clients FOREIGN KEY(client_id) REFERENCES integration_clients (id) ON DELETE RESTRICT,
	CONSTRAINT fk_integration_facility_mappings_facility_id_facility FOREIGN KEY(facility_id) REFERENCES facility (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_integration_facility_mappings_facility_id ON integration_facility_mappings (facility_id);

CREATE TABLE integration_inbound_messages (
	id CHAR(36) NOT NULL,
	client_id CHAR(36) NOT NULL,
	facility_id CHAR(36) NOT NULL,
	protocol VARCHAR(16) NOT NULL,
	direction VARCHAR(16) NOT NULL,
	message_type VARCHAR(128) NOT NULL,
	external_message_id VARCHAR(128),
	idempotency_key VARCHAR(200) NOT NULL,
	ordering_key VARCHAR(200),
	correlation_id VARCHAR(64) NOT NULL,
	schema_version VARCHAR(64) NOT NULL,
	payload_hash VARCHAR(64) NOT NULL,
	status VARCHAR(16) NOT NULL,
	attempt_count INTEGER NOT NULL DEFAULT 0,
	max_attempts INTEGER NOT NULL,
	next_attempt_at DATETIME(6),
	lease_owner VARCHAR(96),
	lease_token VARCHAR(32),
	lease_expires_at DATETIME(6),
	last_error_code VARCHAR(64),
	last_error_category VARCHAR(32),
	received_on DATETIME(6) NOT NULL,
	completed_on DATETIME(6),
	created_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	updated_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	CONSTRAINT pk_integration_inbound_messages PRIMARY KEY (id),
	CONSTRAINT ck_integration_inbound_messages_status_valid CHECK (status IN ('RECEIVED', 'VALIDATED', 'PENDING', 'PROCESSING', 'SUCCEEDED', 'RETRY_WAIT', 'DEAD_LETTER', 'REJECTED')),
	CONSTRAINT ck_integration_inbound_messages_attempt_count_non_negative CHECK (attempt_count >= 0),
	CONSTRAINT fk_integration_inbound_messages_client_id_integration_clients FOREIGN KEY(client_id) REFERENCES integration_clients (id) ON DELETE RESTRICT,
	CONSTRAINT fk_integration_inbound_messages_facility_id_facility FOREIGN KEY(facility_id) REFERENCES facility (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_integration_inbound_messages_client_id_facility_id_or_3881 ON integration_inbound_messages (client_id, facility_id, ordering_key, received_on);
CREATE INDEX ix_integration_inbound_messages_correlation_id ON integration_inbound_messages (correlation_id);
CREATE INDEX ix_integration_inbound_messages_facility_id_status_received_on ON integration_inbound_messages (facility_id, status, received_on);
CREATE INDEX ix_integration_inbound_messages_next_attempt_at ON integration_inbound_messages (next_attempt_at);

CREATE TABLE integration_inbound_payloads (
	message_id CHAR(36) NOT NULL,
	body_canonical LONGTEXT NOT NULL,
	wire_payload MEDIUMBLOB,
	retain_until DATETIME(6),
	created_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	CONSTRAINT pk_integration_inbound_payloads PRIMARY KEY (message_id),
	CONSTRAINT fk_integration_inbound_payloads_message_id_integration_i_a480 FOREIGN KEY(message_id) REFERENCES integration_inbound_messages (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE integration_idempotency_keys (
	id BIGINT NOT NULL AUTO_INCREMENT,
	client_id CHAR(36) NOT NULL,
	facility_id CHAR(36) NOT NULL,
	idempotency_key VARCHAR(200) NOT NULL,
	fingerprint VARCHAR(64) NOT NULL,
	message_id CHAR(36) NOT NULL,
	created_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	CONSTRAINT pk_integration_idempotency_keys PRIMARY KEY (id),
	CONSTRAINT uq_integration_idempotency_keys_client_id_facility_id_id_eead UNIQUE (client_id, facility_id, idempotency_key),
	CONSTRAINT fk_integration_idempotency_keys_client_id_integration_clients FOREIGN KEY(client_id) REFERENCES integration_clients (id) ON DELETE RESTRICT,
	CONSTRAINT fk_integration_idempotency_keys_facility_id_facility FOREIGN KEY(facility_id) REFERENCES facility (id) ON DELETE RESTRICT,
	CONSTRAINT fk_integration_idempotency_keys_message_id_integration_i_4a47 FOREIGN KEY(message_id) REFERENCES integration_inbound_messages (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE integration_outbox_messages (
	id CHAR(36) NOT NULL,
	source_message_id CHAR(36),
	client_id CHAR(36) NOT NULL,
	facility_id CHAR(36) NOT NULL,
	protocol VARCHAR(16) NOT NULL,
	message_type VARCHAR(128) NOT NULL,
	correlation_id VARCHAR(64) NOT NULL,
	body_canonical LONGTEXT NOT NULL,
	payload_hash VARCHAR(64) NOT NULL,
	status VARCHAR(16) NOT NULL,
	attempt_count INTEGER NOT NULL DEFAULT 0,
	max_attempts INTEGER NOT NULL,
	next_attempt_at DATETIME(6),
	lease_owner VARCHAR(96),
	lease_token VARCHAR(32),
	lease_expires_at DATETIME(6),
	last_error_code VARCHAR(64),
	created_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	sent_on DATETIME(6),
	updated_on DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
	CONSTRAINT pk_integration_outbox_messages PRIMARY KEY (id),
	CONSTRAINT ck_integration_outbox_messages_status_valid CHECK (status IN ('PENDING', 'PROCESSING', 'SENT', 'RETRY_WAIT', 'DEAD_LETTER')),
	CONSTRAINT fk_integration_outbox_messages_source_message_id_integra_1fd2 FOREIGN KEY(source_message_id) REFERENCES integration_inbound_messages (id) ON DELETE SET NULL,
	CONSTRAINT fk_integration_outbox_messages_client_id_integration_clients FOREIGN KEY(client_id) REFERENCES integration_clients (id) ON DELETE RESTRICT,
	CONSTRAINT fk_integration_outbox_messages_facility_id_facility FOREIGN KEY(facility_id) REFERENCES facility (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_integration_outbox_messages_facility_id_status_created_on ON integration_outbox_messages (facility_id, status, created_on);
CREATE INDEX ix_integration_outbox_messages_next_attempt_at ON integration_outbox_messages (next_attempt_at);
CREATE INDEX ix_integration_outbox_messages_source_message_id ON integration_outbox_messages (source_message_id);

CREATE TABLE integration_audit_events (
	id BIGINT NOT NULL AUTO_INCREMENT,
	occurred_on DATETIME(6) NOT NULL,
	actor_type VARCHAR(16) NOT NULL,
	actor_id VARCHAR(64),
	action VARCHAR(64) NOT NULL,
	facility_id CHAR(36),
	message_id CHAR(36),
	reason VARCHAR(500),
	detail JSON,
	CONSTRAINT pk_integration_audit_events PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_integration_audit_events_facility_id_occurred_on ON integration_audit_events (facility_id, occurred_on);
CREATE INDEX ix_integration_audit_events_message_id ON integration_audit_events (message_id);

