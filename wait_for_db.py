import time
import psycopg
import sys

def wait_for_db():
    max_retries = 30
    retry_interval = 2
    connection_string = "postgresql://user:password@db/dbname"

    for attempt in range(max_retries):
        try:
            with psycopg.connect(connection_string) as conn:
                print("Successfully connected to the database!")
                return
        except psycopg.OperationalError:
            print(f"Attempt {attempt + 1}/{max_retries}: Database not ready. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)

    print("Failed to connect to the database after multiple attempts.")
    sys.exit(1)

if __name__ == "__main__":
    wait_for_db()