import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Get the database URL from environment variable
db_url = os.getenv('DATABASE_URL')

def run_query(query):
    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        
        # Create a cursor
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Execute the query
        cur.execute(query)
        
        # Fetch all results
        results = cur.fetchall()
        
        # Print results
        for row in results:
            print(row)
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
        run_query(query)
    else:
        print("Please provide a SQL query as an argument.")