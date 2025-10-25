# foundation/clients/snowflake.py
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas


class SnowflakeClient:
    # ──────────────────────────────────────────────────────────────────────────
    # Connection helpers
    # ──────────────────────────────────────────────────────────────────────────
    def __init__(self):
        self.connection_params = {
            "user":       os.getenv("SNOWFLAKE_USER"),
            "password":   os.getenv("SNOWFLAKE_PASSWORD"),
            "account":    os.getenv("SNOWFLAKE_ACCOUNT"),
            "warehouse":  os.getenv("SNOWFLAKE_WAREHOUSE"),
            "database":   os.getenv("SNOWFLAKE_DATABASE"),
            "schema":     os.getenv("SNOWFLAKE_SCHEMA"),
            "role":       os.getenv("SNOWFLAKE_ROLE"),
        }

    @contextmanager
    def get_connection(self):
        conn = snowflake.connector.connect(**self.connection_params)
        try:
            yield conn
        finally:
            conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # Generic helpers
    # ──────────────────────────────────────────────────────────────────────────
    def execute_query(self, query: str) -> pd.DataFrame:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                cols = [c[0] for c in cur.description]
                return pd.DataFrame(cur.fetchall(), columns=cols)

    def get_last_etl_count(self, table_name: str) -> int:
        df = self.execute_query(f"SELECT MAX(ETL_COUNT) FROM {table_name}")
        return int(df.iloc[0, 0]) if not df.empty and df.iloc[0, 0] is not None else 0

    # ──────────────────────────────────────────────────────────────────────────
    # CSV loader
    # ──────────────────────────────────────────────────────────────────────────
    def insert_csv_to_snowflake(
        self,
        file_path: str,
        table_name: str,
        column_mapping: Dict[str, str],
        cleanup: bool = True,
    ) -> bool:
        try:
            print(f"► Loading file {file_path} into {table_name}")

            # 1. Read CSV.  Turn the literal 'NULL' (etc.) into pandas NA immediately.
            df = pd.read_csv(
                file_path,
                na_values=["NULL", "null", "NaN", "NAN"],
                keep_default_na=True,
            )
            print(f"   – CSV rows: {len(df)}")

            # 2. Apply column mapping
            df.rename(columns=column_mapping, inplace=True)
            missing = set(column_mapping.values()) - set(df.columns)
            if missing:
                print(f"   ✗ Missing columns after rename: {missing}")
                return False

            # 3. Add ETL metadata
            ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            etl_count = self.get_last_etl_count(table_name) + 1
            df["ETL_DATE"]  = ts_str
            df["ETL_START"] = ts_str
            df["ETL_COUNT"] = etl_count

            # 4. Re-order to mapped cols + metadata
            df = df[list(column_mapping.values()) + ["ETL_DATE", "ETL_START", "ETL_COUNT"]]

            # 5. Ensure NaNs → None (Snowflake NULL).  Cast to object first.
            df = df.astype(object).where(pd.notnull(df), None)

            # 6. Build data tuples with Python None (no NaN)
            data = [
                tuple(None if pd.isna(v) else v for v in row)
                for row in df.itertuples(index=False, name=None)
            ]

            # 7. Run bulk INSERT
            cols         = ", ".join(df.columns)
            placeholders = ", ".join(["%s"] * len(df.columns))
            sql          = f"INSERT INTO {table_name.upper()} ({cols}) VALUES ({placeholders})"

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany(sql, data)
                conn.commit()

            print(f"   ✓ Inserted {len(data)} rows into {table_name}")
            if cleanup:
                self._cleanup_file(file_path)
            return True

        except Exception as exc:
            print("   ✗ Error during insertion:", exc)
            import traceback, sys
            traceback.print_exc(file=sys.stdout)
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # Misc
    # ──────────────────────────────────────────────────────────────────────────
    def _cleanup_file(self, file_path: str):
        try:
            os.remove(file_path)
            print(f"   – Removed local file {file_path}")
        except Exception as exc:
            print(f"   ! Failed to delete {file_path}: {exc}")

    def test_connection(self) -> bool:
        try:
            df = self.execute_query(
                "SELECT CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()"
            )
            print("✓ Snowflake connection OK →", df.iloc[0].tolist())
            return True
        except Exception as exc:
            print("✗ Snowflake connection failed:", exc)
            return False
