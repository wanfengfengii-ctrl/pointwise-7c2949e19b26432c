import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from fractions import Fraction
from pathlib import Path

from grid.intake import initialize_grid, register_grid
from grid.revisions import RevisionStore
from ledger.catalog import ReportCatalog
from sheet.publish import publish_sheet
from sheet.store import SheetStore, read_sheet
from survey.catalog import SurveyCatalog
from survey.register import open_survey


ACCIDENT_ELEVATIONS = ((2, -1, 2), (-1, 2, 2))
TWO_SHEETS = {'left': (0, 0, 1, 1), 'right': (0, 1, 1, 2)}
ONE_CELL = {'left': (0, 0, 1, 1)}


def point(x, y):
    endpoint = (Fraction(x), Fraction(y))
    return endpoint, endpoint


def span(x0, y0, x1, y1):
    return (Fraction(x0), Fraction(y0)), (Fraction(x1), Fraction(y1))


LEFT_TOP = (0, 0, 0, (point(0, '2/3'), point('1/3', 1)))
LEFT_BOTTOM = (0, 0, 1, (point('2/3', 0), point(1, '1/3')))
RIGHT_BOTTOM = (0, 1, 0, (point(1, '1/3'), point('4/3', 0)))
LEFT_GROUPS = ((LEFT_TOP,), (LEFT_BOTTOM,))
BOTH_GROUPS = ((LEFT_TOP,), (LEFT_BOTTOM, RIGHT_BOTTOM))


def signature(groups):
    return tuple(
        tuple((component.row, component.column, component.part,
               tuple((contact.start, contact.end) for contact in component.contacts))
              for component in group)
        for group in groups
    )


def hand_packet(survey_id, sheet_id, packet_id, coverage, parts, *, scale=1):
    def encode_point(endpoint):
        return [[value.numerator * scale, value.denominator * scale] for value in endpoint]

    return json.dumps({
        'version': 1,
        'survey_id': survey_id,
        'sheet_id': sheet_id,
        'packet_id': packet_id,
        'coverage': coverage,
        'components': [
            {'cell': [row, column], 'part': part, 'contacts': [
                {'start': encode_point(start), 'end': encode_point(end)} for start, end in contacts
            ]}
            for row, column, part, contacts in parts
        ],
    })


def table_count(path, table):
    allowed = {'grid_revisions', 'survey_orders', 'sheet_packets', 'sheet_receipts', 'reports', 'report_receipts'}
    if table not in allowed:
        raise ValueError(f'unknown test table {table!r}')
    with closing(sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)) as connection:
        return connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]


class CommitInterrupted(Exception):
    """Raised at the transaction boundary during a rollback test."""


def interrupt_commit():
    raise CommitInterrupted('interrupted after the paired writes')


class ProjectTestCase(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.source = RevisionStore(self.root / 'source.sqlite')
        self.surveys = SurveyCatalog(self.root / 'surveys.sqlite')
        self.sheets = SheetStore(self.root / 'sheets.sqlite')
        self.reports = ReportCatalog(self.root / 'reports.sqlite')
        initialize_grid(self.source)
        self.surveys.initialize()
        self.sheets.initialize()
        self.reports.initialize()

    def register(self, rows, *, origin=(0, 0), spacing=(1, 1)):
        return register_grid(self.source, 'riverbank', origin, spacing, rows)

    def order(self, rows=ACCIDENT_ELEVATIONS, ranges=TWO_SHEETS, *, level=0, origin=(0, 0), spacing=(1, 1)):
        revision_id = self.register(rows, origin=origin, spacing=spacing)
        return open_survey(self.source, self.surveys, revision_id, level, ranges)

    def publish(self, order, sheet_id):
        issued = publish_sheet(self.source, self.surveys, self.sheets, order.survey_id, sheet_id)
        return issued, read_sheet(self.sheets, issued.packet_id)

    def take_source_offline(self):
        self.source.path.rename(self.root / 'source.offline')
        self.assertFalse(self.source.path.exists())

    def report_counts(self):
        return tuple(table_count(self.reports.path, table) for table in ('reports', 'report_receipts'))

    def sheet_counts(self):
        return tuple(table_count(self.sheets.path, table) for table in ('sheet_packets', 'sheet_receipts'))
