from collections.abc import Callable, Iterable
from dataclasses import dataclass
from uuid import uuid4

from ledger.catalog import ReportCatalog
from ledger.report import encode_report, freeze_report
from ledger.transaction import report_transaction
from sheet.packet import CellComponent


@dataclass(frozen=True)
class IssuedReview:
    report_id: str
    receipt: str


def commit_review(
    catalog: ReportCatalog,
    survey_id: str,
    adopted: Iterable[tuple[str, str]],
    groups: Iterable[Iterable[CellComponent]],
    *,
    before_commit: Callable[[], None] | None = None,
) -> IssuedReview:
    raw = encode_report(freeze_report(survey_id, adopted, groups))
    report_id = uuid4().hex
    receipt = f'review:{report_id}'
    with report_transaction(catalog.path, before_commit=before_commit) as connection:
        catalog.insert_report(connection, report_id, raw)
        catalog.insert_receipt(connection, report_id, receipt)
    return IssuedReview(report_id, receipt)
