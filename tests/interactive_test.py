#!/usr/bin/env python3
"""
Interactive test client for the MCP server
Simple command-line interface to test MCP tools
"""

import asyncio
import json
import subprocess
import sys
import os
from typing import Dict, Any

class InteractiveMCPClient:
    def __init__(self):
        self.server_process = None
    
    async def start_server(self):
        """Start the MCP server"""
        try:
            # Try Docker first, fallback to local
            try:
                self.server_process = await asyncio.create_subprocess_exec(
                    "docker-compose", "exec", "-T", "server", "poetry", "run", "python", "src/server.py",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                print("✅ Started MCP server via Docker")
            except:
                # Fallback to local execution
                self.server_process = await asyncio.create_subprocess_exec(
                    "poetry", "run", "python", "src/server.py",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                print("✅ Started MCP server locally")
            
            return True
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    async def send_mcp_request(self, method: str, params: Dict[str, Any] = None) -> str:
        """Send a request to the MCP server and return the response"""
        if not self.server_process:
            return "❌ Server not started"
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        try:
            request_json = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_json.encode())
            await self.server_process.stdin.drain()
            
            response_line = await self.server_process.stdout.readline()
            if response_line:
                response = json.loads(response_line.decode().strip())
                if "result" in response and "content" in response["result"]:
                    return response["result"]["content"][0].get("text", "No content")
                elif "error" in response:
                    return f"❌ Error: {response['error']}"
                else:
                    return f"⚠️ Unexpected response: {response}"
            else:
                return "❌ No response from server"
                
        except Exception as e:
            return f"❌ Request failed: {e}"
    
    async def test_database_connection(self):
        """Test database connection"""
        print("\n🔌 Testing database connection...")
        result = await self.send_mcp_request("tools/call", {
            "name": "test_db_connection",
            "arguments": {}
        })
        print(f"Result: {result}")
    
    async def test_kaggle_download(self):
        """Test Kaggle dataset download"""
        print("\n📥 Testing Kaggle dataset download...")
        result = await self.send_mcp_request("tools/call", {
            "name": "download_kaggle_dataset",
            "arguments": {"dataset_name": "yashdevladdha/uber-ride-analytics-dashboard"}
        })
        print(f"Result: {result}")
    
    async def test_list_tables(self):
        """Test listing database tables"""
        print("\n📋 Testing list tables...")
        result = await self.send_mcp_request("tools/call", {
            "name": "list_tables",
            "arguments": {}
        })
        print(f"Result: {result}")
    
    async def test_list_datasets(self):
        """Test listing downloaded datasets"""
        print("\n📁 Testing list downloaded datasets...")
        result = await self.send_mcp_request("tools/call", {
            "name": "list_downloaded_datasets",
            "arguments": {}
        })
        print(f"Result: {result}")
    
    async def run_quick_test(self):
        """Run a quick test of basic functionality"""
        print("🚀 Running quick MCP server test...")
        
        if not await self.start_server():
            return
        
        try:
            await self.test_database_connection()
            await self.test_list_tables()
            await self.test_kaggle_download()
            await self.test_list_datasets()
            
            print("\n✅ Quick test completed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up the server process"""
        if self.server_process:
            self.server_process.terminate()
            await self.server_process.wait()
            print("🧹 Server process cleaned up")

def print_menu():
    """Print the interactive menu"""
    print("\n" + "="*50)
    print("🔧 MCP Server Test Client")
    print("="*50)
    print("1. Quick Test (Database + Kaggle)")
    print("2. Test Database Connection")
    print("3. Test Kaggle Download")
    print("4. List Database Tables")
    print("5. List Downloaded Datasets")
    print("6. Custom Tool Test")
    print("0. Exit")
    print("="*50)

async def main():
    """Main interactive function"""
    client = InteractiveMCPClient()
    
    while True:
        print_menu()
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            await client.run_quick_test()
        elif choice == "2":
            if await client.start_server():
                await client.test_database_connection()
                await client.cleanup()
        elif choice == "3":
            if await client.start_server():
                await client.test_kaggle_download()
                await client.cleanup()
        elif choice == "4":
            if await client.start_server():
                await client.test_list_tables()
                await client.cleanup()
        elif choice == "5":
            if await client.start_server():
                await client.test_list_datasets()
                await client.cleanup()
        elif choice == "6":
            tool_name = input("Enter tool name: ").strip()
            if tool_name:
                if await client.start_server():
                    result = await client.send_mcp_request("tools/call", {
                        "name": tool_name,
                        "arguments": {}
                    })
                    print(f"Result: {result}")
                    await client.cleanup()
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
