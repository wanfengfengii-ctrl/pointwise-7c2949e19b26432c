import json

from ledger.catalog import ReportCatalog
from ledger.history import read_review
from review.assemble import issue_review
from review.contacts import contacts_intersect
from sheet.edge_contacts import BoundaryContact
from sheet.store import SheetStore, read_sheet
from survey.catalog import SurveyCatalog
from survey.register import open_survey
from tests.fixtures import (
    BOTH_GROUPS, LEFT_BOTTOM, LEFT_GROUPS, LEFT_TOP, ONE_CELL, RIGHT_BOTTOM, TWO_SHEETS,
    ProjectTestCase, hand_packet, point, signature, span,
)


class HandoverTests(ProjectTestCase):
    def _review(self, order, selected, packets):
        issued = issue_review(self.surveys, self.reports, order.survey_id, selected, packets)
        readback = read_review(self.reports, issued.report_id)
        self.assertEqual(readback.receipt, issued.receipt)
        self.assertEqual(readback.report.survey_id, order.survey_id)
        return readback

    def test_fractional_seam(self):
        order = self.order()
        left, raw_left = self.publish(order, 'left')
        right, raw_right = self.publish(order, 'right')
        recut = open_survey(self.source, self.surveys, order.revision_id, 0, {'whole': (0, 0, 1, 2)})
        _, raw_whole = self.publish(recut, 'whole')
        self.take_source_offline()
        report = self._review(order, ['left', 'right'], [raw_left, raw_right]).report
        self.assertEqual(signature(report.groups), BOTH_GROUPS, 'CONTOUR_HANDOFF_MISMATCH')
        self.assertEqual(report.adopted, (('left', left.packet_id), ('right', right.packet_id)))
        reversed_report = self._review(order, ['right', 'left'], [raw_right, raw_left]).report
        recut_report = self._review(recut, ['whole'], [raw_whole]).report
        self.assertEqual(reversed_report, report)
        self.assertEqual(recut_report.groups, report.groups)
        self.assertFalse(self.source.path.exists())

    def test_standalone_packets(self):
        order = self.order()
        raw_left = hand_packet(order.survey_id, 'left', 'handoff-left', TWO_SHEETS['left'],
                               (LEFT_BOTTOM, LEFT_TOP), scale=2)
        raw_right = hand_packet(order.survey_id, 'right', 'handoff-right', TWO_SHEETS['right'], (RIGHT_BOTTOM,))
        self.take_source_offline()
        self.assertEqual(self.sheet_counts(), (0, 0))
        report = self._review(order, ['right', 'left'], [raw_right, raw_left]).report
        self.assertEqual(signature(report.groups), BOTH_GROUPS, 'CONTOUR_HANDOFF_MISMATCH')
        self.assertEqual(report.adopted, (('left', 'handoff-left'), ('right', 'handoff-right')))

    def test_transitive_chain(self):
        ranges = {'west': (0, 0, 1, 1), 'middle': (0, 1, 1, 2), 'east': (0, 2, 1, 3)}
        order = self.order(((1, 1, 1, 1), (-2, -2, -2, -2)), ranges)
        packets = {sheet_id: self.publish(order, sheet_id)[1] for sheet_id in ranges}
        self.take_source_offline()
        members = tuple((0, col, 0, (point(col, '1/3'), point(col + 1, '1/3'))) for col in range(3))
        for names in (('west', 'middle', 'east'), ('east', 'west', 'middle')):
            with self.subTest(names=names):
                report = self._review(order, names, [packets[name] for name in names]).report
                self.assertEqual(signature(report.groups), (members,))
        partial = self._review(order, ['east', 'west'], [packets['west'], packets['east']]).report
        self.assertEqual(signature(partial.groups), ((members[0],), (members[2],)))
        self.assertEqual(tuple(name for name, _ in partial.adopted), ('east', 'west'))

    def test_fixed_readback(self):
        order = self.order()
        left, raw_left = self.publish(order, 'left')
        right, raw_right = self.publish(order, 'right')
        self.take_source_offline()
        left_record = self._review(order, ['left'], [raw_left])
        both_record = self._review(order, ['left', 'right'], [raw_left, raw_right])
        self.assertEqual(signature(left_record.report.groups), LEFT_GROUPS)
        self.assertEqual(signature(both_record.report.groups), BOTH_GROUPS)
        self.assertEqual(left_record.report.adopted, (('left', left.packet_id),))
        self.assertEqual(both_record.report.adopted, (('left', left.packet_id), ('right', right.packet_id)))
        self.assertNotEqual(left_record.receipt, both_record.receipt)

        (self.root / 'source.offline').rename(self.source.path)
        self.register(((9, 9, 9), (9, 9, 9)))
        self.take_source_offline()
        reopened_surveys = SurveyCatalog(self.surveys.path)
        reopened_reports = ReportCatalog(self.reports.path)
        reopened_sheets = SheetStore(self.sheets.path)
        reopened_surveys.initialize()
        reopened_reports.initialize()
        reopened_sheets.initialize()
        self.assertEqual(reopened_surveys.read(order.survey_id), order)
        self.assertEqual(read_sheet(reopened_sheets, left.packet_id), raw_left)
        self.assertEqual(read_sheet(reopened_sheets, right.packet_id), raw_right)
        self.assertEqual(read_review(reopened_reports, left_record.report_id), left_record)
        self.assertEqual(read_review(reopened_reports, both_record.report_id), both_record)
        with self.assertRaises(LookupError):
            read_review(reopened_reports, 'unknown-report')
        self.assertEqual(self.report_counts(), (2, 2))
        self.assertFalse(self.source.path.exists())

    def test_reject_incomplete_or_mixed_survey(self):
        order = self.order()
        other = open_survey(self.source, self.surveys, order.revision_id, order.level, TWO_SHEETS)
        _, left = self.publish(order, 'left')
        _, right = self.publish(order, 'right')
        _, foreign_left = self.publish(other, 'left')
        self.take_source_offline()
        cases = (
            (['left', 'right'], [left], 'missing'),
            (['left'], [foreign_left], 'different survey'),
            (['left', 'right'], [left, left, right], 'duplicate'),
            (['left'], [left, right], 'unselected'),
            (['left', 'left'], [left], 'duplicate'),
            ([], [], 'at least one'),
        )
        for names, packets, message in cases:
            with self.subTest(names=names, expected=message):
                with self.assertRaisesRegex(ValueError, message):
                    issue_review(self.surveys, self.reports, order.survey_id, names, packets)
                self.assertEqual(self.report_counts(), (0, 0))

    def test_invalid_evidence(self):
        order = self.order()
        _, left = self.publish(order, 'left')
        self.take_source_offline()

        def change_coverage(data):
            data['coverage'] = [0, 0, 1, 2]

        def change_cell(data):
            data['components'][0]['cell'] = [0, 1]

        def move_contact_inside(data):
            contact = data['components'][0]['contacts'][0]
            contact['start'] = contact['end'] = [[1, 2], [1, 2]]

        def duplicate_part(data):
            data['components'].append(data['components'][0])

        def merge_touching_parts_without_grouping(data):
            data['components'][1]['contacts'][0] = data['components'][0]['contacts'][0]

        def invalid_fraction(data):
            data['components'][0]['contacts'][0]['start'][0] = [0, 0]

        for edit in (change_coverage, change_cell, move_contact_inside, duplicate_part,
                     merge_touching_parts_without_grouping, invalid_fraction):
            with self.subTest(edit=edit.__name__):
                altered = json.loads(left)
                edit(altered)
                with self.assertRaises(ValueError):
                    issue_review(self.surveys, self.reports, order.survey_id, ['left'], [json.dumps(altered)])
                self.assertEqual(self.report_counts(), (0, 0))

    def test_corner_contact_and_empty_level(self):
        ranges = {'first': (0, 0, 1, 1), 'last': (1, 1, 2, 2)}
        rows = ((1, 1, 1), (1, 0, 1), (1, 1, 1))
        corner_order = self.order(rows, ranges)
        empty_order = open_survey(self.source, self.surveys, corner_order.revision_id, 2, ONE_CELL)
        _, first = self.publish(corner_order, 'first')
        _, last = self.publish(corner_order, 'last')
        empty_id, empty = self.publish(empty_order, 'left')
        self.take_source_offline()
        corner_report = self._review(corner_order, ['last', 'first'], [first, last]).report
        expected = (((0, 0, 0, (point(1, 1),)), (1, 1, 0, (point(1, 1),))),)
        self.assertEqual(signature(corner_report.groups), expected)
        empty_report = self._review(empty_order, ['left'], [empty]).report
        self.assertEqual(empty_report.groups, ())
        self.assertEqual(empty_report.adopted, (('left', empty_id.packet_id),))
        self.assertEqual(self.report_counts(), (2, 2))

    def test_whole_edge_and_closed_contacts(self):
        order = self.order(((-1, 1), (0, 0), (1, -1)), {'south': (0, 0, 1, 1), 'north': (1, 0, 2, 1)})
        _, south = self.publish(order, 'south')
        _, north = self.publish(order, 'north')
        self.take_source_offline()
        result = self._review(order, ['north', 'south'], [south, north]).report
        seam = span(0, 1, 1, 1)
        expected = (((0, 0, 0, (seam, point('1/2', 0))), (1, 0, 0, (seam, point('1/2', 2)))),)
        self.assertEqual(signature(result.groups), expected)
        baseline = BoundaryContact(*seam)
        for contact in (point('1/2', 1), point(1, 1), span('1/2', 1, 2, 1), span('1/2', 0, '1/2', 2)):
            self.assertTrue(contacts_intersect(baseline, BoundaryContact(*contact)))
        for contact in (point('3/2', 1), span(0, 2, 1, 2), span('3/2', 1, 2, 1)):
            self.assertFalse(contacts_intersect(baseline, BoundaryContact(*contact)))
