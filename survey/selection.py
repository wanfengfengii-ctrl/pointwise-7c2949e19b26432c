from collections.abc import Iterable

from survey.catalog import SurveyOrder
from survey.layout import CellRange


def select_sheet(order: SurveyOrder, sheet_id: str) -> CellRange:
    if isinstance(sheet_id, str):
        for identifier, area in order.layout.items():
            if identifier == sheet_id:
                return area
    raise ValueError(f'unknown sheet in survey {order.survey_id}: {sheet_id!r}')


def resolve_selected_sheets(
    order: SurveyOrder, sheet_ids: Iterable[str],
) -> tuple[tuple[str, CellRange], ...]:
    if isinstance(sheet_ids, (str, bytes)) or not isinstance(sheet_ids, Iterable):
        raise ValueError('selected sheet IDs must be an iterable of names')
    selected = {}
    for sheet_id in sheet_ids:
        area = select_sheet(order, sheet_id)
        if sheet_id in selected:
            raise ValueError(f'duplicate selected sheet: {sheet_id!r}')
        selected[sheet_id] = area
    if not selected:
        raise ValueError('at least one sheet must be selected')
    return tuple(sorted(selected.items()))
