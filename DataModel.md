# Data Model Documentation

## Core Entities

### GlobalEntity
- Central registry for all entities in the system
- Tracks creation time and type of every entity
- Enables efficient cross-entity queries and lookups
- Primary Key: (event_time, entity_id)
- Relationships:
  - Referenced by all other tables through entity_id
- Partitioning:
  - Daily partitioning by event_time
  - Optimized for time-based queries
- Key Indexes:
  - (entity_type, event_time) for type-based lookups
  - (entity_id, entity_type) for entity resolution
  - (event_time, entity_id) for time-based queries

### FakeUser
- Primary entity representing users in the system
- Contains basic user information (email, username, status)
- Referenced by most other entities as the owner/creator
- Relationships:
  - One-to-Many with FakeUserShop (as shop owner)
  - One-to-Many with FakeUserPaymentMethod (stored payment methods)
  - One-to-Many with FakeUserInvoice (as invoice recipient)
  - One-to-Many with FakeUserShopOrder (as order placer)
  - One-to-Many with FakeUserShopReview (as reviewer)
  - One-to-Many with FakeUserMetricsHourly/Daily (user metrics)

### FakeUserShop
- Represents a shop owned by a FakeUser
- Contains shop details (name, category, address)
- Relationships:
  - Many-to-One with FakeUser (shop owner)
  - One-to-Many with FakeUserShopProduct (products in shop)
  - One-to-Many with FakeUserShopOrder (orders placed at shop)
  - One-to-Many with FakeUserInvoice (invoices issued by shop)
  - One-to-Many with FakeUserShopPromotion (shop promotions)
  - One-to-Many with FakeUserShopReview (shop reviews)
  - One-to-Many with FakeUserShopMetricsHourly/Daily (shop metrics)

## Product Management

### FakeUserShopProduct
- Represents products available in a shop
- Contains product details (SKU, name, price, inventory)
- Relationships:
  - Many-to-One with FakeUserShop (shop offering product)
  - One-to-Many with FakeUserShopOrderItem (product orders)
  - One-to-Many with FakeUserShopInventoryLog (inventory changes)
  - One-to-Many with FakeUserShopReview (product reviews)
  - One-to-Many with FakeUserShopProductMetricsHourly/Daily (product metrics)

[Previous sections remain unchanged...]

## Metrics and Analytics

### User Metrics (Hourly/Daily)
- FakeUserMetricsHourly and FakeUserMetricsDaily
- Tracks user activity and engagement metrics
- Key metrics include:
  - Order counts and values
  - Payment success/failure rates
  - Review activity
  - Promotion usage
  - Cart abandonment
- Relationships:
  - Many-to-One with FakeUser

### Shop Metrics (Hourly/Daily)
- FakeUserShopMetricsHourly and FakeUserShopMetricsDaily
- Tracks shop performance and business metrics
- Key metrics include:
  - Order volume and revenue
  - Customer counts
  - Product performance
  - Review ratings
  - Promotion effectiveness
  - Inventory value
- Relationships:
  - Many-to-One with FakeUserShop

### Product Metrics (Hourly/Daily)
- FakeUserShopProductMetricsHourly and FakeUserShopProductMetricsDaily
- Tracks individual product performance
- Key metrics include:
  - Sales volume and revenue
  - Inventory levels
  - Price variations
  - Review ratings
  - Promotion impact
  - Page views and cart interactions
- Relationships:
  - Many-to-One with FakeUserShopProduct

## Entity Resolution and Tracking

### GlobalEntity Design
1. Purpose:
   - Central registry for all entities
   - Enables efficient cross-entity queries
   - Supports time-based entity tracking
   - Facilitates entity type resolution

2. Key Features:
   - Composite primary key (event_time, entity_id)
   - Entity type enumeration
   - Daily partitioning
   - Optimized indexes for common queries

3. Use Cases:
   - Entity type resolution
   - Creation time tracking
   - Cross-entity analytics
   - System-wide entity auditing

## Metric Tables Design Principles

### Time Granularity
- Hourly tables: Fine-grained metrics for detailed analysis
- Daily tables: Aggregated metrics for trend analysis
- Both use range partitioning for efficient querying

### Common Metric Categories
1. Transaction Metrics
   - Order counts
   - Revenue figures
   - Payment success rates

2. Engagement Metrics
   - Review activity
   - Promotion usage
   - Cart interactions

3. Performance Metrics
   - Response times
   - Success rates
   - Error counts

4. Business Metrics
   - Revenue
   - Customer acquisition
   - Inventory turnover

### Metric Table Features
- Partitioned by time for efficient querying
- JSON extra_metrics field for extensibility
- Default values for all numeric metrics
- Foreign key relationships to source entities
- Comprehensive coverage of business KPIs

## Partitioning Strategy

All tables use range partitioning based on event_time:
- Daily partitioning for most tables
- Hourly partitioning for GlobalEvents and hourly metrics
- Partitioning key format: YYYY-MM-DD for daily, YYYY-MM-DDThh:00:00 for hourly

## Schema Organization

All tables are in the 'data_playground' schema for proper organization and access control.

## Common Fields

Most tables include:
- UUID primary keys
- event_time for partitioning
- created_time/updated_time for tracking
- extra_data/extra_metrics JSON field for extensibility
- partition_key for range partitioning
