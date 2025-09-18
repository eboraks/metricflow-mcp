import os
import pandas as pd
from dotenv import load_dotenv

from vanna.chromadb import ChromaDB_VectorStore
from vanna.google import GoogleGeminiChat
from sqlalchemy import create_engine, text


class MyVanna(ChromaDB_VectorStore, GoogleGeminiChat):
	def __init__(self, api_key: str, model: str):
		ChromaDB_VectorStore.__init__(self, config={})
		GoogleGeminiChat.__init__(self, config={"api_key": api_key, "model": model})


def main():
	load_dotenv()

	gemini_api_key = os.getenv("GEMINI_API")
	if not gemini_api_key:
		raise ValueError("GEMINI_API not set in .env")

	database_url = os.getenv("DATABASE_URL")
	if not database_url:
		raise ValueError("DATABASE_URL not set in .env")

	# Minimal host fix: allow local runs when .env uses docker host 'db'
	database_url = database_url.replace("@db:", "@localhost:")

	gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")

	vn = MyVanna(api_key=gemini_api_key, model=gemini_model)

	engine = create_engine(database_url)

	# Choose Uber table and create a normalized view with snake_case columns
	with engine.begin() as conn:
		# Determine target table
		preferred = os.getenv("DATA_TABLE")
		candidate_tables = []
		result = conn.execute(text("""
			SELECT table_name
			FROM information_schema.tables
			WHERE table_schema='public' AND table_type='BASE TABLE'
		"""))
		available = {row[0] for row in result.fetchall()}
		if preferred and preferred in available:
			target_table = preferred
		elif "ncr_ride_bookings" in available:
			target_table = "ncr_ride_bookings"
		elif "uber_rides" in available:
			target_table = "uber_rides"
		else:
			# Fallback: first table containing 'ride' or 'uber'
			match = [t for t in available if ("ride" in t.lower() or "uber" in t.lower())]
			target_table = match[0] if match else None

		if not target_table:
			raise ValueError("No Uber-related table found. Set DATA_TABLE env var to your table name.")

		print(f"Using Uber table: {target_table}")

		# Introspect column names for quoting and build snake_case projection
		cols = conn.execute(text(
			"""
			SELECT column_name
			FROM information_schema.columns
			WHERE table_schema='public' AND table_name=:t
			ORDER BY ordinal_position
			"""
		), {"t": target_table}).fetchall()

		def to_snake_case(name: str) -> str:
			import re
			s = name.strip().lower()
			s = re.sub(r"[^a-z0-9]+", "_", s)
			s = re.sub(r"_+", "_", s).strip("_")
			return s or "col"

		select_list = []
		snake_columns = []
		for (col_name,) in cols:
			snake = to_snake_case(col_name)
			snake_columns.append((col_name, snake))
			# Quote original column name to handle spaces/case
			select_list.append(f'"{col_name}" AS {snake}')

		view_name = "uber_bookings"
		view_sql = f"CREATE OR REPLACE VIEW {view_name} AS SELECT " + ", ".join(select_list) + f" FROM {target_table};"
		conn.execute(text(view_sql))
		print(f"Created/updated view: {view_name} with {len(snake_columns)} columns")

	def run_sql(sql: str) -> pd.DataFrame:
		with engine.connect() as conn:
			return pd.read_sql_query(sql, conn)

	vn.run_sql = run_sql
	vn.run_sql_is_set = True

	# Train on the normalized view schema
	# Build a simple DDL for the view to guide the model
	with engine.connect() as conn2:
		ddl_cols = conn2.execute(text(
			"""
			SELECT column_name, data_type
			FROM information_schema.columns
			WHERE table_schema='public' AND table_name=:v
			ORDER BY ordinal_position
			"""
		), {"v": "uber_bookings"}).fetchall()
		ddl_lines = []
		for col_name, data_type in ddl_cols:
			mapped = "text"
			if "double" in data_type or data_type in ("numeric", "real"):
				mapped = "double precision"
			elif data_type in ("integer", "bigint", "smallint"):
				mapped = "integer"
			elif "timestamp" in data_type or data_type == "date":
				mapped = data_type
			ddl_lines.append(f"\t\t{col_name} {mapped}")
		ddl_sql = "CREATE TABLE uber_bookings (\n" + ",\n".join(ddl_lines) + "\n\t)"
		vn.train(ddl=ddl_sql)

	# Documentation and Uber-specific examples
	vn.train(documentation=(
		"Uber bookings dataset: Each row is a ride booking with timestamps, status, locations, ride distance, booking value, ratings, and payment method."
	))

	vn.train(
		question="How many total rides are there?",
		sql="SELECT COUNT(*) AS total_rides FROM uber_bookings;"
	)

	vn.train(
		question="How many completed rides by day?",
		sql=(
			"SELECT date::date AS ride_date, COUNT(*) AS completed_rides "
			"FROM uber_bookings WHERE lower(booking_status) = 'completed' "
			"GROUP BY date::date ORDER BY ride_date;"
		)
	)

	vn.train(
		question="What is the average ride distance per vehicle type?",
		sql=(
			"SELECT vehicle_type, AVG(ride_distance) AS avg_distance "
			"FROM uber_bookings GROUP BY vehicle_type ORDER BY avg_distance DESC;"
		)
	)

	vn.train(
		question="Top 10 pickup locations by rides",
		sql=(
			"SELECT pickup_location, COUNT(*) AS rides "
			"FROM uber_bookings GROUP BY pickup_location ORDER BY rides DESC LIMIT 10;"
		)
	)

	vn.train(
		question="Total booking value (revenue)?",
		sql="SELECT SUM(booking_value) AS total_booking_value FROM uber_bookings;"
	)

	# Show available tables
	print("\n" + "="*60)
	print("📊 AVAILABLE DATABASE TABLES")
	print("="*60)
	try:
		with engine.connect() as conn:
			result = conn.execute(text("""
				SELECT table_name, 
				       (SELECT COUNT(*) FROM information_schema.columns 
				        WHERE table_name = t.table_name AND table_schema = 'public') as column_count
				FROM information_schema.tables t
				WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
				ORDER BY table_name;
			"""))
			tables = result.fetchall()
			for table_name, col_count in tables:
				print(f"📋 {table_name} ({col_count} columns)")
	except Exception as e:
		print(f"Error listing tables: {e}")

	# Show sample data from uber_bookings view
	print("\n" + "="*60)
	print("📈 SAMPLE DATA FROM UBER_BOOKINGS VIEW")
	print("="*60)
	try:
		with engine.connect() as conn:
			result = conn.execute(text("SELECT * FROM uber_bookings LIMIT 3"))
			df_sample = pd.read_sql_query("SELECT * FROM uber_bookings LIMIT 3", conn)
			print(df_sample.to_string(index=False))
	except Exception as e:
		print(f"Error showing sample data: {e}")

	# Test different questions
	test_questions = [
		"How many total rides are there?",
		"How many completed rides by day?",
		"What is the average ride distance per vehicle type?",
		"Top 10 pickup locations by rides",
		"Total booking value (revenue)?"
	]

	for i, question in enumerate(test_questions, 1):
		print(f"\n" + "="*60)
		print(f"🤖 TEST {i}: {question}")
		print("="*60)
		
		# Get SQL only to avoid any automatic execution
		sql = vn.generate_sql(question)
		df = None

		if sql:
			# Enhanced normalization: convert common SQLite date funcs to Postgres
			def normalize_sql_for_postgres(s: str) -> str:
				replacements = [
					("DATE('now', '-7 days')", "CURRENT_DATE - INTERVAL '7 days'"),
					("DATE('now', '-6 days')", "CURRENT_DATE - INTERVAL '6 days'"),
					("DATE('now', '-1 day')", "CURRENT_DATE - INTERVAL '1 day'"),
					("DATE('now')", "CURRENT_DATE"),
					("date('now', '-7 days')", "CURRENT_DATE - INTERVAL '7 days'"),
					("date('now', '-6 days')", "CURRENT_DATE - INTERVAL '6 days'"),
					("date('now', '-1 day')", "CURRENT_DATE - INTERVAL '1 day'"),
					("date('now')", "CURRENT_DATE"),
					("datetime('now')", "NOW()"),
			]
				for old, new in replacements:
					s = s.replace(old, new)
				return s

			sql = normalize_sql_for_postgres(sql)
			print(f"\n🔍 Generated SQL:\n{sql}")
			if df is None:
				try:
					df = vn.run_sql(sql)
					print(f"\n📊 Query Results ({len(df)} rows):")
					print(df.to_string(index=False))
				except Exception as e:
					print(f"\n❌ Failed to run generated SQL: {e}")
		else:
			print("❌ Could not generate a SQL query for the question.")


if __name__ == "__main__":
	main()


