from fractions import Fraction

from grid.intake import initialize_grid, read_grid_revision
from grid.revisions import RevisionStore
from survey.catalog import SurveyCatalog
from survey.register import open_survey
from tests.fixtures import ACCIDENT_ELEVATIONS, ONE_CELL, ProjectTestCase, table_count


class PrepareTests(ProjectTestCase):
    def test_survey_pins_revision(self):
        order = self.order(origin=('1/3', '-2/5'), spacing=('5/2', '3/4'))
        corrected = self.register(((7, 0, 6), (5, -2, 4)))
        initialize_grid(self.source)
        self.surveys.initialize()
        pinned = self.surveys.read(order.survey_id)
        self.assertEqual(pinned, order)
        self.assertNotEqual(pinned.revision_id, corrected)
        first = read_grid_revision(self.source, pinned.revision_id)
        second = read_grid_revision(self.source, corrected)
        self.assertEqual(first.samples.rows, ACCIDENT_ELEVATIONS)
        self.assertEqual(second.samples.rows, ((7, 0, 6), (5, -2, 4)))
        self.assertEqual(first.geometry.vertex(1, 1), (Fraction(17, 6), Fraction(7, 20)))
        left = first.samples.cell_corners(0, 0)
        right = first.samples.cell_corners(0, 1)
        self.assertEqual((left[1], left[3]), (right[0], right[2]))

    def test_reopen_keeps_edits(self):
        order = self.order()
        revised_rows = (('7/5', 4), (-3, 0))
        corrected = self.register(revised_rows)
        source = RevisionStore(self.source.path)
        surveys = SurveyCatalog(self.surveys.path)
        initialize_grid(source)
        surveys.initialize()
        self.assertEqual(read_grid_revision(source, corrected).samples.rows,
                         ((Fraction(7, 5), 4), (-3, 0)))
        self.assertEqual(read_grid_revision(source, order.revision_id).samples.rows, ACCIDENT_ELEVATIONS)
        self.assertEqual(surveys.read(order.survey_id), order)
        self.assertEqual(table_count(source.path, 'grid_revisions'), 2)
        self.assertEqual(table_count(surveys.path, 'survey_orders'), 1)

    def test_incomplete_grid(self):
        original = self.register(((3, 4), (2, 7)))
        invalid_grids = (((3, 4), (2,)), ((3, 4), (2, None)), ((3, 4),), [[3], [4]], [])
        for rows in invalid_grids:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.register(rows)
        self.assertEqual(table_count(self.source.path, 'grid_revisions'), 1)
        self.assertEqual(read_grid_revision(self.source, original).samples.rows, ((3, 4), (2, 7)))
        with_zero = self.register(((3, 4), (2, 0)))
        self.assertEqual(read_grid_revision(self.source, with_zero).samples.rows[1][1], 0)

    def test_invalid_geometry(self):
        rows = ((0, 1), (2, 3))
        invalid = (
            ((0,), (1, 1)), ((0, 0), (0, 1)), ((0, 0), (1, -1)),
            ((0, '1/0'), (1, 1)), ((True, 0), (1, 1)), ((0, 0), (1, 0.5)),
        )
        for origin, spacing in invalid:
            with self.subTest(origin=origin, spacing=spacing), self.assertRaises(ValueError):
                self.register(rows, origin=origin, spacing=spacing)
        self.assertEqual(table_count(self.source.path, 'grid_revisions'), 0)

    def test_overlapping_sheets(self):
        revision_id = self.register(((1, 2, 3, 4), (0, 1, 2, 3)))
        layouts = (
            {'west': (0, 0, 1, 2), 'east': (0, 1, 1, 3)},
            {'west': (0, 0, 1, 2), 'east': (0, 0, 1, 2)},
        )
        for ranges in layouts:
            with self.subTest(ranges=ranges), self.assertRaisesRegex(ValueError, 'overlap'):
                open_survey(self.source, self.surveys, revision_id, 0, ranges)
        self.assertEqual(table_count(self.surveys.path, 'survey_orders'), 0)

    def test_nested_overlap(self):
        rows = ((1, 1, 1, 1),) * 4
        with self.assertRaisesRegex(ValueError, 'overlap'):
            self.order(rows, {'outer': (0, 0, 3, 3), 'inner': (1, 1, 2, 2)})
        self.assertEqual(table_count(self.surveys.path, 'survey_orders'), 0)

    def test_bounds_and_shared_edges(self):
        revision_id = self.register(((1, 1, 1, 1),) * 4)
        with self.assertRaises(LookupError):
            open_survey(self.source, self.surveys, 'missing', 0, ONE_CELL)
        for bounds in ((0, 2, 1, 4), (-1, 0, 1, 1), (1, 0, 1, 1), (0, 0, True, 1)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                open_survey(self.source, self.surveys, revision_id, 0, {'bad': bounds})
        with self.assertRaises(ValueError):
            open_survey(self.source, self.surveys, revision_id, '1/0', ONE_CELL)
        self.assertEqual(table_count(self.surveys.path, 'survey_orders'), 0)
        ranges = {'west': (0, 0, 1, 1), 'east': (0, 1, 1, 2), 'far': (1, 2, 2, 3)}
        order = open_survey(self.source, self.surveys, revision_id, '1/3', ranges)
        self.assertEqual(order.layout.sheet_ids(), ('east', 'far', 'west'))
        self.assertEqual(order.level, Fraction(1, 3))
        self.assertEqual(self.surveys.read(order.survey_id), order)
