# metricflow-mcp

## Tech Stack
- Docker Compose: Orchestrates Postgres and the MCP server services.
- PostgreSQL 15: Primary relational database for storing imported datasets.
- SQLAlchemy: Database engine/ORM for connections and SQL execution.
- psycopg2-binary: PostgreSQL driver used by SQLAlchemy and data loaders.
- Python 3.12: Runtime for the MCP server, tools, and tests.
- FastMCP: Framework for defining and exposing MCP tools in the server.
- pandas: CSV parsing and data loading into Postgres.
- kagglehub: Downloads datasets from Kaggle for local import.
- Alembic: Database migration tooling (included in dependencies).
- ChromaDB (optional): Local vector store used by the Vanna demo.
- Google Generative AI (optional): Gemini LLM used in the Vanna demo.