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

	# Ensure the demo table exists and has sample data
	with engine.begin() as conn:
		conn.execute(text("""
			CREATE TABLE IF NOT EXISTS sales (
				sale_id INT PRIMARY KEY,
				product VARCHAR(255),
				quantity INT,
				price_per_unit INT,
				sale_date DATE
			)
		"""))
		# Seed minimal data if empty (last 7 days)
		result = conn.execute(text("SELECT COUNT(*) FROM sales"))
		count = result.scalar() or 0
		if count == 0:
			conn.execute(text("""
				WITH days AS (
					SELECT generate_series(CURRENT_DATE - INTERVAL '6 days', CURRENT_DATE, INTERVAL '1 day')::date AS d
				)
				INSERT INTO sales (sale_id, product, quantity, price_per_unit, sale_date)
				SELECT 
					ROW_NUMBER() OVER () as sale_id,
					CASE WHEN (EXTRACT(DOW FROM d)::int % 2)=0 THEN 'Laptop' ELSE 'Phone' END as product,
					5 as quantity,
					CASE WHEN (EXTRACT(DOW FROM d)::int % 2)=0 THEN 1000 ELSE 600 END as price_per_unit,
					d as sale_date
				FROM days;
			"""))

	def run_sql(sql: str) -> pd.DataFrame:
		with engine.connect() as conn:
			return pd.read_sql_query(sql, conn)

	vn.run_sql = run_sql
	vn.run_sql_is_set = True

	# Minimal training, similar to the initial prompt
	vn.train(ddl="""
		CREATE TABLE sales (
			sale_id INT PRIMARY KEY,
			product VARCHAR(255),
			quantity INT,
			price_per_unit INT,
			sale_date DATE
		)
	""")

	vn.train(documentation=(
		"The sales table contains records of each sale. Total revenue is quantity * price_per_unit."
	))

	vn.train(
		question="What are the total sales for each product?",
		sql="SELECT product, SUM(quantity * price_per_unit) AS total_sales FROM sales GROUP BY product",
	)

	# Teach the model the correct Postgres syntax for last-7-days by day
	vn.train(
		question="What was our total revenue last week, broken down by day?",
		sql=(
			"SELECT sale_date::date AS sale_date, "
			"SUM(quantity * price_per_unit) AS daily_revenue "
			"FROM sales "
			"WHERE sale_date BETWEEN CURRENT_DATE - INTERVAL '7 days' AND CURRENT_DATE "
			"GROUP BY sale_date::date ORDER BY sale_date::date;"
		),
	)

	question = "What was our total revenue last week, broken down by day?"
	print(f"\nAsking: {question}")
	# Get SQL only to avoid any automatic execution
	sql = vn.generate_sql(question)
	df = None

	if sql:
		# Minimal normalization: convert common SQLite date funcs to Postgres
		def normalize_sql_for_postgres(s: str) -> str:
			replacements = [
				("DATE('now', '-7 days')", "CURRENT_DATE - INTERVAL '7 days'"),
				("DATE('now', '-1 day')", "CURRENT_DATE - INTERVAL '1 day'"),
				("DATE('now')", "CURRENT_DATE"),
				("date('now', '-7 days')", "CURRENT_DATE - INTERVAL '7 days'"),
				("date('now', '-1 day')", "CURRENT_DATE - INTERVAL '1 day'"),
				("date('now')", "CURRENT_DATE"),
				("datetime('now')", "NOW()"),
		]
			for old, new in replacements:
				s = s.replace(old, new)
			return s

		sql = normalize_sql_for_postgres(sql)
		print("\nGenerated SQL:\n", sql)
		if df is None:
			try:
				df = vn.run_sql(sql)
			except Exception as e:
				print("\nFailed to run generated SQL:", e)
				return
		print("\nQuery Results:")
		print(df)
	else:
		print("Could not generate a SQL query for the question.")


if __name__ == "__main__":
	main()


