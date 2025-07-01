---
slug: /use-cases/data-lake/rest-catalog
sidebar_label: 'REST Catalog'
title: 'REST Catalog'
pagination_prev: null
pagination_next: null
description: 'In this guide, we will walk you through the steps to query
 your data in S3 buckets using ClickHouse and the REST Catalog (Tabular.io).'
keywords: ['REST', 'Tabular', 'Data Lake', 'Iceberg']
show_related_blogs: true
---

import ExperimentalBadge from '@theme/badges/ExperimentalBadge';

<ExperimentalBadge/>

:::note
Integration with the REST Catalog works with Iceberg tables only.
This integration supports both AWS S3 and other cloud storage providers.
:::

ClickHouse supports integration with multiple catalogs (Unity, Glue, REST, Polaris, etc.). This guide will walk you through the steps to query your data managed by Tabular.io using ClickHouse and the [REST Catalog](https://tabular.io/).

The REST Catalog is a standardized API specification for Iceberg catalogs, widely supported by various platforms including Tabular.io, which provides a managed Iceberg catalog service.

:::note
As this feature is experimental, you will need to enable it using:
`SET allow_experimental_database_rest_catalog = 1;`
:::

## Configuring REST Catalog in Tabular.io {#configuring-rest-catalog-in-tabular}

To allow ClickHouse to interact with the REST catalog, you need to configure authentication and access to your Tabular.io workspace.

### Prerequisites {#prerequisites}

1. **Tabular.io Account**: Sign up for a [Tabular.io account](https://tabular.io/) if you don't have one
2. **Warehouse Setup**: Create a warehouse in your Tabular.io workspace
3. **Authentication Credentials**: Generate API credentials for programmatic access

### Authentication Methods {#authentication-methods}

Tabular.io supports several authentication methods:

* **OAuth2 Client Credentials**: Recommended for production environments
* **Bearer Token**: Simple token-based authentication
* **Basic Authentication**: Username/password authentication

## Creating a connection between REST Catalog and ClickHouse {#creating-a-connection-between-rest-catalog-and-clickhouse}

With your REST catalog configured and authentication in place, establish a connection between ClickHouse and the REST catalog.

### Using OAuth2 Client Credentials {#using-oauth2-client-credentials}

```sql
CREATE DATABASE rest_catalog
ENGINE = DataLakeCatalog('https://api.tabular.io/ws/<workspace-id>/v1/<warehouse-name>')
SETTINGS 
    catalog_type = 'rest',
    catalog_credential = '<client-id>:<client-secret>',
    oauth_server_uri = 'https://api.tabular.io/oauth/tokens',
    auth_scope = 'catalog:read'
```

### Using Bearer Token {#using-bearer-token}

```sql
CREATE DATABASE rest_catalog 
ENGINE = DataLakeCatalog('https://api.tabular.io/ws/<workspace-id>/v1/<warehouse-name>')
SETTINGS 
    catalog_type = 'rest',
    catalog_credential = '<bearer-token>'
```

### Using Basic Authentication {#using-basic-authentication}

```sql
CREATE DATABASE rest_catalog
ENGINE = DataLakeCatalog('https://api.tabular.io/ws/<workspace-id>/v1/<warehouse-name>')
SETTINGS 
    catalog_type = 'rest',
    catalog_credential = '<username>:<password>',
    auth_header_type = 'basic'
```

## Querying REST catalog tables using ClickHouse {#querying-rest-catalog-tables-using-clickhouse}

Now that the connection is in place, you can start querying via the REST catalog. For example:

```sql
USE rest_catalog;

SHOW TABLES;
```

```sql title="Response"
┌─name────────────────────────────┐
│ sales.customer_orders           │
│ sales.products                  │
│ analytics.daily_metrics         │
│ analytics.user_events           │
│ inventory.stock_levels          │
└─────────────────────────────────┘
```

To query a table:

```sql
SELECT count(*) FROM `sales.customer_orders`;
```

```sql title="Response"
┌─count()─┐
│ 1542897 │
└─────────┘
```

:::note Backticks required
Backticks are required because ClickHouse doesn't support more than one namespace.
:::

To inspect the table DDL:

```sql
SHOW CREATE TABLE `sales.customer_orders`;
```

```sql title="Response"
┌─statement─────────────────────────────────────────────────┐
│ CREATE TABLE rest_catalog.`sales.customer_orders`        │
│ (                                                         │
│     `order_id` Nullable(Int64),                          │
│     `customer_id` Nullable(Int64),                       │
│     `order_date` Nullable(Date),                         │
│     `order_timestamp` Nullable(DateTime64(6)),           │
│     `total_amount` Nullable(Decimal(10, 2)),             │
│     `currency` Nullable(String),                         │
│     `status` Nullable(String),                           │
│     `shipping_address` Nullable(String),                 │
│     `billing_address` Nullable(String),                  │
│     `payment_method` Nullable(String),                   │
│     `discount_amount` Nullable(Decimal(10, 2)),          │
│     `tax_amount` Nullable(Decimal(10, 2)),               │
│     `created_at` Nullable(DateTime64(6)),                │
│     `updated_at` Nullable(DateTime64(6))                 │
│ )                                                         │
│ ENGINE = Iceberg('s3://tabular-warehouse/sales/orders/') │
└───────────────────────────────────────────────────────────┘
```

### Advanced Querying Examples {#advanced-querying-examples}

Query with filtering and aggregation:

```sql
SELECT 
    status,
    COUNT(*) as order_count,
    SUM(total_amount) as total_revenue
FROM `sales.customer_orders`
WHERE order_date >= '2024-01-01'
GROUP BY status
ORDER BY total_revenue DESC;
```

```sql title="Response"
┌─status─────┬─order_count─┬─total_revenue─┐
│ completed  │      856432 │   12847392.45 │
│ shipped    │      234567 │    3521847.23 │
│ processing │       89234 │    1234567.89 │
│ cancelled  │       23456 │     345678.90 │
└────────────┴─────────────┴───────────────┘
```

Time-series analysis:

```sql
SELECT 
    toStartOfMonth(order_date) as month,
    COUNT(*) as orders,
    AVG(total_amount) as avg_order_value
FROM `sales.customer_orders`
WHERE order_date >= '2024-01-01'
GROUP BY month
ORDER BY month;
```

## Working with Partitioned Tables {#working-with-partitioned-tables}

REST catalogs often contain partitioned Iceberg tables for better performance:

```sql
-- Query specific partition
SELECT COUNT(*) 
FROM `analytics.user_events`
WHERE event_date = '2024-01-15';

-- Query across multiple partitions
SELECT 
    event_date,
    event_type,
    COUNT(*) as event_count
FROM `analytics.user_events`
WHERE event_date BETWEEN '2024-01-01' AND '2024-01-31'
GROUP BY event_date, event_type
ORDER BY event_date, event_count DESC;
```

## Loading data from your Data Lake into ClickHouse {#loading-data-from-your-data-lake-into-clickhouse}

If you need to load data from the REST catalog into ClickHouse, start by creating a local ClickHouse table:

```sql
CREATE TABLE customer_orders
(
    `order_id` Int64,
    `customer_id` Int64,
    `order_date` Date,
    `order_timestamp` DateTime64(6),
    `total_amount` Decimal(10, 2),
    `currency` String,
    `status` String,
    `shipping_address` String,
    `billing_address` String,
    `payment_method` String,
    `discount_amount` Decimal(10, 2),
    `tax_amount` Decimal(10, 2),
    `created_at` DateTime64(6),
    `updated_at` DateTime64(6)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(order_date)
ORDER BY (customer_id, order_date, order_id);
```

Then load the data from your REST catalog table via an `INSERT INTO SELECT`:

```sql
INSERT INTO customer_orders 
SELECT * FROM rest_catalog.`sales.customer_orders`;
```

### Incremental Data Loading {#incremental-data-loading}

For large tables, consider incremental loading:

```sql
-- Load only recent data
INSERT INTO customer_orders 
SELECT * FROM rest_catalog.`sales.customer_orders`
WHERE updated_at > (
    SELECT MAX(updated_at) FROM customer_orders
);
```

## Best Practices {#best-practices}

1. **Use appropriate authentication**: OAuth2 for production, bearer tokens for development
2. **Leverage partitioning**: Query specific partitions when possible for better performance
3. **Monitor costs**: REST catalog queries may incur costs based on data scanned
4. **Use projection pushdown**: ClickHouse automatically pushes down filters and projections
5. **Consider data locality**: Co-locate ClickHouse and your data storage for better performance

## Troubleshooting {#troubleshooting}

### Common Issues {#common-issues}

**Authentication failures:**
```sql
-- Verify your credentials are correct
SELECT * FROM system.databases WHERE name = 'rest_catalog';
```

**Connection timeouts:**
```sql
-- Increase timeout settings
SET rest_catalog_connection_timeout = 30;
SET rest_catalog_read_timeout = 60;
```

**Table not found errors:**
```sql
-- Check available namespaces
SHOW DATABASES FROM rest_catalog;

-- List tables in specific namespace
SHOW TABLES FROM rest_catalog LIKE 'sales.%';
```

## Configuration Reference {#configuration-reference}

| Setting | Description | Required | Default |
|---------|-------------|----------|---------|
| `catalog_type` | Must be set to 'rest' | Yes | - |
| `catalog_credential` | Authentication credentials | Yes | - |
| `oauth_server_uri` | OAuth token endpoint | No | - |
| `auth_scope` | OAuth scope | No | - |
| `auth_header_type` | Authentication header type | No | 'bearer' |
| `warehouse` | Warehouse identifier | No | - |
| `rest_catalog_connection_timeout` | Connection timeout in seconds | No | 10 |
| `rest_catalog_read_timeout` | Read timeout in seconds | No | 60 | 