# Product Link Management Specification

## Purpose
Manage tracked ML products via web UI and Telegram.

## Requirements

### Requirement: Parse Product URL
MUST extract item_id from ML URLs.

#### Scenario: Valid URL
- GIVEN a valid ML product URL
- WHEN submitted
- THEN item_id extracted and validated

#### Scenario: Invalid URL
- GIVEN a non-ML URL
- WHEN submitted
- THEN error returned

### Requirement: Add Product
MUST register a parsed product.

#### Scenario: New product
- GIVEN a valid item_id
- WHEN user confirms
- THEN product is stored and tracking begins

#### Scenario: Duplicate
- GIVEN an already tracked product
- WHEN user adds the same item_id
- THEN SHOULD notify user

### Requirement: Remove Product
MUST soft-delete a product.

#### Scenario: Remove active
- GIVEN an active product
- WHEN user requests removal
- THEN marked inactive

### Requirement: List Products
MUST return all active products with price.
