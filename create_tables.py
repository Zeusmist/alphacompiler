import asyncio
import asyncpg
from lib.config import pg_user, pg_password, pg_database, pg_host

# import alpha_calls_table query from alpha_calls_table.sql


async def create_table():
    conn = await asyncpg.connect(
        user=pg_user, password=pg_password, database=pg_database, host=pg_host
    )

    # SQL command to create the table
    create_table_query = """
    CREATE TABLE IF NOT EXISTS alpha_calls (
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
    """

    try:
        # Execute the create table command
        await conn.execute(create_table_query)
        print("Table created successfully")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        await conn.close()


# Run the async function
asyncio.get_event_loop().run_until_complete(create_table())
