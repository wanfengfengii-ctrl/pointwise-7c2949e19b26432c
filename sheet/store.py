import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from sheet.packet import SheetPacket, decode_packet, encode_packet


@dataclass(frozen=True)
class IssuedSheet:
    packet_id: str
    receipt: str


class SheetStore:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()

    def initialize(self) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS sheet_packets (
                    packet_id TEXT PRIMARY KEY NOT NULL,
                    survey_id TEXT NOT NULL,
                    sheet_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            ''')
            connection.execute('''
                CREATE TABLE IF NOT EXISTS sheet_receipts (
                    packet_id TEXT PRIMARY KEY NOT NULL REFERENCES sheet_packets(packet_id),
                    receipt TEXT UNIQUE NOT NULL
                )
            ''')

    def commit_packet(
        self, packet: SheetPacket, *, before_commit: Callable[[], None] | None = None,
    ) -> IssuedSheet:
        raw = encode_packet(packet)
        decode_packet(raw)
        receipt = f'sheet:{packet.packet_id}'
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute('PRAGMA foreign_keys = ON')
            with connection:
                connection.execute(
                    'INSERT INTO sheet_packets VALUES (?, ?, ?, ?)',
                    (packet.packet_id, packet.survey_id, packet.sheet_id, raw),
                )
                connection.execute('INSERT INTO sheet_receipts VALUES (?, ?)', (packet.packet_id, receipt))
                if before_commit is not None:
                    before_commit()
        return IssuedSheet(packet.packet_id, receipt)

    def _read_issued(self, packet_id: str) -> tuple[str, str]:
        uri = f'{self.path.as_uri()}?mode=ro'
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            row = connection.execute('''
                SELECT p.payload, r.receipt
                FROM sheet_packets AS p JOIN sheet_receipts AS r USING (packet_id)
                WHERE p.packet_id = ?
            ''', (packet_id,)).fetchone()
        if row is None:
            raise LookupError(f'unknown sheet packet: {packet_id}')
        return row

    def read_packet(self, packet_id: str) -> str:
        return self._read_issued(packet_id)[0]

    def read_receipt(self, packet_id: str) -> str:
        return self._read_issued(packet_id)[1]


def read_sheet(store: SheetStore, packet_id: str) -> str:
    return store.read_packet(packet_id)
