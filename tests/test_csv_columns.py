#!/usr/bin/env python3
"""
Test script specifically for testing CSV column display
This script focuses on downloading data and showing all columns clearly
"""

import subprocess
import json
import sys

def run_docker_command(command):
    """Run a command inside the Docker container"""
    try:
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "server"] + command,
            capture_output=True,
            text=True,
            timeout=60  # Longer timeout for downloads
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_csv_columns_display():
    """Test CSV column display with detailed output"""
    print("🚀 Testing CSV Column Display")
    print("=" * 60)
    
    test_script = '''
import asyncio
import sys
sys.path.append('/app/src')

import server

async def test_csv_columns():
    print("📥 Step 1: Downloading Kaggle dataset...")
    try:
        download_result = await server.download_kaggle_dataset("yashdevladdha/uber-ride-analytics-dashboard")
        print(f"✅ Download successful!")
        print(f"📁 {download_result}")
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return
    
    print("\\n📁 Step 2: Listing downloaded datasets...")
    try:
        datasets_result = await server.list_downloaded_datasets()
        print(f"📂 {datasets_result}")
    except Exception as e:
        print(f"❌ Failed to list datasets: {e}")
    
    print("\\n📊 Step 3: Attempting to import CSV data...")
    try:
        # Try different possible CSV filenames
        possible_files = ["uber_data.csv", "data.csv", "rides.csv", "uber_rides.csv"]
        
        for filename in possible_files:
            try:
                print(f"\\n🔄 Trying to import: {filename}")
                import_result = await server.import_kaggle_csv(
                    "yashdevladdha/uber-ride-analytics-dashboard", 
                    filename, 
                    "uber_rides"
                )
                print(f"✅ Import successful: {import_result}")
                break
            except Exception as import_error:
                print(f"⚠️ Failed to import {filename}: {import_error}")
                continue
        else:
            print("\\n❌ Could not import any CSV files. The dataset might not contain CSV files.")
            return
        
        print("\\n📋 Step 4: Getting table structure (ALL COLUMNS)...")
        try:
            table_info = await server.get_table_info("uber_rides")
            print(f"\\n📊 TABLE STRUCTURE:")
            print("=" * 80)
            print(table_info)
        except Exception as e:
            print(f"❌ Failed to get table info: {e}")
        
        print("\\n📊 Step 5: Querying sample data (showing ALL COLUMNS)...")
        try:
            query_result = await server.query_data("uber_rides", 5)
            print(f"\\n📈 SAMPLE DATA WITH ALL COLUMNS:")
            print("=" * 80)
            print(query_result)
        except Exception as e:
            print(f"❌ Failed to query data: {e}")
        
        print("\\n📋 Step 6: Listing all tables...")
        try:
            tables_result = await server.list_tables()
            print(f"\\n📂 {tables_result}")
        except Exception as e:
            print(f"❌ Failed to list tables: {e}")
            
    except Exception as e:
        print(f"❌ CSV import process failed: {e}")

asyncio.run(test_csv_columns())
'''
    
    success, stdout, stderr = run_docker_command([
        "poetry", "run", "python", "-c", test_script
    ])
    
    print("\\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print("=" * 60)
    
    if success:
        print("✅ Test completed successfully!")
        print("\\n📋 OUTPUT:")
        print(stdout)
    else:
        print("❌ Test failed!")
        print("\\n📋 ERROR:")
        print(stderr)
    
    return success

def main():
    """Main function"""
    print("🧪 CSV Column Display Test")
    print("This test will download a Kaggle dataset and show all CSV columns")
    print("=" * 60)
    
    # Check if containers are running
    try:
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True
        )
        
        if "mcp-server" not in result.stdout or "Up" not in result.stdout:
            print("❌ MCP server container is not running")
            print("Please run: docker-compose up -d")
            return
        
        print("✅ MCP server container is running")
    except Exception as e:
        print(f"❌ Failed to check container status: {e}")
        return
    
    # Run the test
    success = test_csv_columns_display()
    
    if success:
        print("\\n🎉 CSV column display test completed successfully!")
        print("You should see all columns from the CSV data displayed above.")
    else:
        print("\\n⚠️ CSV column display test failed.")
        print("Check the error messages above for details.")

if __name__ == "__main__":
    main()
