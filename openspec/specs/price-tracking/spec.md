# Price Tracking Specification

## Purpose
Query ML API periodically and store price snapshots.

## Requirements

### Requirement: Schedule Checks
MUST check active prices on a fixed interval.

#### Scenario: Normal cycle
- GIVEN active products in DB
- WHEN the interval elapses
- THEN each price is fetched from the ML API

#### Scenario: No products
- GIVEN zero active products
- WHEN interval elapses
- THEN cycle SHALL skip

### Requirement: Store Snapshots
MUST persist each price with a timestamp.

#### Scenario: Successful fetch
- GIVEN a product with valid item_id
- WHEN ML API returns data
- THEN price_history row inserted

#### Scenario: API error
- GIVEN a product whose API call fails
- WHEN fetch returns an error
- THEN skipped, error logged

### Requirement: Track Min/Max Price
MUST compute lowest and highest price per product.

#### Scenario: New low
- GIVEN a product with existing min_price
- WHEN a snapshot is below min_price
- THEN min_price is updated
