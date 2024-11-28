# Data Model Documentation

[Previous sections remain unchanged until Partitioning Strategy...]

## Partitioning Strategy

All tables use range partitioning based on event_time:
- Hourly partitioning for most operational tables (orders, payments, users, shops, products, etc.)
- Daily partitioning for metric tables (UserMetricsDaily, ShopMetricsDaily, ProductMetricsDaily)
- Partitioning key format: 
  - Hourly tables: YYYY-MM-DDThh:00:00
  - Daily tables: YYYY-MM-DD

### Hourly Partitioned Tables
- GlobalEntity
- GlobalEvent
- User
- Shop
- ShopProduct
- ShopOrder
- ShopOrderPayment
- Invoice
- InvoicePayment
- UserPaymentMethod
- ShopPromotion
- ShopReview
- ShopInventoryLog
- RequestResponseLog

### User
- Primary entity representing users in the system
- Contains basic user information (email, username, status)
- Referenced by most other entities as the owner/creator
- Relationships:
  - One-to-Many with Shop (as shop owner)
  - One-to-Many with UserPaymentMethod (stored payment methods)
  - One-to-Many with Invoice (as invoice recipient)
  - One-to-Many with ShopOrder (as order placer)
  - One-to-Many with ShopReview (as reviewer)
  - One-to-Many with UserMetricsHourly/Daily (user metrics)

### Shop
- Represents a shop owned by a User
- Contains shop details (name, category, address)
- Relationships:
  - Many-to-One with User (shop owner)
  - One-to-Many with ShopProduct (products in shop)
  - One-to-Many with ShopOrder (orders placed at shop)
  - One-to-Many with Invoice (invoices issued by shop)
  - One-to-Many with ShopPromotion (shop promotions)
  - One-to-Many with ShopReview (shop reviews)
  - One-to-Many with ShopMetricsHourly/Daily (shop metrics)

## Product Management

### ShopProduct
- Represents products available in a shop
- Contains product details (SKU, name, price, inventory)
- Relationships:
  - Many-to-One with Shop (shop offering product)
  - One-to-Many with ShopOrderItem (product orders)
  - One-to-Many with ShopInventoryLog (inventory changes)
  - One-to-Many with ShopReview (product reviews)
  - One-to-Many with ShopProductMetricsHourly/Daily (product metrics)

[Previous sections remain unchanged...]

## Metrics and Analytics

### User Metrics (Hourly/Daily)
- UserMetricsHourly and UserMetricsDaily
- Tracks user activity and engagement metrics
- Key metrics include:
  - Order counts and values
  - Payment success/failure rates
  - Review activity
  - Promotion usage
  - Cart abandonment
- Relationships:
  - Many-to-One with User

### Shop Metrics (Hourly/Daily)
- ShopMetricsHourly and ShopMetricsDaily
- Tracks shop performance and business metrics
- Key metrics include:
  - Order volume and revenue
  - Customer counts
  - Product performance
  - Review ratings
  - Promotion effectiveness
  - Inventory value
- Relationships:
  - Many-to-One with Shop

### Product Metrics (Hourly/Daily)
- ShopProductMetricsHourly and ShopProductMetricsDaily
- Tracks individual product performance
- Key metrics include:
  - Sales volume and revenue
  - Inventory levels
  - Price variations
  - Review ratings
  - Promotion impact
  - Page views and cart interactions
- Relationships:
  - Many-to-One with ShopProduct

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
- Hourly tables: Fine-grained operational data for real-time analysis and processing
- Daily tables: Aggregated metrics for trend analysis and reporting
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
- Daily partitioning for efficient historical analysis
- JSON extra_metrics field for extensibility
- Default values for all numeric metrics
- Foreign key relationships to source entities
- Comprehensive coverage of business KPIs

## Schema Organization

All tables are in the 'data_playground' schema for proper organization and access control.

## Common Fields

Most tables include:
- UUID primary keys
- event_time for partitioning
- created_time/updated_time for tracking
- extra_data/extra_metrics JSON field for extensibility
- partition_key for range partitioning
