# MCP Server Test Suite

This folder contains various test clients and utilities for testing the MCP server functionality.

## Test Files

### 1. `docker_test.py` - Comprehensive Component Testing ✅
**Recommended for most testing**

Tests all server components inside the Docker container:
```bash
python tests/docker_test.py
```

**What it tests:**
- Database connection
- CSV importer functionality
- Kaggle downloader functionality
- MCP tools
- Kaggle dataset download

### 2. `interactive_test.py` - Interactive Menu Testing
**User-friendly menu-driven testing**

```bash
python tests/interactive_test.py
```

**Features:**
- Menu-driven interface
- Individual tool testing
- Custom tool testing
- Easy to use

### 3. `test_client.py` - Full MCP Protocol Testing
**Complete MCP client with command-line options**

```bash
# Run comprehensive test
python tests/test_client.py --comprehensive

# List available tools
python tests/test_client.py --list

# Test specific tool
python tests/test_client.py --tool test_db_connection

# Run server locally instead of Docker
python tests/test_client.py --local
```

### 4. `simple_test.py` - Local Component Testing
**Tests components locally (requires local dependencies)**

```bash
python tests/simple_test.py
```

**Note:** Requires all dependencies installed locally via Poetry.

### 5. `test_csv_columns.py` - CSV Column Display Testing
**Specialized test for CSV column display and data analysis**

```bash
python tests/test_csv_columns.py
```

**Features:**
- Downloads Kaggle datasets
- Shows all CSV columns clearly
- Displays table structure with column types
- Shows sample data with all columns
- Enhanced column formatting with emojis and formatting

## Prerequisites

Before running tests, ensure:

1. **Docker is running** (for Docker-based tests)
2. **MCP server is started**:
   ```bash
   docker-compose up -d
   ```
3. **Dependencies are installed** (for local tests):
   ```bash
   poetry install
   ```

## Quick Start

1. **Start the MCP server:**
   ```bash
   docker-compose up -d
   ```

2. **Run comprehensive test:**
   ```bash
   python tests/docker_test.py
   ```

3. **Use interactive testing:**
   ```bash
   python tests/interactive_test.py
   ```

## Test Results

All tests should show:
- ✅ Database connection working
- ✅ CSV importer ready
- ✅ Kaggle downloader ready
- ✅ MCP tools functional
- ✅ Kaggle dataset download working

If any tests fail, check:
- Docker containers are running
- Database is accessible
- Dependencies are installed
- Environment variables are set
