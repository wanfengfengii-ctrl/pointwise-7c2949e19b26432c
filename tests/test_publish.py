from fractions import Fraction

from sheet.packet import decode_packet, encode_packet
from sheet.store import read_sheet
from survey.register import open_survey
from tests.fixtures import LEFT_BOTTOM, LEFT_TOP, ONE_CELL, ProjectTestCase, point, signature, span


class PublishTests(ProjectTestCase):
    def test_cell_contact_groups(self):
        cases = (
            ('positive saddle', (2, -1, -1, 2), (LEFT_TOP[3], LEFT_BOTTOM[3])),
            ('negative saddle', (1, -2, -2, 1), (
                (point(0, '1/3'), point('1/3', 0)), (point('2/3', 1), point(1, '2/3')),
            )),
            ('zero saddle', (1, -1, -1, 1), (
                (point(0, '1/2'), point('1/2', 0), point('1/2', 1), point(1, '1/2')),
            )),
            ('whole edge and branch', (0, 0, -1, 1), ((span(0, 0, 1, 0), point('1/2', 1)),)),
            ('all zero', (0, 0, 0, 0), ((
                span(0, 0, 0, 1), span(0, 0, 1, 0), span(0, 1, 1, 1), span(1, 0, 1, 1),
            ),)),
            ('isolated corner', (0, 1, 1, 1), ((point(0, 0),),)),
            ('isolated corner and arc', (0, 1, 1, -1), (
                (point(0, 0),), (point('1/2', 1), point(1, '1/2')),
            )),
            ('empty', (1, 2, 3, 4), ()),
        )
        for label, corners, contacts in cases:
            with self.subTest(case=label):
                level = Fraction(5, 7)
                lower_left, lower_right, upper_left, upper_right = [value + level for value in corners]
                order = self.order(((lower_left, lower_right), (upper_left, upper_right)), ONE_CELL, level=level)
                _, raw = self.publish(order, 'left')
                packet = decode_packet(raw)
                expected = tuple((0, 0, part, piece) for part, piece in enumerate(contacts))
                self.assertEqual(signature((packet.components,))[0], expected)

    def test_pinned_publish(self):
        original = self.order(((2, -1), (-1, 2)), ONE_CELL)
        corrected = self.register(((4, 4), (4, 4)))
        updated = open_survey(self.source, self.surveys, corrected, 0, ONE_CELL)
        _, old_raw = self.publish(original, 'left')
        _, new_raw = self.publish(updated, 'left')
        self.assertEqual(signature((decode_packet(old_raw).components,))[0], (LEFT_TOP, LEFT_BOTTOM))
        self.assertEqual(decode_packet(new_raw).components, ())

    def test_packet_roundtrip(self):
        order = self.order(origin=('1/2', '-3/2'), spacing=('3/2', '9/4'))
        issued, raw = self.publish(order, 'left')
        packet = decode_packet(raw)
        self.assertEqual(packet.packet_id, issued.packet_id)
        self.assertEqual(packet.survey_id, order.survey_id)
        self.assertEqual(packet.sheet_id, 'left')
        self.assertEqual(packet.coverage.coordinates, (0, 0, 1, 1))
        expected = (
            (0, 0, 0, (point('1/2', 0), point(1, '3/4'))),
            (0, 0, 1, (point('3/2', '-3/2'), point(2, '-3/4'))),
        )
        self.assertEqual(signature((packet.components,))[0], expected)
        self.assertEqual(encode_packet(packet), raw)
        self.assertEqual(self.sheets.read_receipt(issued.packet_id), issued.receipt)
        self.assertEqual(self.sheet_counts(), (1, 1))
        with self.assertRaises(LookupError):
            read_sheet(self.sheets, 'unknown-packet')
