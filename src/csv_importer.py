import pandas as pd
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CSVImporter:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not provided")
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def analyze_csv(self, csv_path: str) -> dict:
        """Analyze CSV file structure and return metadata"""
        try:
            # Read first few rows to analyze structure
            df_sample = pd.read_csv(csv_path, nrows=5)
            
            analysis = {
                "file_path": csv_path,
                "total_rows": len(pd.read_csv(csv_path)),
                "columns": list(df_sample.columns),
                "column_types": df_sample.dtypes.to_dict(),
                "sample_data": df_sample.head(3).to_dict('records'),
                "file_size_mb": os.path.getsize(csv_path) / (1024 * 1024)
            }
            
            logger.info(f"CSV Analysis: {analysis['total_rows']} rows, {len(analysis['columns'])} columns")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing CSV: {e}")
            raise
    
    def create_table_from_csv(self, csv_path: str, table_name: str = "csv_data") -> str:
        """Create a table based on CSV structure and import data"""
        try:
            # Read CSV
            df = pd.read_csv(csv_path)

            inspector = inspect(self.engine)
            table_exists = inspector.has_table(table_name)

            # If table exists, TRUNCATE it to avoid dropping dependencies (e.g., views), then append
            if table_exists:
                with self.engine.begin() as conn:
                    conn.execute(text(f"TRUNCATE TABLE {table_name};"))
                if_exists_mode = 'append'
            else:
                if_exists_mode = 'fail'

            # Load data
            df.to_sql(
                name=table_name,
                con=self.engine,
                if_exists=if_exists_mode,
                index=False,
                method='multi',
                chunksize=10000
            )
            
            # Get row count
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar()
            
            logger.info(f"Successfully imported {row_count} rows into table '{table_name}'")
            return f"Imported {row_count} rows into table '{table_name}'"
            
        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            raise
    
    def query_table(self, table_name: str, limit: int = 10) -> list:
        """Query data from the imported table"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
                columns = result.keys()
                rows = result.fetchall()
                
                # Convert to list of dictionaries
                data = [dict(zip(columns, row)) for row in rows]
                return data
                
        except Exception as e:
            logger.error(f"Error querying table: {e}")
            raise
    
    def get_table_info(self, table_name: str) -> dict:
        """Get information about a table"""
        try:
            inspector = inspect(self.engine)
            
            if not inspector.has_table(table_name):
                return {"error": f"Table '{table_name}' does not exist"}
            
            columns = inspector.get_columns(table_name)
            
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar()
            
            return {
                "table_name": table_name,
                "row_count": row_count,
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"]
                    }
                    for col in columns
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            raise
