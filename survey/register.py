from collections.abc import Mapping

from grid.intake import read_grid_revision
from grid.rationals import RationalInput, parse_rational
from grid.revisions import RevisionStore
from survey.catalog import SurveyCatalog, SurveyOrder
from survey.layout import CellRange, validate_layout


def open_survey(
    source: RevisionStore,
    surveys: SurveyCatalog,
    revision_id: str,
    level: RationalInput,
    ranges: Mapping[str, CellRange | tuple[int, int, int, int]],
) -> SurveyOrder:
    revision = read_grid_revision(source, revision_id)
    exact_level = parse_rational(level)
    cell_shape = revision.samples.cell_shape
    layout = validate_layout(ranges, cell_shape)
    return surveys.add(revision_id, exact_level, revision.geometry, cell_shape, layout)
