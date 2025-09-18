import argparse
import csv
import os
import sys
import psycopg2


def read_csv_header(csv_path: str) -> list[str]:
	with open(csv_path, mode='r', encoding='utf-8', newline='') as f:
		reader = csv.reader(f)
		headers = next(reader)
		return headers


def quote_ident(identifier: str) -> str:
	# Escape embedded quotes and wrap in double-quotes for PostgreSQL identifiers
	return '"' + identifier.replace('"', '""') + '"'


def main() -> None:
	parser = argparse.ArgumentParser(description="Fast CSV -> PostgreSQL via COPY")
	parser.add_argument("csv", help="Path to local CSV file")
	parser.add_argument("--table", required=True, help="Target table name (in public schema unless --schema provided)")
	parser.add_argument("--schema", default="public", help="Target schema (default: public)")
	parser.add_argument("--host", default=os.getenv("PGHOST", "localhost"))
	parser.add_argument("--port", type=int, default=int(os.getenv("PGPORT", "5432")))
	parser.add_argument("--dbname", default=os.getenv("PGDATABASE", "mcpdb"))
	parser.add_argument("--user", default=os.getenv("PGUSER", "mcpuser"))
	parser.add_argument("--password", default=os.getenv("PGPASSWORD", "mcppass"))
	parser.add_argument("--delimiter", default=",")
	parser.add_argument("--quote", default='"')
	parser.add_argument("--null-token", dest="null_token", default="null", help="String token in CSV to treat as SQL NULL (default: 'null')")
	parser.add_argument("--create-table", action="store_true", help="Create table (all TEXT columns) from CSV header if not exists")
	parser.add_argument("--truncate", action="store_true", help="TRUNCATE the table before load (keeps dependent views)")
	args = parser.parse_args()

	csv_path = args.csv
	if not os.path.exists(csv_path):
		print(f"CSV not found: {csv_path}", file=sys.stderr)
		sys.exit(1)

	headers = read_csv_header(csv_path)
	qualified_table = f"{quote_ident(args.schema)}.{quote_ident(args.table)}"
	column_list_sql = ", ".join(quote_ident(h) for h in headers)

	conn = psycopg2.connect(
		host=args.host,
		port=args.port,
		dbname=args.dbname,
		user=args.user,
		password=args.password,
	)
	conn.autocommit = False

	try:
		with conn.cursor() as cur:
			# Optionally create table with TEXT columns using exact header names
			if args.create_table:
				cols_sql = ", ".join(f"{quote_ident(h)} TEXT" for h in headers)
				cur.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_ident(args.schema)};")
				cur.execute(
					f"CREATE TABLE IF NOT EXISTS {qualified_table} ({cols_sql});"
				)

			# Optional truncate to avoid DROP when views depend on the table
			if args.truncate:
				cur.execute(f"TRUNCATE TABLE {qualified_table};")

			# COPY with CSV HEADER, explicit delimiter/quote
			copy_sql = (
				f"COPY {qualified_table} ({column_list_sql}) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER '{args.delimiter}', QUOTE '{args.quote}', NULL '{args.null_token}')"
			)
			with open(csv_path, mode='r', encoding='utf-8', newline='') as f:
				cur.copy_expert(sql=copy_sql, file=f)

			# Row count
			cur.execute(f"SELECT COUNT(*) FROM {qualified_table};")
			row_count = cur.fetchone()[0]
			print(f"Loaded {row_count} rows into {args.schema}.{args.table}")

		conn.commit()
	except Exception as e:
		conn.rollback()
		raise
	finally:
		conn.close()


if __name__ == "__main__":
	main()


