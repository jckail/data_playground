# Data Analytics Platform

A comprehensive data analytics and visualization platform demonstrating end-to-end data modeling, real-time analytics, and interactive dashboards. This project showcases full-stack development capabilities, data engineering practices, and modern DevOps approaches.

## 🎯 Overview

This platform models and analyzes user journey data through various stages:
- Lead → User signs up for the application
- Prospect → User selects a plan and creates a shop
- Customer → User completes first payment
- Churn → User becomes inactive (non-payment or shop deletion)

## 🏗 Architecture

### Backend Services
- **FastAPI Application**: RESTful API service with comprehensive data models and endpoints
- **PostgreSQL Database**: Scalable data storage with partitioned tables
- **Alembic**: Database migration management
- **Background Tasks**: Automated data processing and rollup generation

### Frontend & Visualization
- **Streamlit Dashboard**: Interactive data visualization and analysis
- **Grafana**: Real-time monitoring and custom dashboards
- **Prometheus**: Metrics collection and monitoring

### Data Pipeline
- **Event Processing**: Real-time event capture and processing
- **Data Modeling**: Structured data storage with temporal partitioning
- **Analytics Generation**: Automated rollup and analytics calculation

## 📊 Data Models

### Global Events
```sql
CREATE TABLE global_events (
    ts VARCHAR,           -- Hourly partition timestamp
    event_id UUID,        -- Unique event identifier
    event_time TIMESTAMP, -- Actual event timestamp
    event_type ENUM,      -- Event classification
    metadata JSONB,       -- Event-specific data
    PRIMARY KEY (ts, event_id)
);
```

### Core Tables
- **Users**: User account information and metadata
- **Shops**: Store configurations and relationships
- **Plans**: Service tier definitions
- **Invoices**: Billing records
- **Payments**: Transaction tracking

## 🚀 Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start services:
   ```bash
   docker-compose up -d
   ```
4. Initialize database:
   ```bash
   alembic upgrade head
   ```
5. Run the application:
   ```bash
   ./helpers/local_test.sh
   ```

## 🔍 Key Features

- **Real-time Analytics**: Live tracking of user activities and business metrics
- **Interactive Dashboards**: Visual representation of data flows and user journeys
- **Sankey Diagrams**: User flow visualization and conversion tracking
- **Temporal Analysis**: Historical data analysis with point-in-time accuracy
- **Automated Reporting**: Scheduled report generation and data rollups

## 🛠 Development

### API Endpoints
- Frontend: `http://localhost:5173/`
- Backend: `http://localhost:8080/`
- Grafana: `http://localhost:3000/`

### Monitoring
- Application logs: `backend/app/logs/latestfile.log`
- Metrics: Available through Prometheus/Grafana
- Performance monitoring: Custom Grafana dashboards

### Testing
- Automated test data generation
- Comprehensive API testing suite
- Performance benchmarking tools

## 📈 Data Flow

```
User Signs Up → Creates Shop → Pays Invoice → [Repeat/Churn]
```

### Event Types
1. **User Account Creation**
   ```json
   {
       "user_id": "string",
       "email": "string"
   }
   ```
2. **Shop Creation**
   ```json
   {
       "user_id": "string",
       "shop_id": "string",
       "plan_id": "string"
   }
   ```
3. **Account/Shop Deletion**
4. **Payment Processing**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Additional Resources

- API Documentation: `/docs` endpoint
- Grafana Dashboards: `grafana/dashboards/`
- Configuration Templates: Available in respective service directories
