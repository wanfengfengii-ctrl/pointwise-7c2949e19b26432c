from ledger.catalog import ReportCatalog
from ledger.history import read_review
from review.assemble import issue_review
from sheet.publish import publish_sheet
from sheet.store import SheetStore, read_sheet
from tests.fixtures import (
    BOTH_GROUPS, LEFT_GROUPS, CommitInterrupted, ProjectTestCase, interrupt_commit, signature,
)


class TransactionTests(ProjectTestCase):
    def test_commit_failure_preserves_old_results(self):
        order = self.order()
        left, raw_left = self.publish(order, 'left')
        old_sheet_counts = self.sheet_counts()
        with self.assertRaisesRegex(ValueError, 'unknown sheet'):
            publish_sheet(self.source, self.surveys, self.sheets, order.survey_id, 'unknown')
        with self.assertRaises(CommitInterrupted):
            publish_sheet(
                self.source, self.surveys, self.sheets, order.survey_id, 'right',
                before_commit=interrupt_commit,
            )
        sheet_reopen = SheetStore(self.sheets.path)
        sheet_reopen.initialize()
        self.assertEqual(self.sheet_counts(), old_sheet_counts)
        self.assertEqual(read_sheet(sheet_reopen, left.packet_id), raw_left)
        self.assertEqual(sheet_reopen.read_receipt(left.packet_id), left.receipt)

        _, raw_right = self.publish(order, 'right')
        self.take_source_offline()
        first = issue_review(self.surveys, self.reports, order.survey_id, ['left'], [raw_left])
        original = read_review(self.reports, first.report_id)
        self.assertEqual(signature(original.report.groups), LEFT_GROUPS)
        old_report_counts = self.report_counts()
        with self.assertRaises(CommitInterrupted):
            issue_review(
                self.surveys, self.reports, order.survey_id, ['left', 'right'], [raw_left, raw_right],
                before_commit=interrupt_commit,
            )
        report_reopen = ReportCatalog(self.reports.path)
        report_reopen.initialize()
        self.assertEqual(self.report_counts(), old_report_counts)
        self.assertEqual(read_review(report_reopen, first.report_id), original)
        self.assertEqual(original.receipt, first.receipt)

        retry = issue_review(self.surveys, report_reopen, order.survey_id, ['right', 'left'], [raw_right, raw_left])
        result = read_review(report_reopen, retry.report_id)
        self.assertEqual(signature(result.report.groups), BOTH_GROUPS)
        self.assertEqual(result.receipt, retry.receipt)
        self.assertEqual(read_review(report_reopen, first.report_id), original)
        self.assertEqual(self.report_counts(), (2, 2))
