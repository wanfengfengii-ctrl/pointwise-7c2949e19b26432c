from collections.abc import Callable, Iterable

from ledger.catalog import ReportCatalog
from ledger.issue import IssuedReview, commit_review
from review.contacts import iter_contact_links
from review.groups import build_groups
from review.selection import validate_review_selection
from survey.catalog import SurveyCatalog


def issue_review(
    surveys: SurveyCatalog,
    reports: ReportCatalog,
    survey_id: str,
    selected_sheet_ids: Iterable[str],
    packets: Iterable[str],
    *,
    before_commit: Callable[[], None] | None = None,
) -> IssuedReview:
    order = surveys.read(survey_id)
    selection = validate_review_selection(order, selected_sheet_ids, packets)
    links = iter_contact_links(selection.components)
    groups = build_groups(selection.components, links)
    return commit_review(
        reports, order.survey_id, selection.adopted, groups, before_commit=before_commit,
    )
