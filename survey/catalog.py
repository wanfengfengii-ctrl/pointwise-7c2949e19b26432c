import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from uuid import uuid4

from grid.geometry import GridGeometry, build_geometry
from grid.rationals import from_rational_pair, to_rational_pair
from survey.layout import SheetLayout, validate_layout


@dataclass(frozen=True)
class SurveyOrder:
    survey_id: str
    revision_id: str
    level: Fraction
    geometry: GridGeometry
    cell_shape: tuple[int, int]
    layout: SheetLayout


def _encode_order(order: SurveyOrder) -> str:
    return json.dumps({
        'level': to_rational_pair(order.level),
        'origin': [to_rational_pair(value) for value in order.geometry.origin],
        'spacing': [to_rational_pair(value) for value in order.geometry.spacing],
        'cell_shape': order.cell_shape,
        'ranges': {sheet_id: area.coordinates for sheet_id, area in order.layout.items()},
    }, separators=(',', ':'))


def _decode_order(survey_id: str, revision_id: str, raw: str) -> SurveyOrder:
    data = json.loads(raw)
    geometry = build_geometry(
        tuple(map(from_rational_pair, data['origin'])),
        tuple(map(from_rational_pair, data['spacing'])),
    )
    cell_shape = tuple(data['cell_shape'])
    return SurveyOrder(
        survey_id, revision_id, from_rational_pair(data['level']), geometry,
        cell_shape, validate_layout(data['ranges'], cell_shape),
    )


class SurveyCatalog:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()

    def initialize(self) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS survey_orders (
                    survey_id TEXT PRIMARY KEY NOT NULL,
                    revision_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            ''')

    def add(
        self, revision_id: str, level: Fraction, geometry: GridGeometry,
        cell_shape: tuple[int, int], layout: SheetLayout,
    ) -> SurveyOrder:
        order = SurveyOrder(uuid4().hex, revision_id, level, geometry, cell_shape, layout)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                'INSERT INTO survey_orders (survey_id, revision_id, payload) VALUES (?, ?, ?)',
                (order.survey_id, revision_id, _encode_order(order)),
            )
        return order

    def read(self, survey_id: str) -> SurveyOrder:
        uri = f'{self.path.as_uri()}?mode=ro'
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            row = connection.execute(
                'SELECT revision_id, payload FROM survey_orders WHERE survey_id = ?', (survey_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f'unknown survey: {survey_id}')
        revision_id, raw = row
        return _decode_order(survey_id, revision_id, raw)
