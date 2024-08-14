CREATE TABLE alpha_calls (
    id SERIAL PRIMARY KEY,
    token_ticker VARCHAR(20) NOT NULL,
    token_address TEXT,
    token_name VARCHAR(100),
    token_image TEXT,
    network VARCHAR(50) NOT NULL,
    additional_info TEXT,
    channel_name VARCHAR(100) NOT NULL,
    message_url TEXT NOT NULL,
    date TIMESTAMP NOT NULL,
    long_term BOOLEAN NOT NULL
);

CREATE INDEX idx_alpha_calls_date ON alpha_calls(date);
CREATE INDEX idx_alpha_calls_token_ticker ON alpha_calls(token_ticker);
CREATE INDEX idx_alpha_calls_network ON alpha_calls(network);
CREATE INDEX idx_alpha_calls_token_address ON alpha_calls(token_address);