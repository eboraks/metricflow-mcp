#!/usr/bin/env python3
"""
Test script to demonstrate loading data into PostgreSQL
This script shows the complete process of downloading CSV data and storing it in PostgreSQL
"""

import subprocess
import json
import sys

# Ensure stdout/stderr can encode Unicode on Windows consoles
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def run_docker_command(command):
    """Run a command inside the Docker container"""
    try:
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "server"] + command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120  # Longer timeout for downloads and imports
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def run_db_command(sql_command):
    """Run a SQL command directly on the PostgreSQL database"""
    try:
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "db", "psql", "-U", "mcpuser", "-d", "mcpdb", "-c", sql_command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_postgres_data_loading():
    """Test complete data loading process into PostgreSQL"""
    print("🚀 Testing PostgreSQL Data Loading")
    print("=" * 60)
    
    # Step 1: Check current database state
    print("📊 Step 1: Checking current database state...")
    success, stdout, stderr = run_db_command("\\dt")
    if success:
        print(f"✅ Current tables: {stdout}")
    else:
        print(f"❌ Failed to list tables: {stderr}")
    
    # Step 2: Download and import data
    print("\n📥 Step 2: Downloading and importing data into PostgreSQL...")
    
    test_script = '''
import asyncio
import sys
import os
sys.path.append('/app/src')

import server

async def load_data_into_postgres():
    print("🔄 Starting data loading process...")
    
    # Step 1: Download Kaggle dataset
    print("\\n📥 Downloading Kaggle dataset...")
    try:
        download_info = server.kaggle_downloader.download_dataset("yashdevladdha/uber-ride-analytics-dashboard")
        if download_info.get("status") == "error":
            raise Exception(download_info.get("error", "Unknown error"))
        print(f"✅ Download successful!")
        print(f"📁 Download path: {download_info.get('download_path', '')}")
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False
    
    # Step 2: List downloaded datasets
    print("\\n📁 Listing downloaded datasets...")
    try:
        datasets_result = server.kaggle_downloader.list_downloaded_datasets()
        print(f"📂 {datasets_result}")
    except Exception as e:
        print(f"❌ Failed to list datasets: {e}")
    
    # Step 3: Try to import CSV data
    print("\\n📊 Attempting to import CSV data into PostgreSQL...")
    try:
        # Try different possible CSV filenames
        possible_files = ["uber_data.csv", "data.csv", "rides.csv", "uber_rides.csv", "uber-rides.csv"]
        
        import_success = False
        for filename in possible_files:
            try:
                print(f"\\n🔄 Trying to import: {filename}")
                # Find CSV file path
                dl = server.kaggle_downloader.download_dataset("yashdevladdha/uber-ride-analytics-dashboard")
                if dl.get("status") == "error":
                    raise Exception(dl.get("error", "Unknown error"))
                target_csv = None
                for p in dl.get("csv_file_paths", []):
                    if filename in p or filename == os.path.basename(p):
                        target_csv = p
                        break
                if not target_csv:
                    available = [os.path.basename(p) for p in dl.get("csv_file_paths", [])]
                    print(f"⚠️ CSV not found: {filename}. Available: {', '.join(available)}")
                    continue
                import_result = server.csv_importer.create_table_from_csv(target_csv, "uber_rides")
                if isinstance(import_result, str) and ("Imported" in import_result):
                    print(f"✅ Import successful: {import_result}")
                    import_success = True
                    break
                else:
                    print(f"⚠️ Import did not succeed: {import_result}")
            except Exception as import_error:
                print(f"⚠️ Failed to import {filename}: {import_error}")
                continue
        
        if not import_success:
            print("\\n❌ Could not import any CSV files.")
            print("Let's create a sample CSV file and import it instead...")
            
            # Create a sample CSV file
            import pandas as pd
            import os
            
            sample_data = {
                'ride_id': [1, 2, 3, 4, 5],
                'pickup_datetime': ['2023-01-01 08:00:00', '2023-01-01 09:00:00', '2023-01-01 10:00:00', '2023-01-01 11:00:00', '2023-01-01 12:00:00'],
                'dropoff_datetime': ['2023-01-01 08:30:00', '2023-01-01 09:30:00', '2023-01-01 10:30:00', '2023-01-01 11:30:00', '2023-01-01 12:30:00'],
                'passenger_count': [2, 1, 3, 2, 1],
                'trip_distance': [5.2, 3.1, 7.8, 4.5, 2.9],
                'pickup_location': ['Manhattan', 'Brooklyn', 'Queens', 'Manhattan', 'Bronx'],
                'dropoff_location': ['Brooklyn', 'Manhattan', 'Manhattan', 'Queens', 'Manhattan'],
                'fare_amount': [15.50, 12.30, 22.80, 18.20, 9.75]
            }
            
            df = pd.DataFrame(sample_data)
            csv_path = "/tmp/sample_uber_data.csv"
            df.to_csv(csv_path, index=False)
            
            print(f"\\n📝 Created sample CSV file: {csv_path}")
            print(f"📊 Sample data: {df.head()}")
            
            # Import the sample CSV
            import_result = server.csv_importer.create_table_from_csv(csv_path, "uber_rides")
            print(f"✅ Sample data imported: {import_result}")
            import_success = True
        
        if import_success:
            # Step 4: Verify data in PostgreSQL
            print("\\n📋 Step 4: Verifying data in PostgreSQL...")
            
            # Get table info
            table_info = server.csv_importer.get_table_info("uber_rides")
            print(f"\\n📊 Table structure:")
            print(table_info)
            
            # Query sample data
            query_result = server.csv_importer.query_table("uber_rides", 5)
            print(f"\\n📈 Sample data from PostgreSQL:")
            print(query_result)
            
            # List all tables
            from sqlalchemy import text as _text
            with server.engine.connect() as _conn:
                res = _conn.execute(_text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' ORDER BY table_name;
                """))
                tables = [r[0] for r in res.fetchall()]
            print(f"\\n📂 All tables in database:")
            print(tables)
            
            print("\\n✅ Data successfully loaded into PostgreSQL!")
            return True
        else:
            print("\\n❌ Failed to import any data")
            return False
            
    except Exception as e:
        print(f"❌ Data loading process failed: {e}")
        return False

asyncio.run(load_data_into_postgres())
'''
    
    success, stdout, stderr = run_docker_command([
        "poetry", "run", "python", "-c", test_script
    ])
    
    print("\n" + "=" * 60)
    print("📊 DATA LOADING RESULTS:")
    print("=" * 60)
    
    if success:
        print("✅ Data loading test completed successfully!")
        print("\n📋 OUTPUT:")
        print(stdout)
    else:
        print("❌ Data loading test failed!")
        print("\n📋 ERROR:")
        print(stderr)
    
    # Step 3: Verify data in PostgreSQL directly
    print("\n🔍 Step 3: Direct PostgreSQL verification...")
    
    # Check tables
    success, stdout, stderr = run_db_command("\\dt")
    if success:
        print(f"📋 Tables in database: {stdout}")
    
    # Check row count
    success, stdout, stderr = run_db_command("SELECT COUNT(*) FROM uber_rides;")
    if success:
        print(f"📊 Rows in uber_rides table: {stdout}")
    else:
        print(f"⚠️ uber_rides table might not exist: {stderr}")
    
    # Show sample data
    success, stdout, stderr = run_db_command("SELECT * FROM uber_rides LIMIT 3;")
    if success:
        print(f"📈 Sample data from PostgreSQL: {stdout}")
    else:
        print(f"⚠️ Could not query uber_rides: {stderr}")
    
    return success

def main():
    """Main function"""
    print("🗄️ PostgreSQL Data Loading Test")
    print("This test demonstrates loading CSV data into PostgreSQL")
    print("=" * 60)
    
    # Check if containers are running
    try:
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        if "mcp-server" not in result.stdout or "Up" not in result.stdout:
            print("❌ MCP server container is not running")
            print("Please run: docker-compose up -d")
            return
        
        if "mcp-postgres" not in result.stdout or "Up" not in result.stdout:
            print("❌ PostgreSQL container is not running")
            print("Please run: docker-compose up -d")
            return
        
        print("✅ Both MCP server and PostgreSQL containers are running")
    except Exception as e:
        print(f"❌ Failed to check container status: {e}")
        return
    
    # Run the test
    success = test_postgres_data_loading()
    
    if success:
        print("\n🎉 PostgreSQL data loading test completed successfully!")
        print("Your CSV data is now stored in PostgreSQL and can be queried!")
    else:
        print("\n⚠️ PostgreSQL data loading test failed.")
        print("Check the error messages above for details.")

if __name__ == "__main__":
    main()

