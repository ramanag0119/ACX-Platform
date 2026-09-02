"""phase1_7 hms 92 table foundation

Revision ID: 0e2687233b59
Revises: 
Create Date: 2026-08-16 21:21:20.995681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0e2687233b59'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: Every PostgreSQL ENUM type this revision owns, frozen at generation time so
#: the migration never drifts with the models. Created once, before any table;
#: dropped once, after every table. Blueprint §2.7.
ENUM_TYPES = [
    postgresql.ENUM('room', 'restaurant', 'others', name='amenity_category'),
    postgresql.ENUM('pending', 'active', 'checkout accepted', 'checkout pending', 'checkout rejected', 'checked out', 'cancelled', name='stay_status'),
    postgresql.ENUM('pending', 'approved', name='document_approval_status'),
    postgresql.ENUM('approved', 'rejected', 'pending', name='user_document_approval_status'),
    postgresql.ENUM('ikanos', 'porta', name='request_source'),
    postgresql.ENUM('booking', 'job order', name='import_entity_type'),
    postgresql.ENUM('queued', 'success', 'error', 'processing', name='import_status'),
    postgresql.ENUM('male', 'female', 'other', name='gender'),
    postgresql.ENUM('married', 'unmarried', 'divorced', 'other', name='marital_status'),
    postgresql.ENUM('admin', 'system_user', 'manager', 'guest', 'staff', name='role_type'),
    postgresql.ENUM('admin', name='department_key'),
    postgresql.ENUM('admin', name='function_key'),
    postgresql.ENUM('unassigned', 'assigned', 'cancelled', 'completed', name='room_service_request_status'),
    postgresql.ENUM('scheduled', 'planned', 'disinfection', name='maintenance_request_type'),
    postgresql.ENUM('weekly', name='recurrence_type'),
    postgresql.ENUM('HUB', 'KLE', 'MIK', 'AIR', name='device_short_code'),
    postgresql.ENUM('Active', 'Inactive', name='device_health_status'),
    postgresql.ENUM('configured', 'bad_configuration', 'commissioned', 'decommissioned', 'under_maintenance', 'missing', name='device_config_status'),
    postgresql.ENUM('active', 'decommissioned', name='firmware_status'),
    postgresql.ENUM('Integer', 'Double', 'String', 'Date Time', name='param_data_type'),
    postgresql.ENUM('Queued', 'Processing', 'Processed', 'Error', name='command_processing_status'),
    postgresql.ENUM('DeviceData', 'DeviceAlert', 'DeviceHealth', 'LastWill', 'ServerBroadCast', 'ServerToHub', 'DeviceToIkanos', 'IkanosToDevice', name='mqtt_topic_type'),
    postgresql.ENUM('installation', 'replacement', 'troubleshoot', name='job_order_type_of_work'),
    postgresql.ENUM('pending', 'completed', name='job_order_status'),
    postgresql.ENUM('locked', 'unlocked', name='lock_event'),
    postgresql.ENUM('app', 'keypad', name='lock_unlock_mode'),
    postgresql.ENUM('warning', 'critical', name='alert_severity'),
    postgresql.ENUM('0', '1', '2', name='activity_notifier_status'),
    postgresql.ENUM('0', '1', '2', name='activity_notifier_user_type'),
    postgresql.ENUM('pending', 'processing', 'processed', 'error', name='notification_status'),
    postgresql.ENUM('email', 'sms', 'push notification', 'silent notification', name='notification_channel'),
    postgresql.ENUM('active', 'inactive', name='scheduler_job_status'),
    postgresql.ENUM('passed', 'failed', name='scheduler_execution_status'),
    postgresql.ENUM('smart room', 'service request', 'checkout', 'booking', 'guest room', name='daily_metric_type'),
]


def upgrade() -> None:
    """Create the approved 92-table HMS foundation."""
    bind = op.get_bind()

    # 1. Enum types -- exactly once each, before any table references them.
    for enum_type in ENUM_TYPES:
        enum_type.create(bind, checkfirst=False)

    # 2. Tables. Cyclic foreign keys are omitted here and added in step 3.
    op.create_table('alert_type',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_alert_type'))
    )
    op.create_table('amenity_condition',
    sa.Column('name', sa.String(length=45), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_amenity_condition'))
    )
    op.create_table('amenity_status',
    sa.Column('amenity_status_name', sa.String(length=100), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_amenity_status'))
    )
    op.create_table('attachment',
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('file_name', sa.String(length=100), nullable=False),
    sa.Column('file_path', sa.String(length=256), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attachment')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_attachment_legacy_id'))
    )
    op.create_index(op.f('ix_attachment_created_by'), 'attachment', ['created_by'], unique=False)
    op.create_index(op.f('ix_attachment_facility_id'), 'attachment', ['facility_id'], unique=False)
    op.create_table('country',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('phone_code', sa.String(length=10), nullable=False),
    sa.Column('iso_code', sa.String(length=10), nullable=True),
    sa.Column('nice_name', sa.String(length=50), nullable=False),
    sa.Column('iso3', sa.String(length=3), nullable=True),
    sa.Column('num_code', sa.SmallInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_country'))
    )
    op.create_index(op.f('ix_country_phone_code'), 'country', ['phone_code'], unique=False)
    op.create_table('device_type',
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.Column('device_short_code', postgresql.ENUM(name='device_short_code', create_type=False), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_type'))
    )
    op.create_table('entity_type',
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_entity_type'))
    )
    op.create_table('import_job',
    sa.Column('import_job_name', sa.String(length=100), nullable=True),
    sa.Column('entity_type', postgresql.ENUM(name='import_entity_type', create_type=False), nullable=False),
    sa.Column('import_status', postgresql.ENUM(name='import_status', create_type=False), server_default='queued', nullable=False),
    sa.Column('total_records', sa.Integer(), nullable=True),
    sa.Column('success_count', sa.Integer(), nullable=True),
    sa.Column('error_count', sa.Integer(), nullable=True),
    sa.Column('import_file_name', sa.String(length=100), nullable=True),
    sa.Column('error_file_name', sa.String(length=100), nullable=True),
    sa.Column('completed_on', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_import_job')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_import_job_legacy_id'))
    )
    op.create_index(op.f('ix_import_job_import_status'), 'import_job', ['import_status'], unique=False)
    op.create_table('incident_event',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_incident_event'))
    )
    op.create_table('incident_status',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_incident_status'))
    )
    op.create_table('job_order',
    sa.Column('order_reference', sa.String(length=20), nullable=False),
    sa.Column('description', sa.String(length=200), nullable=True),
    sa.Column('type_of_work', postgresql.ENUM(name='job_order_type_of_work', create_type=False), nullable=False),
    sa.Column('work_commence', sa.DateTime(timezone=True), nullable=False),
    sa.Column('estimated_completion_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('authentication_code', sa.String(length=20), nullable=False),
    sa.Column('assigned_to', sa.UUID(), nullable=True),
    sa.Column('job_order_status', postgresql.ENUM(name='job_order_status', create_type=False), server_default='pending', nullable=False),
    sa.Column('completed_on', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job_order')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_job_order_legacy_id')),
    sa.UniqueConstraint('order_reference', name=op.f('uq_job_order_order_reference'))
    )
    op.create_index(op.f('ix_job_order_assigned_to'), 'job_order', ['assigned_to'], unique=False)
    op.create_index(op.f('ix_job_order_job_order_status'), 'job_order', ['job_order_status'], unique=False)
    op.create_table('key_type',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_key_type'))
    )
    op.create_table('notification_template',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('type', postgresql.ENUM(name='notification_channel', create_type=False), nullable=False),
    sa.Column('path', sa.String(length=100), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_template')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_notification_template_legacy_id')),
    sa.UniqueConstraint('name', 'type', name='uq_notification_template_name_type')
    )
    op.create_table('occasion_type',
    sa.Column('occasion_type', sa.String(length=50), nullable=False),
    sa.Column('notification_template', sa.Text(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_occasion_type'))
    )
    op.create_table('organisation',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('org_uid', sa.String(length=3), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_organisation')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_organisation_legacy_id')),
    sa.UniqueConstraint('org_uid', name=op.f('uq_organisation_org_uid'))
    )
    op.create_table('other_device',
    sa.Column('msg_id', sa.String(length=255), nullable=True),
    sa.Column('device_name', sa.String(length=225), nullable=True),
    sa.Column('voltage', sa.DOUBLE_PRECISION(), nullable=True),
    sa.Column('current', sa.DOUBLE_PRECISION(), nullable=True),
    sa.Column('power', sa.DOUBLE_PRECISION(), nullable=True),
    sa.Column('power_factor', sa.DOUBLE_PRECISION(), nullable=True),
    sa.Column('all_energy', sa.DOUBLE_PRECISION(), nullable=True),
    sa.Column('thirty_day_energy', sa.DOUBLE_PRECISION(), nullable=True),
    sa.Column('today_energy', sa.DOUBLE_PRECISION(), nullable=True),
    sa.Column('current_hour_energy', sa.DOUBLE_PRECISION(), nullable=True),
    sa.Column('ec', sa.DOUBLE_PRECISION(), nullable=True),
    sa.Column('msg_string', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_other_device')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_other_device_legacy_id'))
    )
    op.create_index('ix_other_device_device_name_timestamp', 'other_device', ['device_name', 'timestamp'], unique=False)
    op.create_table('promo_code',
    sa.Column('offer_name', sa.String(length=100), nullable=True),
    sa.Column('promo_code', sa.String(length=20), nullable=False),
    sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expiry_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('discount_percentage', sa.SmallInteger(), nullable=True),
    sa.Column('max_discount_value', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('min_order_value', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('promo_code_icon', sa.UUID(), nullable=True),
    sa.Column('promo_code_description', sa.String(length=250), nullable=True),
    sa.Column('offered_by', sa.String(length=100), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_promo_code')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_promo_code_legacy_id')),
    sa.UniqueConstraint('promo_code', name=op.f('uq_promo_code_promo_code'))
    )
    op.create_index(op.f('ix_promo_code_expiry_time'), 'promo_code', ['expiry_time'], unique=False)
    op.create_index(op.f('ix_promo_code_status'), 'promo_code', ['status'], unique=False)
    op.create_table('role_module',
    sa.Column('module_name', sa.String(length=100), nullable=False),
    sa.Column('read_applicable', sa.Boolean(), nullable=True),
    sa.Column('write_applicable', sa.Boolean(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_role_module'))
    )
    op.create_table('scheduler_job',
    sa.Column('job_key', sa.String(length=100), nullable=False),
    sa.Column('job_name', sa.String(length=50), nullable=False),
    sa.Column('job_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', postgresql.ENUM(name='scheduler_job_status', create_type=False), nullable=False),
    sa.Column('is_dynamic_job', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_scheduler_job')),
    sa.UniqueConstraint('job_key', name=op.f('uq_scheduler_job_job_key')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_scheduler_job_legacy_id'))
    )
    op.create_table('service_status',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_service_status'))
    )
    op.create_table('service_type',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_service_type'))
    )
    op.create_table('stay',
    sa.Column('internal_stay_ref_number', sa.String(length=100), nullable=False),
    sa.Column('external_stay_ref_number', sa.String(length=100), nullable=True),
    sa.Column('booking_user_id', sa.UUID(), nullable=False),
    sa.Column('no_of_rooms', sa.SmallInteger(), server_default='0', nullable=True),
    sa.Column('no_of_guests', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('expected_checkin_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expected_checkout_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actual_checkin_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('actual_checkout_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('gst', sa.String(length=20), nullable=True),
    sa.Column('checkout_initiated_by', sa.UUID(), nullable=True),
    sa.Column('document_approval_status', postgresql.ENUM(name='document_approval_status', create_type=False), server_default='pending', nullable=False),
    sa.Column('status', postgresql.ENUM(name='stay_status', create_type=False), server_default='pending', nullable=True),
    sa.Column('request_source', postgresql.ENUM(name='request_source', create_type=False), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('modified_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stay')),
    sa.UniqueConstraint('internal_stay_ref_number', name=op.f('uq_stay_internal_stay_ref_number')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_stay_legacy_id'))
    )
    op.create_index(op.f('ix_stay_booking_user_id'), 'stay', ['booking_user_id'], unique=False)
    op.create_index(op.f('ix_stay_expected_checkin_time'), 'stay', ['expected_checkin_time'], unique=False)
    op.create_index(op.f('ix_stay_expected_checkout_time'), 'stay', ['expected_checkout_time'], unique=False)
    op.create_index(op.f('ix_stay_status'), 'stay', ['status'], unique=False)
    op.create_table('user_token',
    sa.Column('token', sa.String(length=36), nullable=False),
    sa.Column('app_user_id', sa.UUID(), nullable=False),
    sa.Column('is_expired', sa.Boolean(), server_default='false', nullable=True),
    sa.Column('expired_on', sa.DateTime(timezone=True), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_token')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_user_token_legacy_id')),
    sa.UniqueConstraint('token', name=op.f('uq_user_token_token'))
    )
    op.create_index(op.f('ix_user_token_app_user_id'), 'user_token', ['app_user_id'], unique=False)
    op.create_table('activity_type',
    sa.Column('activity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_type_id', sa.SmallInteger(), nullable=False),
    sa.Column('notification_type', sa.CHAR(length=3), nullable=False),
    sa.Column('is_subscribable', sa.Boolean(), server_default='true', nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['entity_type_id'], ['entity_type.id'], name=op.f('fk_activity_type_entity_type_id_entity_type'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_activity_type'))
    )
    op.create_index(op.f('ix_activity_type_entity_type_id'), 'activity_type', ['entity_type_id'], unique=False)
    op.create_table('app_user',
    sa.Column('user_uid', sa.String(length=72), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=True),
    sa.Column('email', sa.String(length=256), nullable=True),
    sa.Column('country', sa.SmallInteger(), nullable=True),
    sa.Column('phone_number', sa.String(length=15), nullable=False),
    sa.Column('alternate_phone_number', sa.String(length=15), nullable=True),
    sa.Column('gender', postgresql.ENUM(name='gender', create_type=False), nullable=True),
    sa.Column('dob', sa.Date(), nullable=True),
    sa.Column('is_child', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('age', sa.SmallInteger(), nullable=True),
    sa.Column('is_staff', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('date_of_joining', sa.DateTime(timezone=True), nullable=True),
    sa.Column('date_of_termination', sa.DateTime(timezone=True), nullable=True),
    sa.Column('supervisor', sa.UUID(), nullable=True),
    sa.Column('address', sa.String(length=1000), nullable=True),
    sa.Column('nationality', sa.SmallInteger(), nullable=True),
    sa.Column('marital_status', postgresql.ENUM(name='marital_status', create_type=False), nullable=True),
    sa.Column('job_function_id', sa.UUID(), nullable=True),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('emp_id', sa.String(length=20), nullable=True),
    sa.Column('user_name', sa.String(length=100), nullable=True),
    sa.Column('password_hash', sa.String(length=100), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['country'], ['country.id'], name=op.f('fk_app_user_country_country'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['nationality'], ['country.id'], name=op.f('fk_app_user_nationality_country'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_app_user')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_app_user_legacy_id')),
    sa.UniqueConstraint('user_name', name=op.f('uq_app_user_user_name')),
    sa.UniqueConstraint('user_uid', name=op.f('uq_app_user_user_uid'))
    )
    op.create_index(op.f('ix_app_user_department_id'), 'app_user', ['department_id'], unique=False)
    op.create_index(op.f('ix_app_user_email'), 'app_user', ['email'], unique=False)
    op.create_index(op.f('ix_app_user_is_staff'), 'app_user', ['is_staff'], unique=False)
    op.create_index(op.f('ix_app_user_job_function_id'), 'app_user', ['job_function_id'], unique=False)
    op.create_index('ix_app_user_metadata_gin', 'app_user', ['metadata'], unique=False, postgresql_using='gin')
    op.create_index(op.f('ix_app_user_phone_number'), 'app_user', ['phone_number'], unique=False)
    op.create_table('command_type',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('device_type_id', sa.SmallInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['device_type_id'], ['device_type.id'], name=op.f('fk_command_type_device_type_id_device_type'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_command_type'))
    )
    op.create_index(op.f('ix_command_type_device_type_id'), 'command_type', ['device_type_id'], unique=False)
    op.create_table('device_param',
    sa.Column('device_type', sa.SmallInteger(), nullable=False),
    sa.Column('param_name', sa.String(length=50), nullable=False),
    sa.Column('data_type', postgresql.ENUM(name='param_data_type', create_type=False), nullable=True),
    sa.Column('unit', sa.String(length=20), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['device_type'], ['device_type.id'], name=op.f('fk_device_param_device_type_device_type'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_param'))
    )
    op.create_index(op.f('ix_device_param_device_type'), 'device_param', ['device_type'], unique=False)
    op.create_table('facility',
    sa.Column('org_id', sa.UUID(), nullable=False),
    sa.Column('facility_uid', sa.String(length=3), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('currency_id', sa.SmallInteger(), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('state', sa.String(length=100), nullable=True),
    sa.Column('pin_code', sa.String(length=20), nullable=True),
    sa.Column('guest_rooms', sa.Integer(), nullable=True),
    sa.Column('email', sa.String(length=500), nullable=False),
    sa.Column('additional_email', sa.String(length=500), nullable=True),
    sa.Column('google_map_link', sa.String(length=256), nullable=True),
    sa.Column('cloud_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('facility_image_id', sa.UUID(), nullable=True),
    sa.Column('default_key_user', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organisation.id'], name=op.f('fk_facility_org_id_organisation'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_facility')),
    sa.UniqueConstraint('facility_uid', name=op.f('uq_facility_facility_uid')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_facility_legacy_id'))
    )
    op.create_index(op.f('ix_facility_org_id'), 'facility', ['org_id'], unique=False)
    op.create_table('firmware',
    sa.Column('device_type_id', sa.SmallInteger(), nullable=False),
    sa.Column('firmware_version', sa.String(length=20), nullable=False),
    sa.Column('firmware_filename', sa.String(length=500), nullable=False),
    sa.Column('firmware_url', sa.String(length=500), nullable=False),
    sa.Column('firmware_size', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('crc', sa.Text(), nullable=False),
    sa.Column('release_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('release_notes', sa.Text(), nullable=True),
    sa.Column('decommission_reason', sa.String(length=200), nullable=True),
    sa.Column('status', postgresql.ENUM(name='firmware_status', create_type=False), server_default='active', nullable=False),
    sa.Column('uploaded_by', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['device_type_id'], ['device_type.id'], name=op.f('fk_firmware_device_type_id_device_type'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_firmware')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_firmware_legacy_id'))
    )
    op.create_index(op.f('ix_firmware_device_type_id'), 'firmware', ['device_type_id'], unique=False)
    op.create_table('notification',
    sa.Column('created_by', sa.String(length=100), nullable=False),
    sa.Column('status', postgresql.ENUM(name='notification_status', create_type=False), nullable=False),
    sa.Column('reference_id', sa.BigInteger(), nullable=True),
    sa.Column('template_id', sa.UUID(), nullable=True),
    sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['template_id'], ['notification_template.id'], name=op.f('fk_notification_template_id_notification_template'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_notification_legacy_id'))
    )
    op.create_index(op.f('ix_notification_reference_id'), 'notification', ['reference_id'], unique=False)
    op.create_index(op.f('ix_notification_status'), 'notification', ['status'], unique=False)
    op.create_index(op.f('ix_notification_template_id'), 'notification', ['template_id'], unique=False)
    op.create_table('scheduler_job_execution',
    sa.Column('scheduler_job_id', sa.UUID(), nullable=False),
    sa.Column('job_execution_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('job_response', sa.LargeBinary(), nullable=True),
    sa.Column('status', postgresql.ENUM(name='scheduler_execution_status', create_type=False), nullable=False),
    sa.Column('job_run_duration', sa.Integer(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['scheduler_job_id'], ['scheduler_job.id'], name=op.f('fk_scheduler_job_execution_scheduler_job_id_scheduler_job'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_scheduler_job_execution')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_scheduler_job_execution_legacy_id'))
    )
    op.create_index(op.f('ix_scheduler_job_execution_job_execution_date'), 'scheduler_job_execution', ['job_execution_date'], unique=False)
    op.create_index(op.f('ix_scheduler_job_execution_scheduler_job_id'), 'scheduler_job_execution', ['scheduler_job_id'], unique=False)
    op.create_table('user_device',
    sa.Column('app_user_id', sa.UUID(), nullable=False),
    sa.Column('mobile_model', sa.String(length=100), nullable=True),
    sa.Column('mobile_os', sa.String(length=50), nullable=True),
    sa.Column('device_token', sa.String(length=200), nullable=True),
    sa.Column('is_mobile_token', sa.Boolean(), nullable=True),
    sa.Column('user_token_id', sa.UUID(), nullable=True),
    sa.Column('stay_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_user_device_stay_id_stay'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_token_id'], ['user_token.id'], name=op.f('fk_user_device_user_token_id_user_token'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_device')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_user_device_legacy_id'))
    )
    op.create_index(op.f('ix_user_device_app_user_id'), 'user_device', ['app_user_id'], unique=False)
    op.create_index(op.f('ix_user_device_user_token_id'), 'user_device', ['user_token_id'], unique=False)
    op.create_table('user_document',
    sa.Column('app_user_id', sa.UUID(), nullable=False),
    sa.Column('attachment_id', sa.UUID(), nullable=False),
    sa.Column('stay_id', sa.UUID(), nullable=True),
    sa.Column('document_approval_status', postgresql.ENUM(name='user_document_approval_status', create_type=False), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_user_document_stay_id_stay'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_document')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_user_document_legacy_id'))
    )
    op.create_index(op.f('ix_user_document_app_user_id'), 'user_document', ['app_user_id'], unique=False)
    op.create_index(op.f('ix_user_document_stay_id'), 'user_document', ['stay_id'], unique=False)
    op.create_table('activity',
    sa.Column('activity_type_id', sa.SmallInteger(), nullable=False),
    sa.Column('entity_type_id', sa.SmallInteger(), nullable=False),
    sa.Column('entity_id', sa.BigInteger(), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('actor_id', sa.UUID(), nullable=False),
    sa.Column('stay_id', sa.UUID(), nullable=True),
    sa.Column('activity_response_ids', sa.Text(), nullable=True),
    sa.Column('data_version', sa.SmallInteger(), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['activity_type_id'], ['activity_type.id'], name=op.f('fk_activity_activity_type_id_activity_type'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['entity_type_id'], ['entity_type.id'], name=op.f('fk_activity_entity_type_id_entity_type'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_activity_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_activity_stay_id_stay'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_activity')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_activity_legacy_id'))
    )
    op.create_index(op.f('ix_activity_actor_id'), 'activity', ['actor_id'], unique=False)
    op.create_index('ix_activity_created_on', 'activity', ['created_on'], unique=False)
    op.create_index('ix_activity_entity_type_id_entity_id', 'activity', ['entity_type_id', 'entity_id'], unique=False)
    op.create_index(op.f('ix_activity_facility_id'), 'activity', ['facility_id'], unique=False)
    op.create_table('amenity_type',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=False),
    sa.Column('amenity_category', postgresql.ENUM(name='amenity_category', create_type=False), server_default='others', nullable=False),
    sa.Column('image_id', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_amenity_type_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_amenity_type')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_amenity_type_legacy_id'))
    )
    op.create_index(op.f('ix_amenity_type_facility_id'), 'amenity_type', ['facility_id'], unique=False)
    op.create_table('daily_dual_data_point',
    sa.Column('metric_date', sa.Date(), nullable=False),
    sa.Column('metric_type', postgresql.ENUM(name='daily_metric_type', create_type=False), nullable=False),
    sa.Column('dp_1', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('dp_2', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_daily_dual_data_point_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('metric_date', 'metric_type', name=op.f('pk_daily_dual_data_point'))
    )
    op.create_index('ix_daily_dual_data_point_facility_id_metric_date', 'daily_dual_data_point', ['facility_id', 'metric_date'], unique=False)
    op.create_table('department',
    sa.Column('department_name', sa.String(length=255), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('department_key', postgresql.ENUM(name='department_key', create_type=False), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_department_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_department')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_department_legacy_id'))
    )
    op.create_index(op.f('ix_department_facility_id'), 'department', ['facility_id'], unique=False)
    op.create_table('facility_event',
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('venue', sa.String(length=200), nullable=True),
    sa.Column('chief_guests', sa.String(length=500), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('expected_attendees', sa.SmallInteger(), nullable=True),
    sa.Column('interested_attendees', sa.SmallInteger(), server_default='0', nullable=True),
    sa.Column('start_date_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_date_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('image_id', sa.UUID(), nullable=True),
    sa.Column('cancellation_reason', sa.Text(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_facility_event_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_facility_event')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_facility_event_legacy_id'))
    )
    op.create_index(op.f('ix_facility_event_facility_id'), 'facility_event', ['facility_id'], unique=False)
    op.create_index(op.f('ix_facility_event_start_date_time'), 'facility_event', ['start_date_time'], unique=False)
    op.create_table('facility_user',
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('app_user_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_facility_user_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('facility_id', 'app_user_id', name=op.f('pk_facility_user'))
    )
    op.create_index(op.f('ix_facility_user_app_user_id'), 'facility_user', ['app_user_id'], unique=False)
    op.create_table('feature',
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('feature_name', sa.String(length=100), nullable=False),
    sa.Column('is_smart_feature', sa.Boolean(), nullable=True),
    sa.Column('device_type', sa.SmallInteger(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['device_type'], ['device_type.id'], name=op.f('fk_feature_device_type_device_type'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_feature_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_feature')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_feature_legacy_id'))
    )
    op.create_index(op.f('ix_feature_facility_id'), 'feature', ['facility_id'], unique=False)
    op.create_table('invoice',
    sa.Column('invoice_number', sa.String(length=20), nullable=False),
    sa.Column('invoice_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('invoice_due_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('billing_user_id', sa.UUID(), nullable=False),
    sa.Column('billing_user_name', sa.String(length=100), nullable=True),
    sa.Column('billing_address', sa.String(length=500), nullable=True),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('facility_name', sa.String(length=100), nullable=True),
    sa.Column('facility_address', sa.String(length=500), nullable=True),
    sa.Column('facility_image_id', sa.UUID(), nullable=True),
    sa.Column('stay_id', sa.UUID(), nullable=False),
    sa.Column('net_amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('total_tax', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_invoice_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_invoice_stay_id_stay'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_invoice')),
    sa.UniqueConstraint('invoice_number', name=op.f('uq_invoice_invoice_number')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_invoice_legacy_id'))
    )
    op.create_index(op.f('ix_invoice_facility_id'), 'invoice', ['facility_id'], unique=False)
    op.create_index(op.f('ix_invoice_stay_id'), 'invoice', ['stay_id'], unique=False)
    op.create_table('job_function',
    sa.Column('function_name', sa.String(length=100), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('function_key', postgresql.ENUM(name='function_key', create_type=False), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_job_function_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job_function')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_job_function_legacy_id'))
    )
    op.create_index(op.f('ix_job_function_facility_id'), 'job_function', ['facility_id'], unique=False)
    op.create_table('mqtt_broker',
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('broker_name', sa.String(length=50), nullable=False),
    sa.Column('broker_ip', sa.String(length=40), nullable=True),
    sa.Column('broker_vpn_ip', sa.String(length=40), nullable=True),
    sa.Column('broker_port', sa.Integer(), nullable=True),
    sa.Column('broker_user_name', sa.String(length=50), nullable=True),
    sa.Column('broker_password', sa.String(length=50), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_mqtt_broker_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_mqtt_broker')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_mqtt_broker_legacy_id'))
    )
    op.create_index(op.f('ix_mqtt_broker_facility_id'), 'mqtt_broker', ['facility_id'], unique=False)
    op.create_table('notification_receiver',
    sa.Column('app_user_id', sa.UUID(), nullable=True),
    sa.Column('notification_id', sa.BigInteger(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=256), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('device_token', sa.String(length=200), nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['notification_id'], ['notification.id'], name=op.f('fk_notification_receiver_notification_id_notification'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_receiver')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_notification_receiver_legacy_id'))
    )
    op.create_index(op.f('ix_notification_receiver_app_user_id'), 'notification_receiver', ['app_user_id'], unique=False)
    op.create_index(op.f('ix_notification_receiver_notification_id'), 'notification_receiver', ['notification_id'], unique=False)
    op.create_table('occasion',
    sa.Column('occasion_name', sa.String(length=100), nullable=True),
    sa.Column('occasion_type', sa.SmallInteger(), nullable=False),
    sa.Column('is_repeatable', sa.Boolean(), server_default='false', nullable=True),
    sa.Column('notification_template', sa.Text(), nullable=True),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('month', sa.SmallInteger(), nullable=False),
    sa.Column('day_of_month', sa.SmallInteger(), nullable=False),
    sa.Column('app_user_id', sa.UUID(), nullable=True),
    sa.Column('notify_to_hub', sa.Boolean(), server_default='true', nullable=True),
    sa.Column('occasion_start_date', sa.Date(), nullable=False),
    sa.Column('occasion_end_date', sa.Date(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_occasion_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['occasion_type'], ['occasion_type.id'], name=op.f('fk_occasion_occasion_type_occasion_type'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_occasion')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_occasion_legacy_id'))
    )
    op.create_index(op.f('ix_occasion_facility_id'), 'occasion', ['facility_id'], unique=False)
    op.create_index(op.f('ix_occasion_occasion_start_date'), 'occasion', ['occasion_start_date'], unique=False)
    op.create_index(op.f('ix_occasion_occasion_type'), 'occasion', ['occasion_type'], unique=False)
    op.create_table('property_type',
    sa.Column('property_type_name', sa.String(length=200), nullable=False),
    sa.Column('property_type_image_id', sa.UUID(), nullable=True),
    sa.Column('levels', sa.SmallInteger(), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_property_type_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_property_type')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_property_type_legacy_id'))
    )
    op.create_index(op.f('ix_property_type_facility_id'), 'property_type', ['facility_id'], unique=False)
    op.create_table('role',
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('description', sa.String(length=200), nullable=True),
    sa.Column('role_type', postgresql.ENUM(name='role_type', create_type=False), server_default='staff', nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_role_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_role')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_role_legacy_id'))
    )
    op.create_index(op.f('ix_role_facility_id'), 'role', ['facility_id'], unique=False)
    op.create_table('service_category',
    sa.Column('service_type', sa.SmallInteger(), nullable=False),
    sa.Column('category_name', sa.String(length=100), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('category_icon', sa.UUID(), nullable=True),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('service_category_key', sa.String(length=100), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_service_category_facility_id_facility'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['service_type'], ['service_type.id'], name=op.f('fk_service_category_service_type_service_type'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_service_category')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_service_category_legacy_id'))
    )
    op.create_index(op.f('ix_service_category_facility_id'), 'service_category', ['facility_id'], unique=False)
    op.create_index(op.f('ix_service_category_service_type'), 'service_category', ['service_type'], unique=False)
    op.create_table('activity_notifier',
    sa.Column('activity_id', sa.BigInteger(), nullable=False),
    sa.Column('app_user_id', sa.UUID(), nullable=False),
    sa.Column('status', postgresql.ENUM(name='activity_notifier_status', create_type=False), nullable=False),
    sa.Column('user_type', postgresql.ENUM(name='activity_notifier_user_type', create_type=False), nullable=True),
    sa.Column('notification_type', sa.SmallInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['activity_id'], ['activity.id'], name=op.f('fk_activity_notifier_activity_id_activity'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('activity_id', 'app_user_id', name=op.f('pk_activity_notifier'))
    )
    op.create_index(op.f('ix_activity_notifier_app_user_id'), 'activity_notifier', ['app_user_id'], unique=False)
    op.create_index(op.f('ix_activity_notifier_notification_type'), 'activity_notifier', ['notification_type'], unique=False)
    op.create_index(op.f('ix_activity_notifier_status'), 'activity_notifier', ['status'], unique=False)
    op.create_index(op.f('ix_activity_notifier_user_type'), 'activity_notifier', ['user_type'], unique=False)
    op.create_table('activity_role_association',
    sa.Column('activity_type_id', sa.SmallInteger(), nullable=False),
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['activity_type_id'], ['activity_type.id'], name=op.f('fk_activity_role_association_activity_type_id_activity_type'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], name=op.f('fk_activity_role_association_role_id_role'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('activity_type_id', 'role_id', name=op.f('pk_activity_role_association'))
    )
    op.create_index(op.f('ix_activity_role_association_role_id'), 'activity_role_association', ['role_id'], unique=False)
    op.create_table('notification_result',
    sa.Column('receiver_id', sa.BigInteger(), nullable=False),
    sa.Column('type', postgresql.ENUM(name='notification_channel', create_type=False), nullable=False),
    sa.Column('status', sa.String(length=15), nullable=False),
    sa.Column('log', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['receiver_id'], ['notification_receiver.id'], name=op.f('fk_notification_result_receiver_id_notification_receiver'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_result')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_notification_result_legacy_id'))
    )
    op.create_index('ix_notification_result_created_on', 'notification_result', ['created_on'], unique=False)
    op.create_index(op.f('ix_notification_result_receiver_id'), 'notification_result', ['receiver_id'], unique=False)
    op.create_index(op.f('ix_notification_result_type'), 'notification_result', ['type'], unique=False)
    op.create_table('package',
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=False),
    sa.Column('amenity_type', sa.UUID(), nullable=False),
    sa.Column('is_sub_package', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('image_id', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['amenity_type'], ['amenity_type.id'], name=op.f('fk_package_amenity_type_amenity_type'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_package_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_package')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_package_legacy_id'))
    )
    op.create_index(op.f('ix_package_facility_id'), 'package', ['facility_id'], unique=False)
    op.create_table('property',
    sa.Column('property_name', sa.String(length=200), nullable=False),
    sa.Column('property_type_id', sa.UUID(), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_property_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['property_type_id'], ['property_type.id'], name=op.f('fk_property_property_type_id_property_type'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_property')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_property_legacy_id'))
    )
    op.create_index(op.f('ix_property_facility_id'), 'property', ['facility_id'], unique=False)
    op.create_index(op.f('ix_property_property_type_id'), 'property', ['property_type_id'], unique=False)
    op.create_table('role_module_permission',
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('module_id', sa.SmallInteger(), nullable=False),
    sa.Column('read_access', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('write_access', sa.Boolean(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['module_id'], ['role_module.id'], name=op.f('fk_role_module_permission_module_id_role_module'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], name=op.f('fk_role_module_permission_role_id_role'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('role_id', 'module_id', name=op.f('pk_role_module_permission'))
    )
    op.create_index(op.f('ix_role_module_permission_module_id'), 'role_module_permission', ['module_id'], unique=False)
    op.create_table('user_role',
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('app_user_id', sa.UUID(), nullable=False),
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_user_role_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], name=op.f('fk_user_role_role_id_role'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('facility_id', 'app_user_id', 'role_id', name=op.f('pk_user_role'))
    )
    op.create_index(op.f('ix_user_role_app_user_id'), 'user_role', ['app_user_id'], unique=False)
    op.create_index(op.f('ix_user_role_role_id'), 'user_role', ['role_id'], unique=False)
    op.create_table('package_feature',
    sa.Column('package_id', sa.UUID(), nullable=False),
    sa.Column('feature_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['feature_id'], ['feature.id'], name=op.f('fk_package_feature_feature_id_feature'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['package_id'], ['package.id'], name=op.f('fk_package_feature_package_id_package'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_package_feature')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_package_feature_legacy_id'))
    )
    op.create_index(op.f('ix_package_feature_feature_id'), 'package_feature', ['feature_id'], unique=False)
    op.create_index(op.f('ix_package_feature_package_id'), 'package_feature', ['package_id'], unique=False)
    op.create_table('property_chain',
    sa.Column('level_one_id', sa.UUID(), nullable=False),
    sa.Column('level_two_id', sa.UUID(), nullable=True),
    sa.Column('level_three_id', sa.UUID(), nullable=True),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_property_chain_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['level_one_id'], ['property.id'], name=op.f('fk_property_chain_level_one_id_property'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['level_three_id'], ['property.id'], name=op.f('fk_property_chain_level_three_id_property'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['level_two_id'], ['property.id'], name=op.f('fk_property_chain_level_two_id_property'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_property_chain')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_property_chain_legacy_id'))
    )
    op.create_index(op.f('ix_property_chain_facility_id'), 'property_chain', ['facility_id'], unique=False)
    op.create_index(op.f('ix_property_chain_level_one_id'), 'property_chain', ['level_one_id'], unique=False)
    op.create_index(op.f('ix_property_chain_level_three_id'), 'property_chain', ['level_three_id'], unique=False)
    op.create_index(op.f('ix_property_chain_level_two_id'), 'property_chain', ['level_two_id'], unique=False)
    op.create_table('stay_package',
    sa.Column('stay_id', sa.UUID(), nullable=False),
    sa.Column('package_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['package_id'], ['package.id'], name=op.f('fk_stay_package_package_id_package'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_stay_package_stay_id_stay'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stay_package')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_stay_package_legacy_id'))
    )
    op.create_index(op.f('ix_stay_package_package_id'), 'stay_package', ['package_id'], unique=False)
    op.create_index(op.f('ix_stay_package_stay_id'), 'stay_package', ['stay_id'], unique=False)
    op.create_table('sub_package',
    sa.Column('parent_package_id', sa.UUID(), nullable=False),
    sa.Column('sub_package_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['parent_package_id'], ['package.id'], name=op.f('fk_sub_package_parent_package_id_package'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['sub_package_id'], ['package.id'], name=op.f('fk_sub_package_sub_package_id_package'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('parent_package_id', 'sub_package_id', name=op.f('pk_sub_package'))
    )
    op.create_index(op.f('ix_sub_package_sub_package_id'), 'sub_package', ['sub_package_id'], unique=False)
    op.create_table('amenity',
    sa.Column('name', sa.String(length=6), nullable=False),
    sa.Column('parent_amenity_id', sa.UUID(), nullable=True),
    sa.Column('amenity_type_id', sa.UUID(), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('property_chain_id', sa.UUID(), nullable=True),
    sa.Column('package_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='2', nullable=True),
    sa.Column('is_dnd', sa.SmallInteger(), nullable=True),
    sa.Column('power_save_mode', sa.SmallInteger(), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['amenity_type_id'], ['amenity_type.id'], name=op.f('fk_amenity_amenity_type_id_amenity_type'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_amenity_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['package_id'], ['package.id'], name=op.f('fk_amenity_package_id_package'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_amenity_id'], ['amenity.id'], name=op.f('fk_amenity_parent_amenity_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['property_chain_id'], ['property_chain.id'], name=op.f('fk_amenity_property_chain_id_property_chain'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['status'], ['amenity_status.id'], name=op.f('fk_amenity_status_amenity_status'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_amenity')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_amenity_legacy_id'))
    )
    op.create_index(op.f('ix_amenity_amenity_type_id'), 'amenity', ['amenity_type_id'], unique=False)
    op.create_index(op.f('ix_amenity_facility_id'), 'amenity', ['facility_id'], unique=False)
    op.create_index('ix_amenity_metadata_gin', 'amenity', ['metadata'], unique=False, postgresql_using='gin')
    op.create_index(op.f('ix_amenity_property_chain_id'), 'amenity', ['property_chain_id'], unique=False)
    op.create_index(op.f('ix_amenity_status'), 'amenity', ['status'], unique=False)
    op.create_table('amenity_condition_status',
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('amenity_condition_id', sa.SmallInteger(), nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['amenity_condition_id'], ['amenity_condition.id'], name=op.f('fk_amenity_condition_status_amenity_condition_id_amenity_condition'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_amenity_condition_status_amenity_id_amenity'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('amenity_id', 'amenity_condition_id', name=op.f('pk_amenity_condition_status'))
    )
    op.create_index(op.f('ix_amenity_condition_status_amenity_condition_id'), 'amenity_condition_status', ['amenity_condition_id'], unique=False)
    op.create_table('device',
    sa.Column('device_uid', sa.String(length=16), nullable=True),
    sa.Column('part_number', sa.String(length=50), nullable=True),
    sa.Column('model', sa.String(length=20), nullable=True),
    sa.Column('manufacturer_name', sa.String(length=50), nullable=True),
    sa.Column('mfg_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('parent_device_id', sa.UUID(), nullable=True),
    sa.Column('device_type', sa.SmallInteger(), nullable=False),
    sa.Column('device_name', sa.String(length=100), nullable=True),
    sa.Column('appliance_name', sa.String(length=50), nullable=True),
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('authentication_code', sa.String(length=20), nullable=True),
    sa.Column('health_status', postgresql.ENUM(name='device_health_status', create_type=False), nullable=True),
    sa.Column('device_temperature', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('current_firmware_version', sa.UUID(), nullable=True),
    sa.Column('expected_firmware_version', sa.UUID(), nullable=True),
    sa.Column('device_config_status', postgresql.ENUM(name='device_config_status', create_type=False), nullable=True),
    sa.Column('is_power_off', sa.Boolean(), nullable=True),
    sa.Column('installed_on', sa.DateTime(timezone=True), nullable=True),
    sa.Column('operational_mode', sa.SmallInteger(), nullable=True),
    sa.Column('is_other_device', sa.Integer(), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_device_amenity_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['current_firmware_version'], ['firmware.id'], name=op.f('fk_device_current_firmware_version_firmware'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device_type'], ['device_type.id'], name=op.f('fk_device_device_type_device_type'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['expected_firmware_version'], ['firmware.id'], name=op.f('fk_device_expected_firmware_version_firmware'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_device_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_device_id'], ['device.id'], name=op.f('fk_device_parent_device_id_device'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device')),
    sa.UniqueConstraint('device_uid', name=op.f('uq_device_device_uid')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_device_legacy_id'))
    )
    op.create_index(op.f('ix_device_amenity_id'), 'device', ['amenity_id'], unique=False)
    op.create_index(op.f('ix_device_device_type'), 'device', ['device_type'], unique=False)
    op.create_index(op.f('ix_device_facility_id'), 'device', ['facility_id'], unique=False)
    op.create_index(op.f('ix_device_health_status'), 'device', ['health_status'], unique=False)
    op.create_index('ix_device_metadata_gin', 'device', ['metadata'], unique=False, postgresql_using='gin')
    op.create_index(op.f('ix_device_parent_device_id'), 'device', ['parent_device_id'], unique=False)
    op.create_table('energy_stat',
    sa.Column('device_name', sa.String(length=11), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('hour', sa.BigInteger(), nullable=False),
    sa.Column('energy_consumed', sa.DOUBLE_PRECISION(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_energy_stat_amenity_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_energy_stat_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('device_name', 'facility_id', 'amenity_id', 'hour', name=op.f('pk_energy_stat'))
    )
    op.create_index('ix_energy_stat_amenity_id_hour', 'energy_stat', ['amenity_id', 'hour'], unique=False)
    op.create_index('ix_energy_stat_facility_id_hour', 'energy_stat', ['facility_id', 'hour'], unique=False)
    op.create_table('job_order_amenity',
    sa.Column('job_order_id', sa.UUID(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_job_order_amenity_amenity_id_amenity'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['job_order_id'], ['job_order.id'], name=op.f('fk_job_order_amenity_job_order_id_job_order'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('job_order_id', 'amenity_id', name=op.f('pk_job_order_amenity'))
    )
    op.create_index(op.f('ix_job_order_amenity_amenity_id'), 'job_order_amenity', ['amenity_id'], unique=False)
    op.create_table('promo_code_amenity',
    sa.Column('promo_code_id', sa.UUID(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_promo_code_amenity_amenity_id_amenity'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['promo_code_id'], ['promo_code.id'], name=op.f('fk_promo_code_amenity_promo_code_id_promo_code'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('promo_code_id', 'amenity_id', name=op.f('pk_promo_code_amenity'))
    )
    op.create_index(op.f('ix_promo_code_amenity_amenity_id'), 'promo_code_amenity', ['amenity_id'], unique=False)
    op.create_table('room_allocation',
    sa.Column('stay_id', sa.UUID(), nullable=False),
    sa.Column('room_id', sa.UUID(), nullable=False),
    sa.Column('package_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['package_id'], ['package.id'], name=op.f('fk_room_allocation_package_id_package'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['room_id'], ['amenity.id'], name=op.f('fk_room_allocation_room_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_room_allocation_stay_id_stay'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_room_allocation')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_room_allocation_legacy_id'))
    )
    op.create_index(op.f('ix_room_allocation_package_id'), 'room_allocation', ['package_id'], unique=False)
    op.create_index(op.f('ix_room_allocation_room_id'), 'room_allocation', ['room_id'], unique=False)
    op.create_index(op.f('ix_room_allocation_stay_id'), 'room_allocation', ['stay_id'], unique=False)
    op.create_table('room_service_request',
    sa.Column('guest_room_id', sa.UUID(), nullable=False),
    sa.Column('stay_id', sa.UUID(), nullable=True),
    sa.Column('service_request_status', postgresql.ENUM(name='room_service_request_status', create_type=False), server_default='unassigned', nullable=True),
    sa.Column('assigned_to', sa.UUID(), nullable=True),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('completed_on', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['guest_room_id'], ['amenity.id'], name=op.f('fk_room_service_request_guest_room_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_room_service_request_stay_id_stay'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_room_service_request')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_room_service_request_legacy_id'))
    )
    op.create_index(op.f('ix_room_service_request_guest_room_id'), 'room_service_request', ['guest_room_id'], unique=False)
    op.create_index(op.f('ix_room_service_request_stay_id'), 'room_service_request', ['stay_id'], unique=False)
    op.create_table('service_category_item',
    sa.Column('item_name', sa.String(length=100), nullable=False),
    sa.Column('item_icon', sa.UUID(), nullable=True),
    sa.Column('category_id', sa.UUID(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price_per_unit', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('amenity_id', sa.UUID(), nullable=True),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_service_category_item_amenity_id_amenity'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['category_id'], ['service_category.id'], name=op.f('fk_service_category_item_category_id_service_category'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_service_category_item_facility_id_facility'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_service_category_item')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_service_category_item_legacy_id'))
    )
    op.create_index(op.f('ix_service_category_item_amenity_id'), 'service_category_item', ['amenity_id'], unique=False)
    op.create_index(op.f('ix_service_category_item_category_id'), 'service_category_item', ['category_id'], unique=False)
    op.create_index(op.f('ix_service_category_item_facility_id'), 'service_category_item', ['facility_id'], unique=False)
    op.create_index('ix_service_category_item_metadata_gin', 'service_category_item', ['metadata'], unique=False, postgresql_using='gin')
    op.create_table('service_request',
    sa.Column('service_type', sa.SmallInteger(), nullable=False),
    sa.Column('ref_number', sa.String(length=20), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('assigned_to', sa.UUID(), nullable=True),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('category_id', sa.UUID(), nullable=True),
    sa.Column('promo_code_id', sa.UUID(), nullable=True),
    sa.Column('amenity_id', sa.UUID(), nullable=True),
    sa.Column('stay_id', sa.UUID(), nullable=True),
    sa.Column('app_user_id', sa.UUID(), nullable=True),
    sa.Column('request_source', postgresql.ENUM(name='request_source', create_type=False), nullable=True),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('net_amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('total_tax', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('expected_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_on', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('status_reason', sa.String(length=100), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('updated_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_service_request_amenity_id_amenity'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['category_id'], ['service_category.id'], name=op.f('fk_service_request_category_id_service_category'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id'], ['department.id'], name=op.f('fk_service_request_department_id_department'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_service_request_facility_id_facility'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['promo_code_id'], ['promo_code.id'], name=op.f('fk_service_request_promo_code_id_promo_code'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['service_type'], ['service_type.id'], name=op.f('fk_service_request_service_type_service_type'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['status'], ['service_status.id'], name=op.f('fk_service_request_status_service_status'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_service_request_stay_id_stay'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_service_request')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_service_request_legacy_id')),
    sa.UniqueConstraint('ref_number', name=op.f('uq_service_request_ref_number'))
    )
    op.create_index(op.f('ix_service_request_amenity_id'), 'service_request', ['amenity_id'], unique=False)
    op.create_index(op.f('ix_service_request_assigned_to'), 'service_request', ['assigned_to'], unique=False)
    op.create_index(op.f('ix_service_request_category_id'), 'service_request', ['category_id'], unique=False)
    op.create_index('ix_service_request_created_on', 'service_request', ['created_on'], unique=False)
    op.create_index(op.f('ix_service_request_facility_id'), 'service_request', ['facility_id'], unique=False)
    op.create_index(op.f('ix_service_request_service_type'), 'service_request', ['service_type'], unique=False)
    op.create_index(op.f('ix_service_request_status'), 'service_request', ['status'], unique=False)
    op.create_index(op.f('ix_service_request_stay_id'), 'service_request', ['stay_id'], unique=False)
    op.create_table('stay_user',
    sa.Column('app_user_id', sa.UUID(), nullable=False),
    sa.Column('room_id', sa.UUID(), nullable=True),
    sa.Column('stay_id', sa.UUID(), nullable=False),
    sa.Column('is_key_required', sa.SmallInteger(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['room_id'], ['amenity.id'], name=op.f('fk_stay_user_room_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_stay_user_stay_id_stay'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stay_user')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_stay_user_legacy_id'))
    )
    op.create_index(op.f('ix_stay_user_app_user_id'), 'stay_user', ['app_user_id'], unique=False)
    op.create_index(op.f('ix_stay_user_room_id'), 'stay_user', ['room_id'], unique=False)
    op.create_index(op.f('ix_stay_user_stay_id'), 'stay_user', ['stay_id'], unique=False)
    op.create_table('battery_life_stat',
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('cycle_number', sa.SmallInteger(), nullable=False),
    sa.Column('initial_battery_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('latest_battery_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('battery_life', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_battery_life_stat_device_id_device'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_battery_life_stat')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_battery_life_stat_legacy_id'))
    )
    op.create_index(op.f('ix_battery_life_stat_device_id'), 'battery_life_stat', ['device_id'], unique=False)
    op.create_table('device_alert',
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('alert_type', sa.SmallInteger(), nullable=False),
    sa.Column('alert_severity', postgresql.ENUM(name='alert_severity', create_type=False), nullable=True),
    sa.Column('alert_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['alert_type'], ['alert_type.id'], name=op.f('fk_device_alert_alert_type_alert_type'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_device_alert_amenity_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_device_alert_device_id_device'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_alert')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_device_alert_legacy_id'))
    )
    op.create_index(op.f('ix_device_alert_alert_type'), 'device_alert', ['alert_type'], unique=False)
    op.create_index(op.f('ix_device_alert_amenity_id'), 'device_alert', ['amenity_id'], unique=False)
    op.create_index('ix_device_alert_created_on', 'device_alert', ['created_on'], unique=False)
    op.create_index(op.f('ix_device_alert_device_id'), 'device_alert', ['device_id'], unique=False)
    op.create_table('device_command',
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('command_type', sa.SmallInteger(), nullable=False),
    sa.Column('command_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('processing_status', postgresql.ENUM(name='command_processing_status', create_type=False), server_default='Queued', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['command_type'], ['command_type.id'], name=op.f('fk_device_command_command_type_command_type'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_device_command_device_id_device'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_command')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_device_command_legacy_id'))
    )
    op.create_index(op.f('ix_device_command_device_id'), 'device_command', ['device_id'], unique=False)
    op.create_index(op.f('ix_device_command_processing_status'), 'device_command', ['processing_status'], unique=False)
    op.create_table('device_current_stat',
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('device_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('is_other_device', sa.Integer(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_device_current_stat_device_id_device'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_current_stat')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_device_current_stat_legacy_id'))
    )
    op.create_index(op.f('ix_device_current_stat_device_id'), 'device_current_stat', ['device_id'], unique=False)
    op.create_table('device_health_stat',
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('device_health_status', postgresql.ENUM(name='device_health_status', create_type=False), nullable=False),
    sa.Column('device_temperature', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_device_health_stat_device_id_device'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_health_stat')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_device_health_stat_legacy_id'))
    )
    op.create_index('ix_device_health_stat_created_on_brin', 'device_health_stat', ['created_on'], unique=False, postgresql_using='brin')
    op.create_index('ix_device_health_stat_device_id_created_on', 'device_health_stat', ['device_id', 'created_on'], unique=False)
    op.create_table('device_stat',
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('device_param_id', sa.Integer(), nullable=False),
    sa.Column('device_param_value', sa.String(length=500), nullable=True),
    sa.Column('is_other_device', sa.Integer(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_device_stat_device_id_device'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device_param_id'], ['device_param.id'], name=op.f('fk_device_stat_device_param_id_device_param'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_stat')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_device_stat_legacy_id'))
    )
    op.create_index('ix_device_stat_device_id_timestamp', 'device_stat', ['device_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_device_stat_device_param_id'), 'device_stat', ['device_param_id'], unique=False)
    op.create_index('ix_device_stat_timestamp_brin', 'device_stat', ['timestamp'], unique=False, postgresql_using='brin')
    op.create_table('job_order_device',
    sa.Column('job_order_id', sa.UUID(), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_job_order_device_device_id_device'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['job_order_id'], ['job_order.id'], name=op.f('fk_job_order_device_job_order_id_job_order'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('job_order_id', 'device_id', name=op.f('pk_job_order_device'))
    )
    op.create_index(op.f('ix_job_order_device_device_id'), 'job_order_device', ['device_id'], unique=False)
    op.create_table('lock_activity_log',
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('app_user_id', sa.UUID(), nullable=True),
    sa.Column('event', postgresql.ENUM(name='lock_event', create_type=False), nullable=True),
    sa.Column('unlock_mode', postgresql.ENUM(name='lock_unlock_mode', create_type=False), nullable=True),
    sa.Column('lock_id', sa.UUID(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('stay_id', sa.UUID(), nullable=True),
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('key_type', sa.SmallInteger(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_lock_activity_log_amenity_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_lock_activity_log_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['key_type'], ['key_type.id'], name=op.f('fk_lock_activity_log_key_type_key_type'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['lock_id'], ['device.id'], name=op.f('fk_lock_activity_log_lock_id_device'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_lock_activity_log_stay_id_stay'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lock_activity_log')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_lock_activity_log_legacy_id'))
    )
    op.create_index(op.f('ix_lock_activity_log_amenity_id'), 'lock_activity_log', ['amenity_id'], unique=False)
    op.create_index(op.f('ix_lock_activity_log_app_user_id'), 'lock_activity_log', ['app_user_id'], unique=False)
    op.create_index(op.f('ix_lock_activity_log_facility_id'), 'lock_activity_log', ['facility_id'], unique=False)
    op.create_index('ix_lock_activity_log_lock_id_timestamp', 'lock_activity_log', ['lock_id', 'timestamp'], unique=False)
    op.create_table('maintenance_request',
    sa.Column('maintenance_request_type', postgresql.ENUM(name='maintenance_request_type', create_type=False), nullable=False),
    sa.Column('maintenance_start_date', sa.Date(), nullable=True),
    sa.Column('maintenance_end_date', sa.Date(), nullable=True),
    sa.Column('maintenance_start_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('maintenance_end_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_recurring', sa.SmallInteger(), server_default='0', nullable=True),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('category_id', sa.UUID(), nullable=True),
    sa.Column('item_id', sa.UUID(), nullable=True),
    sa.Column('facility_id', sa.UUID(), nullable=True),
    sa.Column('completed_on', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_room', sa.SmallInteger(), nullable=True),
    sa.Column('non_room_comments', sa.Text(), nullable=True),
    sa.Column('parent_id', sa.UUID(), nullable=True),
    sa.Column('maintenance_request_status', sa.SmallInteger(), nullable=False),
    sa.Column('status_reason', sa.String(length=100), nullable=True),
    sa.Column('delete_comments', sa.Text(), nullable=True),
    sa.Column('under_maintenance', sa.Boolean(), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('updated_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['service_category.id'], name=op.f('fk_maintenance_request_category_id_service_category'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id'], ['department.id'], name=op.f('fk_maintenance_request_department_id_department'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_maintenance_request_facility_id_facility'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['item_id'], ['service_category_item.id'], name=op.f('fk_maintenance_request_item_id_service_category_item'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['maintenance_request_status'], ['service_status.id'], name=op.f('fk_maintenance_request_maintenance_request_status_service_status'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_id'], ['maintenance_request.id'], name=op.f('fk_maintenance_request_parent_id_maintenance_request'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_maintenance_request')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_maintenance_request_legacy_id'))
    )
    op.create_index(op.f('ix_maintenance_request_category_id'), 'maintenance_request', ['category_id'], unique=False)
    op.create_index(op.f('ix_maintenance_request_department_id'), 'maintenance_request', ['department_id'], unique=False)
    op.create_index(op.f('ix_maintenance_request_facility_id'), 'maintenance_request', ['facility_id'], unique=False)
    op.create_index(op.f('ix_maintenance_request_item_id'), 'maintenance_request', ['item_id'], unique=False)
    op.create_index(op.f('ix_maintenance_request_maintenance_start_date'), 'maintenance_request', ['maintenance_start_date'], unique=False)
    op.create_index(op.f('ix_maintenance_request_status'), 'maintenance_request', ['status'], unique=False)
    op.create_table('mqtt_topic',
    sa.Column('mqtt_broker_id', sa.UUID(), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=True),
    sa.Column('topic_name', sa.String(length=50), nullable=False),
    sa.Column('topic_type', postgresql.ENUM(name='mqtt_topic_type', create_type=False), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_mqtt_topic_device_id_device'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['mqtt_broker_id'], ['mqtt_broker.id'], name=op.f('fk_mqtt_topic_mqtt_broker_id_mqtt_broker'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_mqtt_topic')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_mqtt_topic_legacy_id'))
    )
    op.create_index(op.f('ix_mqtt_topic_device_id'), 'mqtt_topic', ['device_id'], unique=False)
    op.create_index(op.f('ix_mqtt_topic_mqtt_broker_id'), 'mqtt_topic', ['mqtt_broker_id'], unique=False)
    op.create_table('room_service_request_item',
    sa.Column('room_service_request_id', sa.UUID(), nullable=False),
    sa.Column('service_category_item_id', sa.UUID(), nullable=False),
    sa.Column('is_processed', sa.SmallInteger(), server_default='0', nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['room_service_request_id'], ['room_service_request.id'], name=op.f('fk_room_service_request_item_room_service_request_id_room_service_request'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['service_category_item_id'], ['service_category_item.id'], name=op.f('fk_room_service_request_item_service_category_item_id_service_category_item'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_room_service_request_item')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_room_service_request_item_legacy_id'))
    )
    op.create_index(op.f('ix_room_service_request_item_room_service_request_id'), 'room_service_request_item', ['room_service_request_id'], unique=False)
    op.create_index(op.f('ix_room_service_request_item_service_category_item_id'), 'room_service_request_item', ['service_category_item_id'], unique=False)
    op.create_table('sensor_operation_stat',
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('stats_date', sa.Date(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('operation_percentage', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_sensor_operation_stat_amenity_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_sensor_operation_stat_device_id_device'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('device_id', 'stats_date', name=op.f('pk_sensor_operation_stat'))
    )
    op.create_index(op.f('ix_sensor_operation_stat_amenity_id'), 'sensor_operation_stat', ['amenity_id'], unique=False)
    op.create_index(op.f('ix_sensor_operation_stat_stats_date'), 'sensor_operation_stat', ['stats_date'], unique=False)
    op.create_table('service_request_item',
    sa.Column('service_request_id', sa.UUID(), nullable=False),
    sa.Column('item_id', sa.UUID(), nullable=True),
    sa.Column('category_id', sa.UUID(), nullable=True),
    sa.Column('quantity', sa.SmallInteger(), nullable=True),
    sa.Column('price_per_unit', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('assigned_to', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['service_category.id'], name=op.f('fk_service_request_item_category_id_service_category'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['item_id'], ['service_category_item.id'], name=op.f('fk_service_request_item_item_id_service_category_item'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['service_request_id'], ['service_request.id'], name=op.f('fk_service_request_item_service_request_id_service_request'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['status'], ['service_status.id'], name=op.f('fk_service_request_item_status_service_status'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_service_request_item')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_service_request_item_legacy_id'))
    )
    op.create_index(op.f('ix_service_request_item_category_id'), 'service_request_item', ['category_id'], unique=False)
    op.create_index(op.f('ix_service_request_item_item_id'), 'service_request_item', ['item_id'], unique=False)
    op.create_index(op.f('ix_service_request_item_service_request_id'), 'service_request_item', ['service_request_id'], unique=False)
    op.create_table('user_device_acl',
    sa.Column('app_user_id', sa.UUID(), nullable=False),
    sa.Column('device_type_id', sa.SmallInteger(), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('amenity_type_id', sa.UUID(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('stay_id', sa.UUID(), nullable=True),
    sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status_id', sa.SmallInteger(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_user_device_acl_amenity_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['amenity_type_id'], ['amenity_type.id'], name=op.f('fk_user_device_acl_amenity_type_id_amenity_type'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_user_device_acl_device_id_device'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device_type_id'], ['device_type.id'], name=op.f('fk_user_device_acl_device_type_id_device_type'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_user_device_acl_stay_id_stay'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_device_acl')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_user_device_acl_legacy_id'))
    )
    op.create_index(op.f('ix_user_device_acl_amenity_id'), 'user_device_acl', ['amenity_id'], unique=False)
    op.create_index(op.f('ix_user_device_acl_amenity_type_id'), 'user_device_acl', ['amenity_type_id'], unique=False)
    op.create_index(op.f('ix_user_device_acl_app_user_id'), 'user_device_acl', ['app_user_id'], unique=False)
    op.create_index(op.f('ix_user_device_acl_device_id'), 'user_device_acl', ['device_id'], unique=False)
    op.create_index(op.f('ix_user_device_acl_device_type_id'), 'user_device_acl', ['device_type_id'], unique=False)
    op.create_index(op.f('ix_user_device_acl_end_time'), 'user_device_acl', ['end_time'], unique=False)
    op.create_index(op.f('ix_user_device_acl_stay_id'), 'user_device_acl', ['stay_id'], unique=False)
    op.create_table('value_alert_limit_config',
    sa.Column('parameter', sa.String(length=50), nullable=False),
    sa.Column('device_name', sa.String(length=50), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=True),
    sa.Column('limit_check', sa.CHAR(length=1), nullable=False),
    sa.Column('is_percentage_value', sa.CHAR(length=3), nullable=False),
    sa.Column('nominal', sa.Integer(), nullable=True),
    sa.Column('limit_low_percentage', sa.Integer(), nullable=True),
    sa.Column('limit_high_percentage', sa.Integer(), nullable=True),
    sa.Column('limit_low_value', sa.Integer(), nullable=True),
    sa.Column('limit_high_value', sa.Integer(), nullable=True),
    sa.Column('remarks', sa.Text(), nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_value_alert_limit_config_device_id_device'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_value_alert_limit_config_facility_id_facility'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_value_alert_limit_config')),
    sa.UniqueConstraint('device_name', 'parameter', 'facility_id', name='uq_value_alert_limit_config_device_name_parameter_facility_id'),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_value_alert_limit_config_legacy_id'))
    )
    op.create_index(op.f('ix_value_alert_limit_config_device_name'), 'value_alert_limit_config', ['device_name'], unique=False)
    op.create_index(op.f('ix_value_alert_limit_config_facility_id'), 'value_alert_limit_config', ['facility_id'], unique=False)
    op.create_table('access_key',
    sa.Column('user_device_acl_id', sa.UUID(), nullable=True),
    sa.Column('app_key', sa.String(length=10), nullable=False),
    sa.Column('keypad_key', sa.String(length=10), nullable=False),
    sa.Column('key_type', sa.SmallInteger(), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=True),
    sa.Column('stay_id', sa.UUID(), nullable=True),
    sa.Column('maintenance_request_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_access_key_device_id_device'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['key_type'], ['key_type.id'], name=op.f('fk_access_key_key_type_key_type'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_request.id'], name=op.f('fk_access_key_maintenance_request_id_maintenance_request'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stay_id'], ['stay.id'], name=op.f('fk_access_key_stay_id_stay'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_device_acl_id'], ['user_device_acl.id'], name=op.f('fk_access_key_user_device_acl_id_user_device_acl'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_access_key')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_access_key_legacy_id'))
    )
    op.create_index(op.f('ix_access_key_device_id'), 'access_key', ['device_id'], unique=False)
    op.create_index(op.f('ix_access_key_key_type'), 'access_key', ['key_type'], unique=False)
    op.create_index(op.f('ix_access_key_stay_id'), 'access_key', ['stay_id'], unique=False)
    op.create_index(op.f('ix_access_key_user_device_acl_id'), 'access_key', ['user_device_acl_id'], unique=False)
    op.create_table('device_incident',
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('alert_type', sa.SmallInteger(), nullable=False),
    sa.Column('subject', sa.String(length=200), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('assigned_to', sa.UUID(), nullable=True),
    sa.Column('latest_alert_id', sa.BigInteger(), nullable=True),
    sa.Column('current_incident_status', sa.SmallInteger(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['alert_type'], ['alert_type.id'], name=op.f('fk_device_incident_alert_type_alert_type'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_device_incident_amenity_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['current_incident_status'], ['incident_status.id'], name=op.f('fk_device_incident_current_incident_status_incident_status'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_device_incident_device_id_device'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_device_incident_facility_id_facility'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['latest_alert_id'], ['device_alert.id'], name=op.f('fk_device_incident_latest_alert_id_device_alert'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_incident')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_device_incident_legacy_id'))
    )
    op.create_index(op.f('ix_device_incident_alert_type'), 'device_incident', ['alert_type'], unique=False)
    op.create_index(op.f('ix_device_incident_amenity_id'), 'device_incident', ['amenity_id'], unique=False)
    op.create_index(op.f('ix_device_incident_assigned_to'), 'device_incident', ['assigned_to'], unique=False)
    op.create_index('ix_device_incident_created_on', 'device_incident', ['created_on'], unique=False)
    op.create_index(op.f('ix_device_incident_current_incident_status'), 'device_incident', ['current_incident_status'], unique=False)
    op.create_index(op.f('ix_device_incident_device_id'), 'device_incident', ['device_id'], unique=False)
    op.create_index(op.f('ix_device_incident_facility_id'), 'device_incident', ['facility_id'], unique=False)
    op.create_index(op.f('ix_device_incident_latest_alert_id'), 'device_incident', ['latest_alert_id'], unique=False)
    op.create_table('maintenance_request_amenity',
    sa.Column('maintenance_request_id', sa.UUID(), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_maintenance_request_amenity_amenity_id_amenity'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_request.id'], name=op.f('fk_maintenance_request_amenity_maintenance_request_id_maintenance_request'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_maintenance_request_amenity')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_maintenance_request_amenity_legacy_id'))
    )
    op.create_index(op.f('ix_maintenance_request_amenity_amenity_id'), 'maintenance_request_amenity', ['amenity_id'], unique=False)
    op.create_index(op.f('ix_maintenance_request_amenity_maintenance_request_id'), 'maintenance_request_amenity', ['maintenance_request_id'], unique=False)
    op.create_table('maintenance_request_assignee',
    sa.Column('maintenance_request_id', sa.UUID(), nullable=False),
    sa.Column('app_user_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='1', nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_request.id'], name=op.f('fk_maintenance_request_assignee_maintenance_request_id_maintenance_request'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_maintenance_request_assignee')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_maintenance_request_assignee_legacy_id'))
    )
    op.create_index(op.f('ix_maintenance_request_assignee_app_user_id'), 'maintenance_request_assignee', ['app_user_id'], unique=False)
    op.create_index(op.f('ix_maintenance_request_assignee_maintenance_request_id'), 'maintenance_request_assignee', ['maintenance_request_id'], unique=False)
    op.create_table('maintenance_request_recurrence',
    sa.Column('maintenance_request_id', sa.UUID(), nullable=False),
    sa.Column('recurrence_type', postgresql.ENUM(name='recurrence_type', create_type=False), nullable=False),
    sa.Column('days_of_week', sa.SmallInteger(), nullable=True),
    sa.Column('max_no_of_occurrences', sa.SmallInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['maintenance_request_id'], ['maintenance_request.id'], name=op.f('fk_maintenance_request_recurrence_maintenance_request_id_maintenance_request'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('maintenance_request_id', name=op.f('pk_maintenance_request_recurrence'))
    )
    op.create_table('value_alert',
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('device_type_id', sa.SmallInteger(), nullable=False),
    sa.Column('device_name', sa.String(length=50), nullable=False),
    sa.Column('amenity_id', sa.UUID(), nullable=False),
    sa.Column('limit_config_id', sa.UUID(), nullable=False),
    sa.Column('device_status_id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('limit_value', sa.String(length=50), nullable=False),
    sa.Column('limit_type', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('status', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('facility_id', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_value_alert_amenity_id_amenity'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], name=op.f('fk_value_alert_device_id_device'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['device_type_id'], ['device_type.id'], name=op.f('fk_value_alert_device_type_id_device_type'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['facility_id'], ['facility.id'], name=op.f('fk_value_alert_facility_id_facility'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['limit_config_id'], ['value_alert_limit_config.id'], name=op.f('fk_value_alert_limit_config_id_value_alert_limit_config'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_value_alert')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_value_alert_legacy_id'))
    )
    op.create_index(op.f('ix_value_alert_amenity_id'), 'value_alert', ['amenity_id'], unique=False)
    op.create_index(op.f('ix_value_alert_device_id'), 'value_alert', ['device_id'], unique=False)
    op.create_index(op.f('ix_value_alert_facility_id'), 'value_alert', ['facility_id'], unique=False)
    op.create_index(op.f('ix_value_alert_limit_config_id'), 'value_alert', ['limit_config_id'], unique=False)
    op.create_index(op.f('ix_value_alert_status'), 'value_alert', ['status'], unique=False)
    op.create_index(op.f('ix_value_alert_timestamp'), 'value_alert', ['timestamp'], unique=False)
    op.create_table('incident_history',
    sa.Column('incident_id', sa.UUID(), nullable=False),
    sa.Column('incident_event_id', sa.SmallInteger(), nullable=False),
    sa.Column('incident_event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('created_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_on', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.ForeignKeyConstraint(['incident_event_id'], ['incident_event.id'], name=op.f('fk_incident_history_incident_event_id_incident_event'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['incident_id'], ['device_incident.id'], name=op.f('fk_incident_history_incident_id_device_incident'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_incident_history')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_incident_history_legacy_id'))
    )
    op.create_index(op.f('ix_incident_history_incident_event_id'), 'incident_history', ['incident_event_id'], unique=False)
    op.create_index(op.f('ix_incident_history_incident_id'), 'incident_history', ['incident_id'], unique=False)

    # 3. Cyclic foreign keys, now that every table exists.
    op.create_foreign_key(
        'fk_access_key_created_by_app_user',
        'access_key',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_activity_actor_id_app_user',
        'activity',
        'app_user',
        ['actor_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_activity_notifier_app_user_id_app_user',
        'activity_notifier',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_amenity_created_by_app_user',
        'amenity',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_amenity_type_created_by_app_user',
        'amenity_type',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_amenity_type_image_id_attachment',
        'amenity_type',
        'attachment',
        ['image_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_app_user_created_by_app_user',
        'app_user',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_app_user_department_id_department',
        'app_user',
        'department',
        ['department_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_app_user_job_function_id_job_function',
        'app_user',
        'job_function',
        ['job_function_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_app_user_supervisor_app_user',
        'app_user',
        'app_user',
        ['supervisor'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_attachment_created_by_app_user',
        'attachment',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_attachment_facility_id_facility',
        'attachment',
        'facility',
        ['facility_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_department_created_by_app_user',
        'department',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_device_alert_created_by_app_user',
        'device_alert',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_device_command_created_by_app_user',
        'device_command',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_device_created_by_app_user',
        'device',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_device_incident_assigned_to_app_user',
        'device_incident',
        'app_user',
        ['assigned_to'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_device_incident_updated_by_app_user',
        'device_incident',
        'app_user',
        ['updated_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_facility_created_by_app_user',
        'facility',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_facility_default_key_user_app_user',
        'facility',
        'app_user',
        ['default_key_user'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_facility_event_created_by_app_user',
        'facility_event',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_facility_event_image_id_attachment',
        'facility_event',
        'attachment',
        ['image_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_facility_facility_image_id_attachment',
        'facility',
        'attachment',
        ['facility_image_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_facility_user_app_user_id_app_user',
        'facility_user',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_facility_user_created_by_app_user',
        'facility_user',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_feature_created_by_app_user',
        'feature',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_firmware_created_by_app_user',
        'firmware',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_firmware_updated_by_app_user',
        'firmware',
        'app_user',
        ['updated_by'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_firmware_uploaded_by_app_user',
        'firmware',
        'app_user',
        ['uploaded_by'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_import_job_created_by_app_user',
        'import_job',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_incident_history_created_by_app_user',
        'incident_history',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_invoice_billing_user_id_app_user',
        'invoice',
        'app_user',
        ['billing_user_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_invoice_created_by_app_user',
        'invoice',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_invoice_facility_image_id_attachment',
        'invoice',
        'attachment',
        ['facility_image_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_job_function_created_by_app_user',
        'job_function',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_job_order_assigned_to_app_user',
        'job_order',
        'app_user',
        ['assigned_to'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_job_order_created_by_app_user',
        'job_order',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_lock_activity_log_app_user_id_app_user',
        'lock_activity_log',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_maintenance_request_amenity_created_by_app_user',
        'maintenance_request_amenity',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_maintenance_request_assignee_app_user_id_app_user',
        'maintenance_request_assignee',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_maintenance_request_assignee_created_by_app_user',
        'maintenance_request_assignee',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_maintenance_request_created_by_app_user',
        'maintenance_request',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_maintenance_request_updated_by_app_user',
        'maintenance_request',
        'app_user',
        ['updated_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_notification_receiver_app_user_id_app_user',
        'notification_receiver',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_occasion_app_user_id_app_user',
        'occasion',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_occasion_created_by_app_user',
        'occasion',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_organisation_created_by_app_user',
        'organisation',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_package_created_by_app_user',
        'package',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_package_feature_created_by_app_user',
        'package_feature',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_package_image_id_attachment',
        'package',
        'attachment',
        ['image_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_promo_code_amenity_created_by_app_user',
        'promo_code_amenity',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_promo_code_created_by_app_user',
        'promo_code',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_promo_code_promo_code_icon_attachment',
        'promo_code',
        'attachment',
        ['promo_code_icon'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_property_chain_created_by_app_user',
        'property_chain',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_property_created_by_app_user',
        'property',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_property_type_property_type_image_id_attachment',
        'property_type',
        'attachment',
        ['property_type_image_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_role_created_by_app_user',
        'role',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_room_allocation_created_by_app_user',
        'room_allocation',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_room_service_request_assigned_to_app_user',
        'room_service_request',
        'app_user',
        ['assigned_to'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_room_service_request_created_by_app_user',
        'room_service_request',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_service_category_category_icon_attachment',
        'service_category',
        'attachment',
        ['category_icon'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_service_category_created_by_app_user',
        'service_category',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_service_category_item_created_by_app_user',
        'service_category_item',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_service_category_item_item_icon_attachment',
        'service_category_item',
        'attachment',
        ['item_icon'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_service_request_app_user_id_app_user',
        'service_request',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_service_request_assigned_to_app_user',
        'service_request',
        'app_user',
        ['assigned_to'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_service_request_created_by_app_user',
        'service_request',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_service_request_item_assigned_to_app_user',
        'service_request_item',
        'app_user',
        ['assigned_to'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_service_request_updated_by_app_user',
        'service_request',
        'app_user',
        ['updated_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_stay_booking_user_id_app_user',
        'stay',
        'app_user',
        ['booking_user_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_stay_checkout_initiated_by_app_user',
        'stay',
        'app_user',
        ['checkout_initiated_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_stay_created_by_app_user',
        'stay',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_stay_modified_by_app_user',
        'stay',
        'app_user',
        ['modified_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_stay_user_app_user_id_app_user',
        'stay_user',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_stay_user_created_by_app_user',
        'stay_user',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_sub_package_created_by_app_user',
        'sub_package',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_user_device_acl_app_user_id_app_user',
        'user_device_acl',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_user_device_acl_created_by_app_user',
        'user_device_acl',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_user_device_app_user_id_app_user',
        'user_device',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_user_document_app_user_id_app_user',
        'user_document',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_user_document_attachment_id_attachment',
        'user_document',
        'attachment',
        ['attachment_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_user_role_app_user_id_app_user',
        'user_role',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_user_role_created_by_app_user',
        'user_role',
        'app_user',
        ['created_by'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_user_token_app_user_id_app_user',
        'user_token',
        'app_user',
        ['app_user_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    """Drop the entire 92-table foundation."""
    bind = op.get_bind()

    # 1. Break the cycles first so the tables can be dropped in any order.
    op.drop_constraint('fk_user_token_app_user_id_app_user', 'user_token', type_='foreignkey')
    op.drop_constraint('fk_user_role_created_by_app_user', 'user_role', type_='foreignkey')
    op.drop_constraint('fk_user_role_app_user_id_app_user', 'user_role', type_='foreignkey')
    op.drop_constraint('fk_user_document_attachment_id_attachment', 'user_document', type_='foreignkey')
    op.drop_constraint('fk_user_document_app_user_id_app_user', 'user_document', type_='foreignkey')
    op.drop_constraint('fk_user_device_app_user_id_app_user', 'user_device', type_='foreignkey')
    op.drop_constraint('fk_user_device_acl_created_by_app_user', 'user_device_acl', type_='foreignkey')
    op.drop_constraint('fk_user_device_acl_app_user_id_app_user', 'user_device_acl', type_='foreignkey')
    op.drop_constraint('fk_sub_package_created_by_app_user', 'sub_package', type_='foreignkey')
    op.drop_constraint('fk_stay_user_created_by_app_user', 'stay_user', type_='foreignkey')
    op.drop_constraint('fk_stay_user_app_user_id_app_user', 'stay_user', type_='foreignkey')
    op.drop_constraint('fk_stay_modified_by_app_user', 'stay', type_='foreignkey')
    op.drop_constraint('fk_stay_created_by_app_user', 'stay', type_='foreignkey')
    op.drop_constraint('fk_stay_checkout_initiated_by_app_user', 'stay', type_='foreignkey')
    op.drop_constraint('fk_stay_booking_user_id_app_user', 'stay', type_='foreignkey')
    op.drop_constraint('fk_service_request_updated_by_app_user', 'service_request', type_='foreignkey')
    op.drop_constraint('fk_service_request_item_assigned_to_app_user', 'service_request_item', type_='foreignkey')
    op.drop_constraint('fk_service_request_created_by_app_user', 'service_request', type_='foreignkey')
    op.drop_constraint('fk_service_request_assigned_to_app_user', 'service_request', type_='foreignkey')
    op.drop_constraint('fk_service_request_app_user_id_app_user', 'service_request', type_='foreignkey')
    op.drop_constraint('fk_service_category_item_item_icon_attachment', 'service_category_item', type_='foreignkey')
    op.drop_constraint('fk_service_category_item_created_by_app_user', 'service_category_item', type_='foreignkey')
    op.drop_constraint('fk_service_category_created_by_app_user', 'service_category', type_='foreignkey')
    op.drop_constraint('fk_service_category_category_icon_attachment', 'service_category', type_='foreignkey')
    op.drop_constraint('fk_room_service_request_created_by_app_user', 'room_service_request', type_='foreignkey')
    op.drop_constraint('fk_room_service_request_assigned_to_app_user', 'room_service_request', type_='foreignkey')
    op.drop_constraint('fk_room_allocation_created_by_app_user', 'room_allocation', type_='foreignkey')
    op.drop_constraint('fk_role_created_by_app_user', 'role', type_='foreignkey')
    op.drop_constraint('fk_property_type_property_type_image_id_attachment', 'property_type', type_='foreignkey')
    op.drop_constraint('fk_property_created_by_app_user', 'property', type_='foreignkey')
    op.drop_constraint('fk_property_chain_created_by_app_user', 'property_chain', type_='foreignkey')
    op.drop_constraint('fk_promo_code_promo_code_icon_attachment', 'promo_code', type_='foreignkey')
    op.drop_constraint('fk_promo_code_created_by_app_user', 'promo_code', type_='foreignkey')
    op.drop_constraint('fk_promo_code_amenity_created_by_app_user', 'promo_code_amenity', type_='foreignkey')
    op.drop_constraint('fk_package_image_id_attachment', 'package', type_='foreignkey')
    op.drop_constraint('fk_package_feature_created_by_app_user', 'package_feature', type_='foreignkey')
    op.drop_constraint('fk_package_created_by_app_user', 'package', type_='foreignkey')
    op.drop_constraint('fk_organisation_created_by_app_user', 'organisation', type_='foreignkey')
    op.drop_constraint('fk_occasion_created_by_app_user', 'occasion', type_='foreignkey')
    op.drop_constraint('fk_occasion_app_user_id_app_user', 'occasion', type_='foreignkey')
    op.drop_constraint('fk_notification_receiver_app_user_id_app_user', 'notification_receiver', type_='foreignkey')
    op.drop_constraint('fk_maintenance_request_updated_by_app_user', 'maintenance_request', type_='foreignkey')
    op.drop_constraint('fk_maintenance_request_created_by_app_user', 'maintenance_request', type_='foreignkey')
    op.drop_constraint('fk_maintenance_request_assignee_created_by_app_user', 'maintenance_request_assignee', type_='foreignkey')
    op.drop_constraint('fk_maintenance_request_assignee_app_user_id_app_user', 'maintenance_request_assignee', type_='foreignkey')
    op.drop_constraint('fk_maintenance_request_amenity_created_by_app_user', 'maintenance_request_amenity', type_='foreignkey')
    op.drop_constraint('fk_lock_activity_log_app_user_id_app_user', 'lock_activity_log', type_='foreignkey')
    op.drop_constraint('fk_job_order_created_by_app_user', 'job_order', type_='foreignkey')
    op.drop_constraint('fk_job_order_assigned_to_app_user', 'job_order', type_='foreignkey')
    op.drop_constraint('fk_job_function_created_by_app_user', 'job_function', type_='foreignkey')
    op.drop_constraint('fk_invoice_facility_image_id_attachment', 'invoice', type_='foreignkey')
    op.drop_constraint('fk_invoice_created_by_app_user', 'invoice', type_='foreignkey')
    op.drop_constraint('fk_invoice_billing_user_id_app_user', 'invoice', type_='foreignkey')
    op.drop_constraint('fk_incident_history_created_by_app_user', 'incident_history', type_='foreignkey')
    op.drop_constraint('fk_import_job_created_by_app_user', 'import_job', type_='foreignkey')
    op.drop_constraint('fk_firmware_uploaded_by_app_user', 'firmware', type_='foreignkey')
    op.drop_constraint('fk_firmware_updated_by_app_user', 'firmware', type_='foreignkey')
    op.drop_constraint('fk_firmware_created_by_app_user', 'firmware', type_='foreignkey')
    op.drop_constraint('fk_feature_created_by_app_user', 'feature', type_='foreignkey')
    op.drop_constraint('fk_facility_user_created_by_app_user', 'facility_user', type_='foreignkey')
    op.drop_constraint('fk_facility_user_app_user_id_app_user', 'facility_user', type_='foreignkey')
    op.drop_constraint('fk_facility_facility_image_id_attachment', 'facility', type_='foreignkey')
    op.drop_constraint('fk_facility_event_image_id_attachment', 'facility_event', type_='foreignkey')
    op.drop_constraint('fk_facility_event_created_by_app_user', 'facility_event', type_='foreignkey')
    op.drop_constraint('fk_facility_default_key_user_app_user', 'facility', type_='foreignkey')
    op.drop_constraint('fk_facility_created_by_app_user', 'facility', type_='foreignkey')
    op.drop_constraint('fk_device_incident_updated_by_app_user', 'device_incident', type_='foreignkey')
    op.drop_constraint('fk_device_incident_assigned_to_app_user', 'device_incident', type_='foreignkey')
    op.drop_constraint('fk_device_created_by_app_user', 'device', type_='foreignkey')
    op.drop_constraint('fk_device_command_created_by_app_user', 'device_command', type_='foreignkey')
    op.drop_constraint('fk_device_alert_created_by_app_user', 'device_alert', type_='foreignkey')
    op.drop_constraint('fk_department_created_by_app_user', 'department', type_='foreignkey')
    op.drop_constraint('fk_attachment_facility_id_facility', 'attachment', type_='foreignkey')
    op.drop_constraint('fk_attachment_created_by_app_user', 'attachment', type_='foreignkey')
    op.drop_constraint('fk_app_user_supervisor_app_user', 'app_user', type_='foreignkey')
    op.drop_constraint('fk_app_user_job_function_id_job_function', 'app_user', type_='foreignkey')
    op.drop_constraint('fk_app_user_department_id_department', 'app_user', type_='foreignkey')
    op.drop_constraint('fk_app_user_created_by_app_user', 'app_user', type_='foreignkey')
    op.drop_constraint('fk_amenity_type_image_id_attachment', 'amenity_type', type_='foreignkey')
    op.drop_constraint('fk_amenity_type_created_by_app_user', 'amenity_type', type_='foreignkey')
    op.drop_constraint('fk_amenity_created_by_app_user', 'amenity', type_='foreignkey')
    op.drop_constraint('fk_activity_notifier_app_user_id_app_user', 'activity_notifier', type_='foreignkey')
    op.drop_constraint('fk_activity_actor_id_app_user', 'activity', type_='foreignkey')
    op.drop_constraint('fk_access_key_created_by_app_user', 'access_key', type_='foreignkey')

    # 2. Tables.
    op.drop_index(op.f('ix_incident_history_incident_id'), table_name='incident_history')
    op.drop_index(op.f('ix_incident_history_incident_event_id'), table_name='incident_history')
    op.drop_table('incident_history')
    op.drop_index(op.f('ix_value_alert_timestamp'), table_name='value_alert')
    op.drop_index(op.f('ix_value_alert_status'), table_name='value_alert')
    op.drop_index(op.f('ix_value_alert_limit_config_id'), table_name='value_alert')
    op.drop_index(op.f('ix_value_alert_facility_id'), table_name='value_alert')
    op.drop_index(op.f('ix_value_alert_device_id'), table_name='value_alert')
    op.drop_index(op.f('ix_value_alert_amenity_id'), table_name='value_alert')
    op.drop_table('value_alert')
    op.drop_table('maintenance_request_recurrence')
    op.drop_index(op.f('ix_maintenance_request_assignee_maintenance_request_id'), table_name='maintenance_request_assignee')
    op.drop_index(op.f('ix_maintenance_request_assignee_app_user_id'), table_name='maintenance_request_assignee')
    op.drop_table('maintenance_request_assignee')
    op.drop_index(op.f('ix_maintenance_request_amenity_maintenance_request_id'), table_name='maintenance_request_amenity')
    op.drop_index(op.f('ix_maintenance_request_amenity_amenity_id'), table_name='maintenance_request_amenity')
    op.drop_table('maintenance_request_amenity')
    op.drop_index(op.f('ix_device_incident_latest_alert_id'), table_name='device_incident')
    op.drop_index(op.f('ix_device_incident_facility_id'), table_name='device_incident')
    op.drop_index(op.f('ix_device_incident_device_id'), table_name='device_incident')
    op.drop_index(op.f('ix_device_incident_current_incident_status'), table_name='device_incident')
    op.drop_index('ix_device_incident_created_on', table_name='device_incident')
    op.drop_index(op.f('ix_device_incident_assigned_to'), table_name='device_incident')
    op.drop_index(op.f('ix_device_incident_amenity_id'), table_name='device_incident')
    op.drop_index(op.f('ix_device_incident_alert_type'), table_name='device_incident')
    op.drop_table('device_incident')
    op.drop_index(op.f('ix_access_key_user_device_acl_id'), table_name='access_key')
    op.drop_index(op.f('ix_access_key_stay_id'), table_name='access_key')
    op.drop_index(op.f('ix_access_key_key_type'), table_name='access_key')
    op.drop_index(op.f('ix_access_key_device_id'), table_name='access_key')
    op.drop_table('access_key')
    op.drop_index(op.f('ix_value_alert_limit_config_facility_id'), table_name='value_alert_limit_config')
    op.drop_index(op.f('ix_value_alert_limit_config_device_name'), table_name='value_alert_limit_config')
    op.drop_table('value_alert_limit_config')
    op.drop_index(op.f('ix_user_device_acl_stay_id'), table_name='user_device_acl')
    op.drop_index(op.f('ix_user_device_acl_end_time'), table_name='user_device_acl')
    op.drop_index(op.f('ix_user_device_acl_device_type_id'), table_name='user_device_acl')
    op.drop_index(op.f('ix_user_device_acl_device_id'), table_name='user_device_acl')
    op.drop_index(op.f('ix_user_device_acl_app_user_id'), table_name='user_device_acl')
    op.drop_index(op.f('ix_user_device_acl_amenity_type_id'), table_name='user_device_acl')
    op.drop_index(op.f('ix_user_device_acl_amenity_id'), table_name='user_device_acl')
    op.drop_table('user_device_acl')
    op.drop_index(op.f('ix_service_request_item_service_request_id'), table_name='service_request_item')
    op.drop_index(op.f('ix_service_request_item_item_id'), table_name='service_request_item')
    op.drop_index(op.f('ix_service_request_item_category_id'), table_name='service_request_item')
    op.drop_table('service_request_item')
    op.drop_index(op.f('ix_sensor_operation_stat_stats_date'), table_name='sensor_operation_stat')
    op.drop_index(op.f('ix_sensor_operation_stat_amenity_id'), table_name='sensor_operation_stat')
    op.drop_table('sensor_operation_stat')
    op.drop_index(op.f('ix_room_service_request_item_service_category_item_id'), table_name='room_service_request_item')
    op.drop_index(op.f('ix_room_service_request_item_room_service_request_id'), table_name='room_service_request_item')
    op.drop_table('room_service_request_item')
    op.drop_index(op.f('ix_mqtt_topic_mqtt_broker_id'), table_name='mqtt_topic')
    op.drop_index(op.f('ix_mqtt_topic_device_id'), table_name='mqtt_topic')
    op.drop_table('mqtt_topic')
    op.drop_index(op.f('ix_maintenance_request_status'), table_name='maintenance_request')
    op.drop_index(op.f('ix_maintenance_request_maintenance_start_date'), table_name='maintenance_request')
    op.drop_index(op.f('ix_maintenance_request_item_id'), table_name='maintenance_request')
    op.drop_index(op.f('ix_maintenance_request_facility_id'), table_name='maintenance_request')
    op.drop_index(op.f('ix_maintenance_request_department_id'), table_name='maintenance_request')
    op.drop_index(op.f('ix_maintenance_request_category_id'), table_name='maintenance_request')
    op.drop_table('maintenance_request')
    op.drop_index('ix_lock_activity_log_lock_id_timestamp', table_name='lock_activity_log')
    op.drop_index(op.f('ix_lock_activity_log_facility_id'), table_name='lock_activity_log')
    op.drop_index(op.f('ix_lock_activity_log_app_user_id'), table_name='lock_activity_log')
    op.drop_index(op.f('ix_lock_activity_log_amenity_id'), table_name='lock_activity_log')
    op.drop_table('lock_activity_log')
    op.drop_index(op.f('ix_job_order_device_device_id'), table_name='job_order_device')
    op.drop_table('job_order_device')
    op.drop_index('ix_device_stat_timestamp_brin', table_name='device_stat', postgresql_using='brin')
    op.drop_index(op.f('ix_device_stat_device_param_id'), table_name='device_stat')
    op.drop_index('ix_device_stat_device_id_timestamp', table_name='device_stat')
    op.drop_table('device_stat')
    op.drop_index('ix_device_health_stat_device_id_created_on', table_name='device_health_stat')
    op.drop_index('ix_device_health_stat_created_on_brin', table_name='device_health_stat', postgresql_using='brin')
    op.drop_table('device_health_stat')
    op.drop_index(op.f('ix_device_current_stat_device_id'), table_name='device_current_stat')
    op.drop_table('device_current_stat')
    op.drop_index(op.f('ix_device_command_processing_status'), table_name='device_command')
    op.drop_index(op.f('ix_device_command_device_id'), table_name='device_command')
    op.drop_table('device_command')
    op.drop_index(op.f('ix_device_alert_device_id'), table_name='device_alert')
    op.drop_index('ix_device_alert_created_on', table_name='device_alert')
    op.drop_index(op.f('ix_device_alert_amenity_id'), table_name='device_alert')
    op.drop_index(op.f('ix_device_alert_alert_type'), table_name='device_alert')
    op.drop_table('device_alert')
    op.drop_index(op.f('ix_battery_life_stat_device_id'), table_name='battery_life_stat')
    op.drop_table('battery_life_stat')
    op.drop_index(op.f('ix_stay_user_stay_id'), table_name='stay_user')
    op.drop_index(op.f('ix_stay_user_room_id'), table_name='stay_user')
    op.drop_index(op.f('ix_stay_user_app_user_id'), table_name='stay_user')
    op.drop_table('stay_user')
    op.drop_index(op.f('ix_service_request_stay_id'), table_name='service_request')
    op.drop_index(op.f('ix_service_request_status'), table_name='service_request')
    op.drop_index(op.f('ix_service_request_service_type'), table_name='service_request')
    op.drop_index(op.f('ix_service_request_facility_id'), table_name='service_request')
    op.drop_index('ix_service_request_created_on', table_name='service_request')
    op.drop_index(op.f('ix_service_request_category_id'), table_name='service_request')
    op.drop_index(op.f('ix_service_request_assigned_to'), table_name='service_request')
    op.drop_index(op.f('ix_service_request_amenity_id'), table_name='service_request')
    op.drop_table('service_request')
    op.drop_index('ix_service_category_item_metadata_gin', table_name='service_category_item', postgresql_using='gin')
    op.drop_index(op.f('ix_service_category_item_facility_id'), table_name='service_category_item')
    op.drop_index(op.f('ix_service_category_item_category_id'), table_name='service_category_item')
    op.drop_index(op.f('ix_service_category_item_amenity_id'), table_name='service_category_item')
    op.drop_table('service_category_item')
    op.drop_index(op.f('ix_room_service_request_stay_id'), table_name='room_service_request')
    op.drop_index(op.f('ix_room_service_request_guest_room_id'), table_name='room_service_request')
    op.drop_table('room_service_request')
    op.drop_index(op.f('ix_room_allocation_stay_id'), table_name='room_allocation')
    op.drop_index(op.f('ix_room_allocation_room_id'), table_name='room_allocation')
    op.drop_index(op.f('ix_room_allocation_package_id'), table_name='room_allocation')
    op.drop_table('room_allocation')
    op.drop_index(op.f('ix_promo_code_amenity_amenity_id'), table_name='promo_code_amenity')
    op.drop_table('promo_code_amenity')
    op.drop_index(op.f('ix_job_order_amenity_amenity_id'), table_name='job_order_amenity')
    op.drop_table('job_order_amenity')
    op.drop_index('ix_energy_stat_facility_id_hour', table_name='energy_stat')
    op.drop_index('ix_energy_stat_amenity_id_hour', table_name='energy_stat')
    op.drop_table('energy_stat')
    op.drop_index(op.f('ix_device_parent_device_id'), table_name='device')
    op.drop_index('ix_device_metadata_gin', table_name='device', postgresql_using='gin')
    op.drop_index(op.f('ix_device_health_status'), table_name='device')
    op.drop_index(op.f('ix_device_facility_id'), table_name='device')
    op.drop_index(op.f('ix_device_device_type'), table_name='device')
    op.drop_index(op.f('ix_device_amenity_id'), table_name='device')
    op.drop_table('device')
    op.drop_index(op.f('ix_amenity_condition_status_amenity_condition_id'), table_name='amenity_condition_status')
    op.drop_table('amenity_condition_status')
    op.drop_index(op.f('ix_amenity_status'), table_name='amenity')
    op.drop_index(op.f('ix_amenity_property_chain_id'), table_name='amenity')
    op.drop_index('ix_amenity_metadata_gin', table_name='amenity', postgresql_using='gin')
    op.drop_index(op.f('ix_amenity_facility_id'), table_name='amenity')
    op.drop_index(op.f('ix_amenity_amenity_type_id'), table_name='amenity')
    op.drop_table('amenity')
    op.drop_index(op.f('ix_sub_package_sub_package_id'), table_name='sub_package')
    op.drop_table('sub_package')
    op.drop_index(op.f('ix_stay_package_stay_id'), table_name='stay_package')
    op.drop_index(op.f('ix_stay_package_package_id'), table_name='stay_package')
    op.drop_table('stay_package')
    op.drop_index(op.f('ix_property_chain_level_two_id'), table_name='property_chain')
    op.drop_index(op.f('ix_property_chain_level_three_id'), table_name='property_chain')
    op.drop_index(op.f('ix_property_chain_level_one_id'), table_name='property_chain')
    op.drop_index(op.f('ix_property_chain_facility_id'), table_name='property_chain')
    op.drop_table('property_chain')
    op.drop_index(op.f('ix_package_feature_package_id'), table_name='package_feature')
    op.drop_index(op.f('ix_package_feature_feature_id'), table_name='package_feature')
    op.drop_table('package_feature')
    op.drop_index(op.f('ix_user_role_role_id'), table_name='user_role')
    op.drop_index(op.f('ix_user_role_app_user_id'), table_name='user_role')
    op.drop_table('user_role')
    op.drop_index(op.f('ix_role_module_permission_module_id'), table_name='role_module_permission')
    op.drop_table('role_module_permission')
    op.drop_index(op.f('ix_property_property_type_id'), table_name='property')
    op.drop_index(op.f('ix_property_facility_id'), table_name='property')
    op.drop_table('property')
    op.drop_index(op.f('ix_package_facility_id'), table_name='package')
    op.drop_table('package')
    op.drop_index(op.f('ix_notification_result_type'), table_name='notification_result')
    op.drop_index(op.f('ix_notification_result_receiver_id'), table_name='notification_result')
    op.drop_index('ix_notification_result_created_on', table_name='notification_result')
    op.drop_table('notification_result')
    op.drop_index(op.f('ix_activity_role_association_role_id'), table_name='activity_role_association')
    op.drop_table('activity_role_association')
    op.drop_index(op.f('ix_activity_notifier_user_type'), table_name='activity_notifier')
    op.drop_index(op.f('ix_activity_notifier_status'), table_name='activity_notifier')
    op.drop_index(op.f('ix_activity_notifier_notification_type'), table_name='activity_notifier')
    op.drop_index(op.f('ix_activity_notifier_app_user_id'), table_name='activity_notifier')
    op.drop_table('activity_notifier')
    op.drop_index(op.f('ix_service_category_service_type'), table_name='service_category')
    op.drop_index(op.f('ix_service_category_facility_id'), table_name='service_category')
    op.drop_table('service_category')
    op.drop_index(op.f('ix_role_facility_id'), table_name='role')
    op.drop_table('role')
    op.drop_index(op.f('ix_property_type_facility_id'), table_name='property_type')
    op.drop_table('property_type')
    op.drop_index(op.f('ix_occasion_occasion_type'), table_name='occasion')
    op.drop_index(op.f('ix_occasion_occasion_start_date'), table_name='occasion')
    op.drop_index(op.f('ix_occasion_facility_id'), table_name='occasion')
    op.drop_table('occasion')
    op.drop_index(op.f('ix_notification_receiver_notification_id'), table_name='notification_receiver')
    op.drop_index(op.f('ix_notification_receiver_app_user_id'), table_name='notification_receiver')
    op.drop_table('notification_receiver')
    op.drop_index(op.f('ix_mqtt_broker_facility_id'), table_name='mqtt_broker')
    op.drop_table('mqtt_broker')
    op.drop_index(op.f('ix_job_function_facility_id'), table_name='job_function')
    op.drop_table('job_function')
    op.drop_index(op.f('ix_invoice_stay_id'), table_name='invoice')
    op.drop_index(op.f('ix_invoice_facility_id'), table_name='invoice')
    op.drop_table('invoice')
    op.drop_index(op.f('ix_feature_facility_id'), table_name='feature')
    op.drop_table('feature')
    op.drop_index(op.f('ix_facility_user_app_user_id'), table_name='facility_user')
    op.drop_table('facility_user')
    op.drop_index(op.f('ix_facility_event_start_date_time'), table_name='facility_event')
    op.drop_index(op.f('ix_facility_event_facility_id'), table_name='facility_event')
    op.drop_table('facility_event')
    op.drop_index(op.f('ix_department_facility_id'), table_name='department')
    op.drop_table('department')
    op.drop_index('ix_daily_dual_data_point_facility_id_metric_date', table_name='daily_dual_data_point')
    op.drop_table('daily_dual_data_point')
    op.drop_index(op.f('ix_amenity_type_facility_id'), table_name='amenity_type')
    op.drop_table('amenity_type')
    op.drop_index(op.f('ix_activity_facility_id'), table_name='activity')
    op.drop_index('ix_activity_entity_type_id_entity_id', table_name='activity')
    op.drop_index('ix_activity_created_on', table_name='activity')
    op.drop_index(op.f('ix_activity_actor_id'), table_name='activity')
    op.drop_table('activity')
    op.drop_index(op.f('ix_user_document_stay_id'), table_name='user_document')
    op.drop_index(op.f('ix_user_document_app_user_id'), table_name='user_document')
    op.drop_table('user_document')
    op.drop_index(op.f('ix_user_device_user_token_id'), table_name='user_device')
    op.drop_index(op.f('ix_user_device_app_user_id'), table_name='user_device')
    op.drop_table('user_device')
    op.drop_index(op.f('ix_scheduler_job_execution_scheduler_job_id'), table_name='scheduler_job_execution')
    op.drop_index(op.f('ix_scheduler_job_execution_job_execution_date'), table_name='scheduler_job_execution')
    op.drop_table('scheduler_job_execution')
    op.drop_index(op.f('ix_notification_template_id'), table_name='notification')
    op.drop_index(op.f('ix_notification_status'), table_name='notification')
    op.drop_index(op.f('ix_notification_reference_id'), table_name='notification')
    op.drop_table('notification')
    op.drop_index(op.f('ix_firmware_device_type_id'), table_name='firmware')
    op.drop_table('firmware')
    op.drop_index(op.f('ix_facility_org_id'), table_name='facility')
    op.drop_table('facility')
    op.drop_index(op.f('ix_device_param_device_type'), table_name='device_param')
    op.drop_table('device_param')
    op.drop_index(op.f('ix_command_type_device_type_id'), table_name='command_type')
    op.drop_table('command_type')
    op.drop_index(op.f('ix_app_user_phone_number'), table_name='app_user')
    op.drop_index('ix_app_user_metadata_gin', table_name='app_user', postgresql_using='gin')
    op.drop_index(op.f('ix_app_user_job_function_id'), table_name='app_user')
    op.drop_index(op.f('ix_app_user_is_staff'), table_name='app_user')
    op.drop_index(op.f('ix_app_user_email'), table_name='app_user')
    op.drop_index(op.f('ix_app_user_department_id'), table_name='app_user')
    op.drop_table('app_user')
    op.drop_index(op.f('ix_activity_type_entity_type_id'), table_name='activity_type')
    op.drop_table('activity_type')
    op.drop_index(op.f('ix_user_token_app_user_id'), table_name='user_token')
    op.drop_table('user_token')
    op.drop_index(op.f('ix_stay_status'), table_name='stay')
    op.drop_index(op.f('ix_stay_expected_checkout_time'), table_name='stay')
    op.drop_index(op.f('ix_stay_expected_checkin_time'), table_name='stay')
    op.drop_index(op.f('ix_stay_booking_user_id'), table_name='stay')
    op.drop_table('stay')
    op.drop_table('service_type')
    op.drop_table('service_status')
    op.drop_table('scheduler_job')
    op.drop_table('role_module')
    op.drop_index(op.f('ix_promo_code_status'), table_name='promo_code')
    op.drop_index(op.f('ix_promo_code_expiry_time'), table_name='promo_code')
    op.drop_table('promo_code')
    op.drop_index('ix_other_device_device_name_timestamp', table_name='other_device')
    op.drop_table('other_device')
    op.drop_table('organisation')
    op.drop_table('occasion_type')
    op.drop_table('notification_template')
    op.drop_table('key_type')
    op.drop_index(op.f('ix_job_order_job_order_status'), table_name='job_order')
    op.drop_index(op.f('ix_job_order_assigned_to'), table_name='job_order')
    op.drop_table('job_order')
    op.drop_table('incident_status')
    op.drop_table('incident_event')
    op.drop_index(op.f('ix_import_job_import_status'), table_name='import_job')
    op.drop_table('import_job')
    op.drop_table('entity_type')
    op.drop_table('device_type')
    op.drop_index(op.f('ix_country_phone_code'), table_name='country')
    op.drop_table('country')
    op.drop_index(op.f('ix_attachment_facility_id'), table_name='attachment')
    op.drop_index(op.f('ix_attachment_created_by'), table_name='attachment')
    op.drop_table('attachment')
    op.drop_table('amenity_status')
    op.drop_table('amenity_condition')
    op.drop_table('alert_type')
    

    # 3. Enum types, once every table that referenced them is gone.
    for enum_type in reversed(ENUM_TYPES):
        enum_type.drop(bind, checkfirst=False)
