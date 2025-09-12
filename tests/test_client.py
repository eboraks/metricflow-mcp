#!/usr/bin/env python3
"""
Test client for the MCP server
This client can be used to test all MCP tools without needing a full MCP client setup
"""

import asyncio
import json
import subprocess
import sys
from typing import Dict, Any, List
import argparse

class MCPTestClient:
    def __init__(self, server_command: List[str] = None):
        """Initialize the test client with server command"""
        self.server_command = server_command or ["docker-compose", "exec", "server", "poetry", "run", "python", "src/server.py"]
        self.process = None
    
    async def start_server(self):
        """Start the MCP server process"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            print("✅ MCP Server started successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}")
            return False
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a request to the MCP server"""
        if not self.process:
            raise RuntimeError("Server not started")
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        request_json = json.dumps(request) + "\n"
        
        try:
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read response
            response_line = await self.process.stdout.readline()
            if response_line:
                response = json.loads(response_line.decode().strip())
                return response
            else:
                return {"error": "No response from server"}
                
        except Exception as e:
            return {"error": f"Request failed: {e}"}
    
    async def test_tool(self, tool_name: str, **kwargs) -> str:
        """Test a specific MCP tool"""
        print(f"\n🔧 Testing tool: {tool_name}")
        print(f"📝 Parameters: {kwargs}")
        
        response = await self.send_request("tools/call", {
            "name": tool_name,
            "arguments": kwargs
        })
        
        if "error" in response:
            result = f"❌ Error: {response['error']}"
        elif "result" in response:
            result = f"✅ Success: {response['result'].get('content', [{}])[0].get('text', 'No content')}"
        else:
            result = f"⚠️ Unexpected response: {response}"
        
        print(f"📊 Result: {result}")
        return result
    
    async def list_tools(self) -> List[str]:
        """List available tools"""
        print("\n📋 Listing available tools...")
        
        response = await self.send_request("tools/list")
        
        if "result" in response and "tools" in response["result"]:
            tools = [tool["name"] for tool in response["result"]["tools"]]
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool}")
            return tools
        else:
            print(f"❌ Failed to list tools: {response}")
            return []
    
    async def run_comprehensive_test(self):
        """Run a comprehensive test of all MCP tools"""
        print("🚀 Starting comprehensive MCP server test...")
        
        # Start server
        if not await self.start_server():
            return
        
        try:
            # List available tools
            tools = await self.list_tools()
            
            if not tools:
                print("❌ No tools found, stopping test")
                return
            
            # Test basic database connection
            await self.test_tool("test_db_connection")
            
            # Test listing tables (should be empty initially)
            await self.test_tool("list_tables")
            
            # Test Kaggle dataset download
            print("\n📥 Testing Kaggle dataset download...")
            await self.test_tool("download_kaggle_dataset", 
                               dataset_name="yashdevladdha/uber-ride-analytics-dashboard")
            
            # List downloaded datasets
            await self.test_tool("list_downloaded_datasets")
            
            # Test CSV analysis (if we have a local CSV file)
            print("\n📊 Testing CSV analysis...")
            # This would work if you have a local CSV file
            # await self.test_tool("analyze_csv", csv_path="sample_data.csv")
            
            print("\n✅ Comprehensive test completed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up the server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            print("🧹 Server process cleaned up")

async def main():
    """Main function to run the test client"""
    parser = argparse.ArgumentParser(description="Test client for MCP server")
    parser.add_argument("--tool", help="Test a specific tool")
    parser.add_argument("--list", action="store_true", help="List available tools")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive test")
    parser.add_argument("--local", action="store_true", help="Run server locally instead of Docker")
    
    args = parser.parse_args()
    
    # Choose server command based on args
    if args.local:
        server_command = ["poetry", "run", "python", "src/server.py"]
    else:
        server_command = ["docker-compose", "exec", "server", "poetry", "run", "python", "src/server.py"]
    
    client = MCPTestClient(server_command)
    
    try:
        if args.comprehensive:
            await client.run_comprehensive_test()
        elif args.list:
            await client.start_server()
            await client.list_tools()
            await client.cleanup()
        elif args.tool:
            await client.start_server()
            # Parse tool arguments (simple implementation)
            tool_args = {}
            if "=" in args.tool:
                tool_name, params = args.tool.split("=", 1)
                # Simple parameter parsing - you can extend this
                tool_args = {"dataset_name": params}
            else:
                tool_name = args.tool
            
            await client.test_tool(tool_name, **tool_args)
            await client.cleanup()
        else:
            print("🔧 MCP Test Client")
            print("Usage:")
            print("  python test_client.py --comprehensive    # Run full test suite")
            print("  python test_client.py --list            # List available tools")
            print("  python test_client.py --tool test_db_connection  # Test specific tool")
            print("  python test_client.py --local           # Run server locally")
            print("\nExample:")
            print("  python test_client.py --tool download_kaggle_dataset=yashdevladdha/uber-ride-analytics-dashboard")
    
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
