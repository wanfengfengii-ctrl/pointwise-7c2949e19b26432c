from dataclasses import dataclass

from ledger.catalog import ReportCatalog
from ledger.report import FrozenReport, decode_report


@dataclass(frozen=True)
class ReviewRecord:
    report_id: str
    receipt: str
    report: FrozenReport


def read_review(catalog: ReportCatalog, report_id: str) -> ReviewRecord:
    raw, receipt = catalog.fetch_report(report_id)
    return ReviewRecord(report_id, receipt, decode_report(raw))
