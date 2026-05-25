# Web Dashboard Specification

## Purpose
Web interface for products, prices, history, and alerts.

## Requirements

### Requirement: Display Products
MUST render products with title, price, and min/max.

#### Scenario: Products loaded
- GIVEN active products in DB
- WHEN user visits the dashboard
- THEN a product table is rendered

#### Scenario: Empty state
- GIVEN zero active products
- WHEN user visits dashboard
- THEN empty state shown

### Requirement: Show Price History
SHOULD show price history as timeline.

#### Scenario: View history
- GIVEN a product with price_history rows
- WHEN user selects a product
- THEN snapshot values and timestamps are shown

### Requirement: Show Recent Alerts
SHOULD show recent alerts newest-first.

#### Scenario: Alerts visible
- GIVEN alerts exist
- WHEN user views dashboard
- THEN alerts shown with product and price
