"""
PostgreSQL Database Setup Script for DementiaNext
Automatically creates database and verifies connection
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database configuration
DB_NAME = 'dementianext_db'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'
DB_HOST = 'localhost'
DB_PORT = '5433'

def create_database():
    """Create PostgreSQL database for DementiaNext"""
    print("=" * 60)
    print("PostgreSQL Database Setup for DementiaNext")
    print("=" * 60)
    
    try:
        # Connect to PostgreSQL server (not specific database)
        print(f"\n✓ Connecting to PostgreSQL server at {DB_HOST}:{DB_PORT}...")
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print("✓ Connected to PostgreSQL server successfully!")
        
        # Check if database already exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"\n⚠ Database '{DB_NAME}' already exists!")
            response = input("Do you want to drop and recreate it? (yes/no): ")
            if response.lower() == 'yes':
                print(f"\n✓ Dropping existing database '{DB_NAME}'...")
                cursor.execute(f"DROP DATABASE {DB_NAME}")
                print("✓ Database dropped successfully!")
            else:
                print("\n✓ Using existing database.")
                cursor.close()
                conn.close()
                return True
        
        # Create database
        print(f"\n✓ Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"✓ Database '{DB_NAME}' created successfully!")
        
        cursor.close()
        conn.close()
        
        # Verify database connection
        print(f"\n✓ Verifying connection to '{DB_NAME}'...")
        test_conn = psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        test_conn.close()
        print("✓ Database connection verified!")
        
        print("\n" + "=" * 60)
        print("✅ DATABASE SETUP COMPLETE!")
        print("=" * 60)
        print(f"\nDatabase Details:")
        print(f"  Name:     {DB_NAME}")
        print(f"  User:     {DB_USER}")
        print(f"  Host:     {DB_HOST}")
        print(f"  Port:     {DB_PORT}")
        print(f"\nNext Steps:")
        print(f"  1. Run migrations: python manage.py migrate")
        print(f"  2. Create superuser: python manage.py createsuperuser")
        print(f"  3. Run tests: python manage.py test")
        print("=" * 60)
        
        return True
        
    except psycopg2.OperationalError as e:
        print("\n❌ ERROR: Could not connect to PostgreSQL server!")
        print(f"\nDetails: {e}")
        print("\nPossible solutions:")
        print("  1. Make sure PostgreSQL is installed")
        print("  2. Check if PostgreSQL service is running:")
        print("     Get-Service postgresql*")
        print("  3. Verify connection details in .env file")
        print("  4. Check if password is correct (default: 'postgres')")
        return False
        
    except psycopg2.Error as e:
        print(f"\n❌ ERROR: Database operation failed!")
        print(f"Details: {e}")
        return False
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return False


if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)
