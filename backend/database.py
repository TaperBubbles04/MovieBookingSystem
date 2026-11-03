from psycopg_pool import ConnectionPool
from contextlib import contextmanager
import os

pool = ConnectionPool(
    conninfo=os.getenv("DATABASE_URL"),
    min_size=2,
    max_size=10,
)

@contextmanager
def get_db():
    with pool.connection() as conn:
        with conn.cursor() as cur:
            yield cur
