# Telegram Notifications Specification

## Purpose
Notify via bot NotifyOffersMc on price drops and accept commands.

## Requirements

### Requirement: Price Drop Alert
MUST alert when price drops below known minimum.

#### Scenario: Price drops
- GIVEN a tracked product with known min_price
- WHEN a snapshot is lower than min_price
- THEN message sent with title, prices, and drop %

#### Scenario: Price unchanged
- GIVEN a tracked product
- WHEN snapshot equals current price
- THEN no notification is sent

### Requirement: /add Command
MUST accept `/add <url>` to register a product.

#### Scenario: Valid URL
- WHEN user sends `/add <ML_URL>`
- THEN product is added and bot confirms

#### Scenario: Invalid URL
- WHEN user sends `/add <invalid>`
- THEN bot replies with an error

### Requirement: /list Command
MUST list active products with price.

#### Scenario: List products
- GIVEN one or more active products
- WHEN user sends `/list`
- THEN bot returns a numbered list

### Requirement: /remove Command
MUST remove a product by ID.

#### Scenario: Remove via bot
- GIVEN an active product
- WHEN user sends `/remove <id>`
- THEN product deleted, bot confirms
