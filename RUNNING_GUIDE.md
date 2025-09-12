# 🚀 How to Run Your MCP Server

Your MCP server is now ready for production use! Here are all the ways to run and interact with it.

## 📋 Prerequisites

- ✅ Docker Desktop installed and running
- ✅ Git repository cloned
- ✅ All dependencies configured

## 🐳 Method 1: Docker (Recommended)

### Start the Server
```bash
# Start both database and MCP server
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f server
```

### Stop the Server
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears database)
docker-compose down -v
```

## 🧪 Method 2: Local Development

### Install Dependencies
```bash
# Install Poetry (if not already installed)
pip install poetry

# Install project dependencies
poetry install
```

### Create Environment File
```bash
# Copy the example environment file
cp env.example .env

# Edit .env with your database settings
# DATABASE_URL=postgresql+psycopg2://mcpuser:mcppass@localhost:5432/mcpdb
```

### Run Locally
```bash
# Start PostgreSQL locally first, then:
poetry run python src/server.py
```

## 🔧 Available MCP Tools

Your server provides these tools:

### Database Tools
- **`test_db_connection()`** - Test database connectivity
- **`list_tables()`** - List all database tables
- **`get_table_info(table_name)`** - Get table structure info
- **`query_data(table_name, limit)`** - Query data from tables

### CSV Tools
- **`analyze_csv(csv_path)`** - Analyze CSV file structure
- **`import_csv(csv_path, table_name)`** - Import CSV to database

### Kaggle Tools
- **`download_kaggle_dataset(dataset_name)`** - Download Kaggle datasets
- **`list_downloaded_datasets()`** - List downloaded datasets
- **`import_kaggle_csv(dataset_name, csv_filename, table_name)`** - Import from Kaggle

## 🧪 Testing Your Server

### Quick Test
```bash
# Run comprehensive test suite
python tests/docker_test.py
```

### Interactive Testing
```bash
# Menu-driven testing interface
python tests/interactive_test.py
```

### Full MCP Protocol Testing
```bash
# Test all tools via MCP protocol
python tests/test_client.py --comprehensive
```

## 📊 Example Usage

### 1. Download Uber Dataset
```bash
# Connect to your MCP client and run:
download_kaggle_dataset("yashdevladdha/uber-ride-analytics-dashboard")
```

### 2. Import CSV Data
```bash
# Import a specific CSV file
import_kaggle_csv("yashdevladdha/uber-ride-analytics-dashboard", "uber_data.csv", "uber_rides")
```

### 3. Query Data
```bash
# View imported data
query_data("uber_rides", 10)

# Get table structure
get_table_info("uber_rides")
```

## 🔌 Connecting MCP Clients

### Using Claude Desktop
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "csv-mcp-server": {
      "command": "docker-compose",
      "args": ["exec", "server", "poetry", "run", "python", "src/server.py"],
      "cwd": "/path/to/your/metricflow-mcp"
    }
  }
}
```

### Using Other MCP Clients
Your server communicates via **STDIO** and supports the **Model Context Protocol (MCP)**.

## 🐛 Troubleshooting

### Server Won't Start
```bash
# Check Docker status
docker --version
docker-compose --version

# Rebuild containers
docker-compose up --build -d

# Check logs
docker-compose logs server
```

### Database Connection Issues
```bash
# Check database container
docker-compose ps

# Test database connection
docker-compose exec db psql -U mcpuser -d mcpdb -c "SELECT version();"
```

### Dependencies Missing
```bash
# Rebuild with fresh dependencies
docker-compose down
docker-compose up --build -d
```

## 📁 Project Structure

```
metricflow-mcp/
├── src/                    # Source code
│   ├── server.py          # Main MCP server
│   ├── csv_importer.py    # CSV import functionality
│   ├── kaggle_downloader.py # Kaggle integration
│   └── models.py          # Database models
├── tests/                 # Test suite
│   ├── docker_test.py     # Comprehensive testing
│   ├── interactive_test.py # Interactive testing
│   └── test_client.py     # MCP protocol testing
├── docker-compose.yml     # Docker configuration
├── Dockerfile            # Container definition
├── pyproject.toml        # Dependencies
└── env.example           # Environment template
```

## 🎯 Next Steps

1. **Start your server**: `docker-compose up -d`
2. **Test functionality**: `python tests/docker_test.py`
3. **Connect your MCP client** to the server
4. **Download and import datasets** using the available tools
5. **Query and analyze your data** through MCP tools

Your MCP server is production-ready! 🎉
