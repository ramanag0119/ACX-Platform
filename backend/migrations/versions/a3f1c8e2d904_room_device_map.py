"""room_device_map: OSS devices installed in HMS rooms

Revision ID: a3f1c8e2d904
Revises: 7c4e2b9a1d53
Create Date: 2026-10-30 12:00:00.000000

Device data is read from the externally owned OSS database, which has no rooms
and which HMS may never write to. This HMS-owned table maps each OSS device
(`insp_device.device_id`) to the room it is installed in, so the backend can
compose room details (BSS) with device data (OSS).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, NOW, UTCDateTime

# revision identifiers, used by Alembic.
revision: str = 'a3f1c8e2d904'
down_revision: Union[str, Sequence[str], None] = '7c4e2b9a1d53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('room_device_map',
    sa.Column('amenity_id', GUID(), nullable=False),
    sa.Column('oss_device_id', GUID(), nullable=False),
    sa.Column('created_by', GUID(), nullable=True),
    sa.Column('legacy_id', sa.BigInteger(), nullable=True),
    sa.Column('id', GUID(), nullable=False),
    sa.Column('created_on', UTCDateTime(), server_default=NOW, nullable=False),
    sa.Column('updated_on', UTCDateTime(), server_default=NOW, nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenity.id'], name=op.f('fk_room_device_map_amenity_id_amenity'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['app_user.id'], name=op.f('fk_room_device_map_created_by_app_user'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_room_device_map')),
    sa.UniqueConstraint('legacy_id', name=op.f('uq_room_device_map_legacy_id')),
    sa.UniqueConstraint('oss_device_id', name=op.f('uq_room_device_map_oss_device_id'))
    )
    op.create_index(op.f('ix_room_device_map_amenity_id'), 'room_device_map', ['amenity_id'], unique=False)


def downgrade() -> None:
    # Dropping the table drops its indexes; MySQL refuses to drop the
    # amenity_id index on its own while the foreign key still needs it.
    op.drop_table('room_device_map')
