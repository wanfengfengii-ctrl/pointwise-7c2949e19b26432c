import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from grid.geometry import GridGeometry, build_geometry
from grid.rationals import from_rational_pair, to_rational_pair
from grid.samples import SampleMatrix, validate_samples


@dataclass(frozen=True)
class GridRevision:
    revision_id: str
    grid_id: str
    geometry: GridGeometry
    samples: SampleMatrix


def _encode_revision(geometry: GridGeometry, samples: SampleMatrix) -> str:
    return json.dumps({
        'origin': [to_rational_pair(value) for value in geometry.origin],
        'spacing': [to_rational_pair(value) for value in geometry.spacing],
        'elevations': [[to_rational_pair(value) for value in row] for row in samples.rows],
    }, separators=(',', ':'))


def _decode_revision(revision_id: str, grid_id: str, raw: str) -> GridRevision:
    payload = json.loads(raw)
    geometry = build_geometry(
        tuple(map(from_rational_pair, payload['origin'])),
        tuple(map(from_rational_pair, payload['spacing'])),
    )
    rows = [list(map(from_rational_pair, row)) for row in payload['elevations']]
    return GridRevision(revision_id, grid_id, geometry, validate_samples(rows))


class RevisionStore:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()

    def initialize(self) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS grid_revisions (
                    revision_id TEXT PRIMARY KEY NOT NULL,
                    grid_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            ''')

    def append(self, grid_id: str, geometry: GridGeometry, samples: SampleMatrix) -> str:
        revision_id = uuid4().hex
        raw = _encode_revision(geometry, samples)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                'INSERT INTO grid_revisions (revision_id, grid_id, payload) VALUES (?, ?, ?)',
                (revision_id, grid_id, raw),
            )
        return revision_id

    def read(self, revision_id: str) -> GridRevision:
        uri = f'{self.path.as_uri()}?mode=ro'
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            row = connection.execute(
                'SELECT grid_id, payload FROM grid_revisions WHERE revision_id = ?',
                (revision_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f'unknown grid revision: {revision_id}')
        grid_id, raw = row
        return _decode_revision(revision_id, grid_id, raw)
