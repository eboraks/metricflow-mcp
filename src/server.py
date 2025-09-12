import os
import asyncio
from fastmcp import FastMCP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from csv_importer import CSVImporter
from models import create_tables
from kaggle_downloader import KaggleDownloader
import logging

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Initialize CSV importer and Kaggle downloader
csv_importer = CSVImporter()
kaggle_downloader = KaggleDownloader()

mcp = FastMCP("csv-mcp-server")

async def test_db_connection() -> str:
    """Test the Postgres + pgvector connection."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            return str(result.scalar())
    except Exception as e:
        return f"Database connection failed: {str(e)}"

mcp.tool()(test_db_connection)

async def analyze_csv(csv_path: str) -> str:
    """Analyze a CSV file and return its structure and metadata."""
    try:
        analysis = csv_importer.analyze_csv(csv_path)
        return f"CSV Analysis:\n" \
               f"- File: {analysis['file_path']}\n" \
               f"- Rows: {analysis['total_rows']}\n" \
               f"- Columns: {', '.join(analysis['columns'])}\n" \
               f"- Size: {analysis['file_size_mb']:.2f} MB\n" \
               f"- Sample data: {analysis['sample_data'][:2]}"
    except Exception as e:
        return f"Error analyzing CSV: {str(e)}"

mcp.tool()(analyze_csv)

async def import_csv(csv_path: str, table_name: str = "csv_data") -> str:
    """Import a CSV file into the database."""
    try:
        result = csv_importer.create_table_from_csv(csv_path, table_name)
        return f"Success: {result}"
    except Exception as e:
        return f"Error importing CSV: {str(e)}"

mcp.tool()(import_csv)

async def query_data(table_name: str = "csv_data", limit: int = 10) -> str:
    """Query data from the imported CSV table."""
    try:
        data = csv_importer.query_table(table_name, limit)
        if not data:
            return f"No data found in table '{table_name}'"
        
        # Get column names from first row
        columns = list(data[0].keys()) if data else []
        
        # Format the data nicely with column headers
        result = f"📊 Data from '{table_name}' (showing {len(data)} rows):\n"
        result += f"📋 Columns ({len(columns)}): {', '.join(columns)}\n"
        result += "=" * 80 + "\n"
        
        for i, row in enumerate(data, 1):
            result += f"\n🔹 Row {i}:\n"
            for key, value in row.items():
                # Truncate long values for better display
                display_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                result += f"  📌 {key}: {display_value}\n"
        
        return result
    except Exception as e:
        return f"Error querying data: {str(e)}"

mcp.tool()(query_data)

async def get_table_info(table_name: str = "csv_data") -> str:
    """Get information about a database table."""
    try:
        info = csv_importer.get_table_info(table_name)
        if "error" in info:
            return info["error"]
        
        result = f"📋 Table: {info['table_name']}\n"
        result += f"📊 Rows: {info['row_count']}\n"
        result += f"📝 Columns ({len(info['columns'])}):\n"
        result += "=" * 60 + "\n"
        
        for i, col in enumerate(info['columns'], 1):
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            result += f"  {i:2d}. 📌 {col['name']:<20} | {col['type']:<15} | {nullable}\n"
        
        return result
    except Exception as e:
        return f"Error getting table info: {str(e)}"

mcp.tool()(get_table_info)

async def list_tables() -> str:
    """List all tables in the database."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if not tables:
                return "No tables found in the database."
            
            return f"Tables in database:\n" + "\n".join(f"- {table}" for table in tables)
    except Exception as e:
        return f"Error listing tables: {str(e)}"

mcp.tool()(list_tables)

async def download_kaggle_dataset(dataset_name: str) -> str:
    """Download a dataset from Kaggle and return information about the downloaded files."""
    try:
        result = kaggle_downloader.download_dataset(dataset_name)
        
        if result["status"] == "error":
            return f"Error downloading dataset: {result['error']}"
        
        response = f"✅ Successfully downloaded dataset: {result['dataset_name']}\n"
        response += f"📁 Download path: {result['download_path']}\n"
        response += f"📊 Total files: {result['total_files']}\n"
        response += f"📈 CSV files: {result['csv_files']}\n\n"
        
        if result['csv_file_paths']:
            response += "CSV files ready for import:\n"
            for csv_path in result['csv_file_paths']:
                response += f"- {csv_path}\n"
        
        return response
        
    except Exception as e:
        return f"Error downloading Kaggle dataset: {str(e)}"

mcp.tool()(download_kaggle_dataset)

async def list_downloaded_datasets() -> str:
    """List all downloaded Kaggle datasets."""
    try:
        datasets = kaggle_downloader.list_downloaded_datasets()
        
        if not datasets:
            return "No datasets downloaded yet."
        
        response = "Downloaded datasets:\n"
        for dataset in datasets:
            response += f"\n📁 {dataset['name']}\n"
            response += f"   Path: {dataset['path']}\n"
            response += f"   Files: {dataset['file_count']}\n"
            if dataset['files']:
                response += f"   Sample files: {', '.join(dataset['files'][:5])}\n"
        
        return response
        
    except Exception as e:
        return f"Error listing datasets: {str(e)}"

mcp.tool()(list_downloaded_datasets)

async def import_kaggle_csv(dataset_name: str, csv_filename: str, table_name: str = None) -> str:
    """Import a specific CSV file from a downloaded Kaggle dataset."""
    try:
        # First, download the dataset if not already downloaded
        download_result = kaggle_downloader.download_dataset(dataset_name)
        
        if download_result["status"] == "error":
            return f"Error downloading dataset: {download_result['error']}"
        
        # Find the specific CSV file
        csv_files = download_result["csv_file_paths"]
        target_csv = None
        
        for csv_path in csv_files:
            if csv_filename in csv_path or csv_filename == os.path.basename(csv_path):
                target_csv = csv_path
                break
        
        if not target_csv:
            available_files = [os.path.basename(f) for f in csv_files]
            return f"CSV file '{csv_filename}' not found. Available files: {', '.join(available_files)}"
        
        # Set default table name if not provided
        if not table_name:
            table_name = os.path.splitext(csv_filename)[0].replace('-', '_').replace(' ', '_')
        
        # Import the CSV
        import_result = csv_importer.create_table_from_csv(target_csv, table_name)
        
        return f"✅ Successfully imported {csv_filename} into table '{table_name}'\n{import_result}"
        
    except Exception as e:
        return f"Error importing Kaggle CSV: {str(e)}"

mcp.tool()(import_kaggle_csv)

if __name__ == "__main__":
    # Create tables on startup
    try:
        create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
    
    asyncio.run(mcp.run())
