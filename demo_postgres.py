#!/usr/bin/env python3
"""
Simple demonstration of loading data into PostgreSQL
"""

import subprocess

def run_command(command):
    """Run a command and return output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🗄️ PostgreSQL Data Loading Demonstration")
    print("=" * 50)
    
    print("📊 Step 1: Check PostgreSQL connection")
    success, stdout, stderr = run_command("docker-compose exec -T db psql -U mcpuser -d mcpdb -c \"SELECT 'PostgreSQL is running!' as status;\"")
    if success:
        print(f"✅ {stdout.strip()}")
    else:
        print(f"❌ PostgreSQL connection failed: {stderr}")
        return
    
    print("\n📋 Step 2: List current tables")
    success, stdout, stderr = run_command("docker-compose exec -T db psql -U mcpuser -d mcpdb -c \"\\dt\"")
    if success:
        print(f"📊 Current tables:\n{stdout}")
    else:
        print(f"❌ Failed to list tables: {stderr}")
    
    print("\n📝 Step 3: Create sample data in PostgreSQL")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS demo_data (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        age INTEGER,
        city VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    success, stdout, stderr = run_command(f"docker-compose exec -T db psql -U mcpuser -d mcpdb -c \"{create_table_sql}\"")
    if success:
        print("✅ Sample table created")
    else:
        print(f"❌ Failed to create table: {stderr}")
    
    print("\n📊 Step 4: Insert sample data")
    insert_sql = """
    INSERT INTO demo_data (name, age, city) VALUES 
    ('Alice Johnson', 28, 'New York'),
    ('Bob Smith', 34, 'London'),
    ('Charlie Brown', 29, 'Paris'),
    ('Diana Prince', 31, 'Tokyo'),
    ('Eve Wilson', 26, 'Sydney');
    """
    
    success, stdout, stderr = run_command(f"docker-compose exec -T db psql -U mcpuser -d mcpdb -c \"{insert_sql}\"")
    if success:
        print("✅ Sample data inserted")
    else:
        print(f"❌ Failed to insert data: {stderr}")
    
    print("\n📈 Step 5: Query the data")
    success, stdout, stderr = run_command("docker-compose exec -T db psql -U mcpuser -d mcpdb -c \"SELECT * FROM demo_data;\"")
    if success:
        print(f"📊 Data in PostgreSQL:\n{stdout}")
    else:
        print(f"❌ Failed to query data: {stderr}")
    
    print("\n📋 Step 6: Show table structure")
    success, stdout, stderr = run_command("docker-compose exec -T db psql -U mcpuser -d mcpdb -c \"\\d demo_data\"")
    if success:
        print(f"📝 Table structure:\n{stdout}")
    else:
        print(f"❌ Failed to show table structure: {stderr}")
    
    print("\n🎉 Demonstration Complete!")
    print("Your MCP server works the same way - it loads CSV data into PostgreSQL tables!")

if __name__ == "__main__":
    main()

