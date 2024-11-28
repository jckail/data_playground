from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, Enum, Index, UUID
from datetime import datetime
from .enums import EntityType

class GlobalEntity(Base, PartitionedModel):
    """
    Tracks all entities in the system, providing a global registry of
    when entities were created, deactivated, or reactivated.
    
    Indexing Strategy:
    - Primary key (event_time, entity_id, partition_key)
    - entity_type is indexed for filtering by type
    - event_time is indexed for time-based queries
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'global_entities'
    __partitiontype__ = "hourly"  # Changed from daily to hourly
    __partition_field__ = "event_time"

    # Primary Fields
    event_time = Column(
        DateTime(timezone=True), 
        primary_key=True,
        comment="Timestamp used for partitioning and primary key"
    )
    entity_id = Column(
        UUID(as_uuid=True), 
        primary_key=True,
        comment="Unique identifier for the entity"
    )
    partition_key = Column(
        String, 
        primary_key=True,
        comment="Key used for time-based table partitioning"
    )
    
    # Entity Type for table mapping
    entity_type = Column(
        Enum(EntityType, schema='data_playground'), 
        nullable=False,
        index=True,
        comment="Type of entity being tracked"
    )

    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,
        comment="When the entity was created"
    )
    deactivated_time = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When the entity was deactivated (if applicable)"
    )
    reactivated_time = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When the entity was reactivated (if applicable)"
    )

    # Indexes for common queries
    __table_args__ = (
        # Index for looking up entities by type
        Index('idx_global_entity_type_time', 
              entity_type, event_time,
              postgresql_using='btree'),
              
        # Index for looking up entities by ID
        Index('idx_global_entity_id_type', 
              entity_id, entity_type,
              postgresql_using='btree'),
              
        # Index for time-based queries
        Index('idx_global_entity_time_id', 
              event_time, entity_id,
              postgresql_using='btree'),
              
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores entity data with hourly partitioning for efficient querying'
        }
    )
