import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path


@contextmanager
def report_transaction(
    path: Path, *, before_commit: Callable[[], None] | None = None,
) -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            yield connection
            if before_commit is not None:
                before_commit()
