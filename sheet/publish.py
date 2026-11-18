from collections.abc import Callable
from uuid import uuid4

from grid.intake import read_grid_revision
from grid.revisions import RevisionStore
from sheet.evidence import build_sheet_evidence
from sheet.packet import SheetPacket
from sheet.store import IssuedSheet, SheetStore
from survey.catalog import SurveyCatalog
from survey.selection import select_sheet


def publish_sheet(
    source: RevisionStore,
    surveys: SurveyCatalog,
    sheets: SheetStore,
    survey_id: str,
    sheet_id: str,
    *,
    before_commit: Callable[[], None] | None = None,
) -> IssuedSheet:
    order = surveys.read(survey_id)
    coverage = select_sheet(order, sheet_id)
    revision = read_grid_revision(source, order.revision_id)
    evidence = build_sheet_evidence(revision.samples, order.geometry, order.level, coverage)
    packet = SheetPacket(order.survey_id, sheet_id, uuid4().hex, coverage, evidence)
    return sheets.commit_packet(packet, before_commit=before_commit)
