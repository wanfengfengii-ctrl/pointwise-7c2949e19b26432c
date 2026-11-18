import json
from collections.abc import Iterable
from dataclasses import dataclass

from sheet.packet import CellComponent, decode_component, encode_component


@dataclass(frozen=True)
class FrozenReport:
    survey_id: str
    adopted: tuple[tuple[str, str], ...]
    groups: tuple[tuple[CellComponent, ...], ...]


def freeze_report(
    survey_id: str,
    adopted: Iterable[tuple[str, str]],
    groups: Iterable[Iterable[CellComponent]],
) -> FrozenReport:
    return FrozenReport(survey_id, tuple(sorted(adopted)), tuple(tuple(group) for group in groups))


def encode_report(report: FrozenReport) -> str:
    return json.dumps({
        'survey_id': report.survey_id,
        'adopted': report.adopted,
        'groups': [[encode_component(component) for component in group] for group in report.groups],
    }, separators=(',', ':'), sort_keys=True)


def decode_report(raw: str) -> FrozenReport:
    payload = json.loads(raw)
    return FrozenReport(
        payload['survey_id'],
        tuple((sheet_id, packet_id) for sheet_id, packet_id in payload['adopted']),
        tuple(tuple(map(decode_component, group)) for group in payload['groups']),
    )
