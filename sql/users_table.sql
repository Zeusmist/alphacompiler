CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    wallet_address VARCHAR(255) UNIQUE,
    role VARCHAR(20) DEFAULT 'basic',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    subscription_end_date TIMESTAMP
);