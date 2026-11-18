import sqlite3
from contextlib import closing
from pathlib import Path


class ReportCatalog:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()

    def initialize(self) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY NOT NULL,
                    payload TEXT NOT NULL
                )
            ''')
            connection.execute('''
                CREATE TABLE IF NOT EXISTS report_receipts (
                    report_id TEXT PRIMARY KEY NOT NULL REFERENCES reports(report_id),
                    receipt TEXT UNIQUE NOT NULL
                )
            ''')

    def insert_report(self, connection: sqlite3.Connection, report_id: str, raw: str) -> None:
        connection.execute('INSERT INTO reports (report_id, payload) VALUES (?, ?)', (report_id, raw))

    def insert_receipt(self, connection: sqlite3.Connection, report_id: str, receipt: str) -> None:
        connection.execute('INSERT INTO report_receipts VALUES (?, ?)', (report_id, receipt))

    def fetch_report(self, report_id: str) -> tuple[str, str]:
        uri = f'{self.path.as_uri()}?mode=ro'
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            row = connection.execute('''
                SELECT p.payload, r.receipt
                FROM reports AS p JOIN report_receipts AS r USING (report_id)
                WHERE p.report_id = ?
            ''', (report_id,)).fetchone()
        if row is None:
            raise LookupError(f'unknown review report: {report_id}')
        return row
