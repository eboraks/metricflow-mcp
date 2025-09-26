import os
import json
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from flask import request

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

	gemini_model = os.getenv("GEMINI_MODEL") or "gemini-1.5-flash"
	if gemini_model.endswith("-latest"):
		gemini_model = gemini_model.replace("-latest", "")
	print(f"[Vanna Flask] DATABASE_URL= {database_url}")
	print(f"[Vanna Flask] GEMINI_MODEL= {gemini_model}")

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

	# Try to get the underlying Flask app to register routes/handlers
	flask_app = getattr(app, "app", None) or getattr(app, "_app", None)
	try:
		from flask import Flask as _Flask
		if flask_app is None and isinstance(app, _Flask):
			flask_app = app
	except Exception:
		pass

	# Minimal Vega-Lite endpoint: pass ?sql=... to render a simple bar chart
	def vega():
		sql = request.args.get("sql")
		if not sql:
			return "Provide SQL via '?sql=...'.", 400
		try:
			df = vn.run_sql(sql)
		except Exception as e:
			return f"SQL error: {e}", 400
		if df is None or df.empty:
			return "No data returned.", 200

		# Limit rows to keep the page responsive
		df = df.head(1000)
		cols = list(df.columns)
		x_field = cols[0]
		y_field = cols[1] if len(cols) > 1 else cols[0]

		# Decide y encoding: numeric -> quantitative, else aggregate count
		is_y_numeric = False
		try:
			is_y_numeric = pd.api.types.is_numeric_dtype(df[y_field])
		except Exception:
			is_y_numeric = False

		values = df.to_dict(orient="records")
		spec = {
			"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
			"data": {"values": values},
			"mark": "bar",
			"encoding": {
				"x": {"field": x_field, "type": "nominal"},
				"y": (
					{"field": y_field, "type": "quantitative"}
					if is_y_numeric
					else {"aggregate": "count", "type": "quantitative"}
				)
			}
		}

		html = f"""<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<title>Vega-Lite</title>
<script src=\"https://cdn.jsdelivr.net/npm/vega@5\"></script>
<script src=\"https://cdn.jsdelivr.net/npm/vega-lite@5\"></script>
<script src=\"https://cdn.jsdelivr.net/npm/vega-embed@6\"></script>
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 24px; }}
  #vis {{ max-width: 1000px; }}
  pre {{ white-space: pre-wrap; word-break: break-word; }}
  a {{ color: #0b5fff; }}
</style>
</head>
<body>
<h3>Vega-Lite Chart</h3>
<div style=\"margin-bottom:12px\">SQL: <code>{sql}</code></div>
<div id=\"vis\"></div>
<script>
const spec = {json.dumps(spec, default=str)};
vegaEmbed('#vis', spec).catch(console.error);
</script>
<div style=\"margin-top:16px\"><a href=\"/\">Back to Vanna</a></div>
</body>
</html>"""
		return html

	# Inject an in-page Vega-Lite panel into the main UI without changing templates
	def _inject_vega_panel(resp):
		try:
			ct = resp.headers.get("Content-Type", "")
			if request.path == "/" and "text/html" in ct:
				html = resp.get_data(as_text=True)
				if "VEGA_PANEL_INJECTED" not in html and "</body>" in html:
					injection = """\n<!-- VEGA_PANEL_INJECTED -->\n<div id=\"vega-lite-panel\" style=\"position:fixed; right:16px; bottom:16px; width:520px; max-width:92vw; height:420px; background:#fff; border:1px solid #e3e3e3; box-shadow:0 6px 24px rgba(0,0,0,0.12); border-radius:8px; z-index:9999; display:flex; flex-direction:column;\">\n  <div style=\"display:flex; align-items:center; justify-content:space-between; padding:10px 12px; border-bottom:1px solid #eee; background:#fafafa; border-top-left-radius:8px; border-top-right-radius:8px;\">\n    <div style=\"font-weight:600; font-size:14px;\">Vega-Lite Chart</div>\n    <button id=\"vega-panel-toggle\" style=\"background:none; border:none; cursor:pointer; font-size:13px; color:#0b5fff;\">Hide</button>\n  </div>\n  <div id=\"vega-panel-body\" style=\"display:flex; flex-direction:column; gap:8px; padding:10px 12px;\">\n    <div style=\"font-size:12px; color:#333;\">Enter SQL to visualize (first column on X, second numeric column on Y; otherwise counts):</div>\n    <textarea id=\"vega-sql\" style=\"width:100%; height:80px; font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \u0027Liberation Mono\u0027, \u0027Courier New\u0027, monospace; font-size:12px; padding:8px; border:1px solid #ddd; border-radius:6px;\" placeholder=\"SELECT vehicle_type, COUNT(*) AS rides FROM uber_bookings GROUP BY 1 ORDER BY 2 DESC LIMIT 10\"></textarea>\n    <div style=\"display:flex; gap:8px; align-items:center;\">\n      <button id=\"vega-render\" style=\"background:#0b5fff; color:#fff; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; font-size:12px;\">Render</button>\n      <span id=\"vega-status\" style=\"font-size:12px; color:#666;\"></span>\n    </div>\n    <iframe id=\"vega-frame\" title=\"Vega-Lite\" style=\"flex:1; width:100%; border:1px solid #eee; border-radius:6px; background:#fff;\"></iframe>\n  </div>\n</div>\n<script>\n(function(){\n  const panel = document.getElementById('vega-lite-panel');\n  const body = document.getElementById('vega-panel-body');\n  const toggle = document.getElementById('vega-panel-toggle');\n  const btn = document.getElementById('vega-render');\n  const ta = document.getElementById('vega-sql');\n  const frame = document.getElementById('vega-frame');\n  const status = document.getElementById('vega-status');\n  if (!panel || !btn || !ta || !frame) return;\n  toggle.addEventListener('click', function(){\n    const isHidden = body.style.display === 'none';\n    body.style.display = isHidden ? 'flex' : 'none';\n    toggle.textContent = isHidden ? 'Hide' : 'Show';\n  });\n  btn.addEventListener('click', function(){\n    const sql = encodeURIComponent(ta.value.trim());\n    if (!sql) { status.textContent = 'Enter SQL to render.'; return; }\n    status.textContent = 'Rendering...';\n    frame.src = '/vega?sql=' + sql;\n    frame.onload = function(){ status.textContent = ''; };\n  });\n})();\n</script>\n"""
					html = html.replace("</body>", injection + "</body>")
					resp.set_data(html)
		except Exception:
			pass
		return resp

	# Register handlers if Flask app is available; otherwise skip gracefully
	if flask_app is not None:
		try:
			flask_app.add_url_rule("/vega", "vega", vega)
			safeguard = flask_app.after_request(_inject_vega_panel)  # registers the hook
		except Exception:
			pass
	return app


if __name__ == "__main__":
	app = build_app()
	app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)


