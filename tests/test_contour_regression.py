from fractions import Fraction

from ledger.history import read_review
from review.assemble import issue_review
from sheet.packet import decode_packet
from tests.fixtures import ONE_CELL, ProjectTestCase, point, signature


class ContourTopologyTests(ProjectTestCase):
    def _cell_signature(self, corners):
        level = Fraction(5, 7)
        rows = tuple(tuple(value + level for value in row) for row in corners)
        order = self.order(rows, ONE_CELL, level=level)
        _, raw = self.publish(order, 'left')
        return signature((decode_packet(raw).components,))[0]

    def test_corner_touch_branches(self):
        cases = (
            ('entering corner joins its arc', ((0, 1), (-1, 2)),
             ((0, 0, 0, (point(0, 0), point('1/3', 1))),)),
            ('two isolated corners stay apart', ((0, -1), (-1, 0)),
             ((0, 0, 0, (point(0, 0),)), (0, 0, 1, (point(1, 1),)))),
            ('diagonal corners join through the cell', ((0, 1), (-1, 0)),
             ((0, 0, 0, (point(0, 0), point(1, 1))),)),
        )
        for label, corners, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(self._cell_signature(corners), expected)

    def test_asymmetric_saddles(self):
        cases = (
            ('rise and run agree', ((3, -1), (-2, 5)), (
                (0, 0, 0, (point(0, '3/5'), point('2/7', 1))),
                (0, 0, 1, (point('3/4', 0), point(1, '1/6'))),
            )),
            ('rise and run disagree', ((2, -1), (-3, 1)), (
                (0, 0, 0, (point(0, '2/5'), point('2/3', 0))),
                (0, 0, 1, (point('3/4', 1), point(1, '1/2'))),
            )),
        )
        for label, corners, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(self._cell_signature(corners), expected)

    def test_zero_saddle_hub_groups_all_neighbors(self):
        rows = (
            (2, 2, 2, 2),
            (2, 1, -1, 2),
            (2, -1, 1, 2),
            (2, 2, 2, 2),
        )
        ranges = {
            'south': (0, 1, 1, 2), 'west': (1, 0, 2, 1), 'center': (1, 1, 2, 2),
            'east': (1, 2, 2, 3), 'north': (2, 1, 3, 2),
        }
        order = self.order(rows, ranges)
        packets = {sheet_id: self.publish(order, sheet_id)[1] for sheet_id in ranges}
        self.take_source_offline()
        expected = ((
            (0, 1, 0, (point('3/2', 1), point(2, '2/3'))),
            (1, 0, 0, (point('2/3', 2), point(1, '3/2'))),
            (1, 1, 0, (point(1, '3/2'), point('3/2', 1), point('3/2', 2), point(2, '3/2'))),
            (1, 2, 0, (point(2, '3/2'), point('7/3', 1))),
            (2, 1, 0, (point(1, '7/3'), point('3/2', 2))),
        ),)
        names = tuple(ranges)
        issued = issue_review(
            self.surveys, self.reports, order.survey_id, names, [packets[name] for name in names],
        )
        report = read_review(self.reports, issued.report_id).report
        self.assertEqual(signature(report.groups), expected)
        reversed_names = tuple(reversed(names))
        reversed_issued = issue_review(
            self.surveys, self.reports, order.survey_id,
            reversed_names, [packets[name] for name in reversed_names],
        )
        self.assertEqual(read_review(self.reports, reversed_issued.report_id).report, report)
