import os
import argparse
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.csv_importer import CSVImporter


def sanitize_table_name(filename: str) -> str:
	base = os.path.splitext(os.path.basename(filename))[0]
	return (
		base.replace("-", "_")
		.replace(" ", "_")
		.replace("/", "_")
		.replace(".", "_")
		.lower()
	)


def main() -> None:
	load_dotenv()

	parser = argparse.ArgumentParser(description="Import a local CSV file into PostgreSQL")
	parser.add_argument("csv_path", help="Path to the local CSV file")
	parser.add_argument("--table", dest="table_name", default=None, help="Target table name (defaults to sanitized file name)")
	parser.add_argument("--db", dest="database_url", default=os.getenv("DATABASE_URL"), help="SQLAlchemy database URL (defaults to env DATABASE_URL)")
	args = parser.parse_args()

	csv_path = args.csv_path
	if not os.path.exists(csv_path):
		raise FileNotFoundError(f"CSV not found: {csv_path}")

	database_url = args.database_url or "postgresql+psycopg2://mcpuser:mcppass@localhost:5432/mcpdb"
	# Minimal host fix for local run if env was configured for docker host 'db'
	database_url = database_url.replace("@db:", "@localhost:")

	table_name = args.table_name or sanitize_table_name(csv_path)

	print(f"Importing CSV -> Postgres")
	print(f"  CSV:   {csv_path}")
	print(f"  Table: {table_name}")
	print(f"  DB:    {database_url}")

	importer = CSVImporter(database_url=database_url)
	engine = create_engine(database_url)

	# Import using TRUNCATE+append behavior if table exists (handled inside CSVImporter)
	msg = importer.create_table_from_csv(csv_path, table_name)
	print(msg)

	# Report row count
	with engine.connect() as conn:
		result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
		row_count = result.scalar() or 0
	print(f"Row count in {table_name}: {row_count}")

	print("Done.")


if __name__ == "__main__":
	main()


