from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker
from app.database import SQLALCHEMY_DATABASE_URL

def test_table_creation():
    try:
        # Create an engine
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        
        # Create a metadata object
        metadata = MetaData(schema='data_playground')
        
        # Define a test table
        test_table = Table('test_permissions_table', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(50))
        )
        
        # Create the table
        metadata.create_all(engine)
        
        # If we get here, table creation was successful
        print("Table creation successful!")
        
        # Optional: Drop the test table
        test_table.drop(engine)
        print("Test table dropped successfully.")
        
        return True
    
    except Exception as e:
        print(f"Error creating table: {e}")
        return False

if __name__ == "__main__":
    result = test_table_creation()
    exit(0 if result else 1)
