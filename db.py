import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


def get_connection():
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )


def init_db():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_identifier TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER REFERENCES users(id),
                    project_id INTEGER REFERENCES projects(id),
                    started_at TIMESTAMPTZ,
                    last_activity_at TIMESTAMPTZ
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id SERIAL PRIMARY KEY,
                    prompt_id TEXT NOT NULL,
                    session_id TEXT REFERENCES sessions(session_id),
                    user_id INTEGER REFERENCES users(id),
                    message_uuid TEXT,
                    prompt TEXT,
                    prompt_length INTEGER,
                    timestamp TIMESTAMPTZ
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_requests (
                    id SERIAL PRIMARY KEY,
                    request_id TEXT UNIQUE NOT NULL,
                    prompt_id TEXT,
                    session_id TEXT REFERENCES sessions(session_id),
                    user_id INTEGER REFERENCES users(id),
                    model TEXT,
                    query_source TEXT,
                    effort TEXT,
                    input_tokens BIGINT DEFAULT 0,
                    output_tokens BIGINT DEFAULT 0,
                    cache_read_tokens BIGINT DEFAULT 0,
                    cache_creation_tokens BIGINT DEFAULT 0,
                    total_tokens BIGINT DEFAULT 0,
                    cost_usd DOUBLE PRECISION DEFAULT 0,
                    duration_ms DOUBLE PRECISION,
                    ttft_ms DOUBLE PRECISION,
                    timestamp TIMESTAMPTZ
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    id SERIAL PRIMARY KEY,
                    message_uuid TEXT UNIQUE NOT NULL,
                    prompt_id TEXT,
                    session_id TEXT REFERENCES sessions(session_id),
                    model TEXT,
                    response TEXT,
                    response_length INTEGER,
                    timestamp TIMESTAMPTZ
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_requests_timestamp
                ON api_requests(timestamp);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_requests_session
                ON api_requests(session_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_prompts_timestamp
                ON prompts(timestamp);
            """)

        conn.commit()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")