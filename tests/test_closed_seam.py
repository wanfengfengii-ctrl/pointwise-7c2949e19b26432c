from ledger.history import read_review
from review.assemble import issue_review
from tests.fixtures import ProjectTestCase, point, signature, span


class ClosedSeamTests(ProjectTestCase):
    def test_closed_edge_connects_at_its_last_corner(self):
        rows = ((1, 1, 1), (0, 0, 1), (1, 1, 1))
        ranges = {"southwest": (0, 0, 1, 1), "northeast": (1, 1, 2, 2)}
        order = self.order(rows, ranges)
        _, southwest = self.publish(order, "southwest")
        _, northeast = self.publish(order, "northeast")
        self.take_source_offline()

        issued = issue_review(
            self.surveys, self.reports, order.survey_id,
            ["northeast", "southwest"], [southwest, northeast],
        )
        actual = read_review(self.reports, issued.report_id).report.groups
        expected = (((0, 0, 0, (span(0, 1, 1, 1),)), (1, 1, 0, (point(1, 1),))),)
        self.assertEqual(signature(actual), expected)
