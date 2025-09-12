#!/usr/bin/env python3
"""
Simple test script to verify MCP server functionality
Tests the server components directly without MCP protocol
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, 'src')

# Load environment variables
load_dotenv()

async def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from csv_importer import CSVImporter
        from kaggle_downloader import KaggleDownloader
        from models import create_tables, get_database_engine
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_database_connection():
    """Test database connection"""
    print("\n🔌 Testing database connection...")
    
    try:
        from models import get_database_engine
        from sqlalchemy import text
        
        engine = get_database_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Database connected: {version}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_csv_importer():
    """Test CSV importer functionality"""
    print("\n📊 Testing CSV importer...")
    
    try:
        from csv_importer import CSVImporter
        
        importer = CSVImporter()
        print("✅ CSV importer initialized")
        return True
    except Exception as e:
        print(f"❌ CSV importer failed: {e}")
        return False

async def test_kaggle_downloader():
    """Test Kaggle downloader functionality"""
    print("\n📥 Testing Kaggle downloader...")
    
    try:
        from kaggle_downloader import KaggleDownloader
        
        downloader = KaggleDownloader()
        print("✅ Kaggle downloader initialized")
        return True
    except Exception as e:
        print(f"❌ Kaggle downloader failed: {e}")
        return False

async def test_mcp_tools():
    """Test MCP tools directly"""
    print("\n🔧 Testing MCP tools...")
    
    try:
        # Import the server module to access tools
        import server
        
        # Test database connection tool
        result = await server.test_db_connection()
        print(f"✅ Database connection tool: {result[:100]}...")
        
        # Test list tables tool
        result = await server.list_tables()
        print(f"✅ List tables tool: {result}")
        
        print("✅ MCP tools working")
        return True
    except Exception as e:
        print(f"❌ MCP tools failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting MCP Server Component Tests...")
    print("="*50)
    
    tests = [
        ("Imports", test_imports),
        ("Database Connection", test_database_connection),
        ("CSV Importer", test_csv_importer),
        ("Kaggle Downloader", test_kaggle_downloader),
        ("MCP Tools", test_mcp_tools),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Results Summary:")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Your MCP server is ready!")
    else:
        print("⚠️ Some tests failed. Check the errors above.")

async def main():
    """Main function"""
    try:
        await run_all_tests()
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"❌ Test suite failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
