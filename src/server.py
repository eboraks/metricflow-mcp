import os
import asyncio
from fastmcp import FastMCP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

mcp = FastMCP("example-mcp-server")

@mcp.tool()
async def test_db_connection() -> str:
    """Test the Postgres + pgvector connection."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        return str(result.scalar())

if __name__ == "__main__":
    asyncio.run(mcp.run())
