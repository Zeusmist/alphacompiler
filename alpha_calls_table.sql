CREATE TABLE alpha_calls (
    id SERIAL PRIMARY KEY,
    token_ticker VARCHAR(20) NOT NULL,
    token_address TEXT,
    network VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    additional_info TEXT,
    channel_name VARCHAR(100) NOT NULL,
    message_url TEXT NOT NULL,
    date TIMESTAMP NOT NULL,
    long_term BOOLEAN NOT NULL
);