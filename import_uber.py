import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.kaggle_downloader import KaggleDownloader
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

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://mcpuser:mcppass@localhost:5432/mcpdb",
    )

    # Minimal host fix for local run if env was configured for docker host 'db'
    database_url = database_url.replace("@db:", "@localhost:")

    dataset_name = os.getenv(
        "KAGGLE_DATASET", "yashdevladdha/uber-ride-analytics-dashboard"
    )

    print(f"Preparing Kaggle dataset (cached if available): {dataset_name}")
    kd = KaggleDownloader(download_dir="./datasets")
    result = kd.download_dataset(dataset_name)
    if result.get("status") != "success":
        raise RuntimeError(f"Failed to download dataset: {result}")

    csv_paths = result.get("csv_file_paths", [])
    if not csv_paths:
        print("No CSV files found in the dataset.")
        return

    print(f"Found {len(csv_paths)} CSV file(s) in cache at {result.get('download_path')}")

    importer = CSVImporter(database_url=database_url)
    engine = create_engine(database_url)

    created_tables = []
    for csv_path in csv_paths:
        table_name = sanitize_table_name(csv_path)
        print(f"\nImporting: {csv_path} -> table: {table_name}")
        msg = importer.create_table_from_csv(csv_path, table_name)
        print(msg)
        with engine.connect() as conn:
            try:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = count.scalar()
                print(f"Row count in {table_name}: {row_count}")
            except Exception as e:
                print(f"Failed to count rows in {table_name}: {e}")
        created_tables.append(table_name)

    # Suggest one to use
    if created_tables:
        suggested = created_tables[0]
        print(
            "\nSet environment variable DATA_TABLE to target this table in the demo, e.g.:"
        )
        print(f"  DATA_TABLE={suggested}")


if __name__ == "__main__":
    main()


