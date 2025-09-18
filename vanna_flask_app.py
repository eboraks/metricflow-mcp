import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from vanna.chromadb import ChromaDB_VectorStore
from vanna.google import GoogleGeminiChat
from vanna.flask import VannaFlaskApp


class MyVanna(ChromaDB_VectorStore, GoogleGeminiChat):
	def __init__(self, api_key: str, model: str):
		# Use a dedicated collection to avoid mixing old 'sales' training with Uber
		ChromaDB_VectorStore.__init__(
			self,
			config={
				"collection_name": os.getenv("VANNA_COLLECTION", "uber_vanna"),
			}
		)
		GoogleGeminiChat.__init__(self, config={"api_key": api_key, "model": model})


def create_vanna_with_pg() -> tuple[MyVanna, str]:
	load_dotenv()

	gemini_api_key = os.getenv("GEMINI_API") or os.getenv("GEMINI_API_KEY")
	if not gemini_api_key:
		raise ValueError("GEMINI_API or GEMINI_API_KEY not set in .env")

	database_url = os.getenv("DATABASE_URL")
	if not database_url:
		raise ValueError("DATABASE_URL not set in .env")

	# Minimal host fix for local runs
	database_url = database_url.replace("@db:", "@localhost:")

	gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")
	print(f"[Vanna Flask] DATABASE_URL= {database_url}")

	vn = MyVanna(api_key=gemini_api_key, model=gemini_model)

	engine = create_engine(database_url)

	# Attach run_sql so UI can execute queries
	def run_sql(sql: str):
		with engine.connect() as conn:
			return pd.read_sql_query(sql, conn)

	vn.run_sql = run_sql
	vn.run_sql_is_set = True

	# ----- Auto-select Uber table, create normalized view, and train context -----
	with engine.begin() as conn:
		preferred = os.getenv("DATA_TABLE")
		available = {r[0] for r in conn.execute(text(
			"""
			SELECT table_name
			FROM information_schema.tables
			WHERE table_schema='public' AND table_type='BASE TABLE'
			"""
		)).fetchall()}
		if preferred and preferred in available:
			target_table = preferred
		elif "ncr_ride_bookings" in available:
			target_table = "ncr_ride_bookings"
		elif "uber_rides" in available:
			target_table = "uber_rides"
		else:
			matches = [t for t in available if ("uber" in t.lower() or "ride" in t.lower())]
			target_table = matches[0] if matches else None

		if target_table:
			cols = conn.execute(text(
				"""
				SELECT column_name
				FROM information_schema.columns
				WHERE table_schema='public' AND table_name=:t
				ORDER BY ordinal_position
				"""
			), {"t": target_table}).fetchall()

			print(f"[Vanna Flask] Using Uber table: {target_table}")

			import re
			def to_snake_case(name: str) -> str:
				s = name.strip().lower()
				s = re.sub(r"[^a-z0-9]+", "_", s)
				s = re.sub(r"_+", "_", s).strip("_")
				return s or "col"

			select_list = []
			for (col_name,) in cols:
				select_list.append(f'"{col_name}" AS {to_snake_case(col_name)}')

			view_sql = "CREATE OR REPLACE VIEW uber_bookings AS SELECT " + ", ".join(select_list) + f" FROM {target_table};"
			conn.execute(text(view_sql))
			# Basic counts for verification
			base_count = conn.execute(text(f"SELECT COUNT(*) FROM {target_table}"))
			base_count_val = base_count.scalar() or 0
			view_count = conn.execute(text("SELECT COUNT(*) FROM uber_bookings"))
			view_count_val = view_count.scalar() or 0
			print(f"[Vanna Flask] Row counts -> {target_table}: {base_count_val}, uber_bookings: {view_count_val}")

	# Train DDL for the view and a few examples so the UI prefers Uber data
	with engine.connect() as conn2:
		ddl_cols = conn2.execute(text(
			"""
			SELECT column_name, data_type
			FROM information_schema.columns
			WHERE table_schema='public' AND table_name=:v
			ORDER BY ordinal_position
			"""
		), {"v": "uber_bookings"}).fetchall()

		if ddl_cols:
			mapped_lines = []
			for col_name, data_type in ddl_cols:
				mapped = "text"
				if "double" in data_type or data_type in ("numeric", "real"):
					mapped = "double precision"
				elif data_type in ("integer", "bigint", "smallint"):
					mapped = "integer"
				elif "timestamp" in data_type or data_type == "date":
					mapped = data_type
				mapped_lines.append(f"\t\t{col_name} {mapped}")
			ddl_sql = "CREATE TABLE uber_bookings (\n" + ",\n".join(mapped_lines) + "\n\t)"
			vn.train(ddl=ddl_sql)

			vn.train(documentation=(
				"Uber bookings: Each row is a ride booking with timestamps, status, locations, ride distance, booking value, ratings, and payment method."
			))
			vn.train(question="How many total rides are there?", sql="SELECT COUNT(*) AS total_rides FROM uber_bookings;")
			vn.train(question="How many completed rides by day?", sql=(
				"SELECT date::date AS ride_date, COUNT(*) AS completed_rides "
				"FROM uber_bookings WHERE lower(booking_status) = 'completed' "
				"GROUP BY date::date ORDER BY ride_date;"
			))
			vn.train(question="What is the average ride distance per vehicle type?", sql=(
				"SELECT vehicle_type, AVG(ride_distance) AS avg_distance FROM uber_bookings GROUP BY vehicle_type ORDER BY avg_distance DESC;"
			))
			vn.train(question="Top 10 pickup locations by rides", sql=(
				"SELECT pickup_location, COUNT(*) AS rides FROM uber_bookings GROUP BY pickup_location ORDER BY rides DESC LIMIT 10;"
			))
			vn.train(question="Total booking value (revenue)?", sql=(
				"SELECT SUM(booking_value) AS total_booking_value FROM uber_bookings;"
			))

	return vn, database_url


def build_app():
	vn, _ = create_vanna_with_pg()
	app = VannaFlaskApp(vn=vn, title="Vanna + Uber", subtitle="Ask questions about Uber bookings")
	return app


if __name__ == "__main__":
	app = build_app()
	app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)


