import json
from dataclasses import dataclass

from grid.rationals import from_rational_pair, to_rational_pair
from sheet.edge_contacts import BoundaryContact, Point, contact_sort_key
from survey.layout import CellRange


@dataclass(frozen=True)
class CellComponent:
    row: int
    column: int
    part: int
    contacts: tuple[BoundaryContact, ...]

    @property
    def cell(self) -> tuple[int, int]:
        return self.row, self.column

    @property
    def identity(self) -> tuple[int, int, int]:
        return self.row, self.column, self.part


@dataclass(frozen=True)
class SheetPacket:
    survey_id: str
    sheet_id: str
    packet_id: str
    coverage: CellRange
    components: tuple[CellComponent, ...]


def _fields(value: object, expected: set[str], description: str) -> dict:
    if not isinstance(value, dict) or value.keys() != expected:
        raise ValueError(f'invalid V1 {description} fields')
    return value


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('V1 identity fields must be nonempty text')
    return value


def _decode_point(data: object) -> Point:
    if not isinstance(data, list) or len(data) != 2:
        raise ValueError('a V1 point needs X and Y values')
    return from_rational_pair(data[0]), from_rational_pair(data[1])


def _decode_contact(data: object) -> BoundaryContact:
    fields = _fields(data, {'start', 'end'}, 'contact')
    return BoundaryContact(_decode_point(fields['start']), _decode_point(fields['end']))


def encode_component(component: CellComponent) -> dict:
    return {
        'cell': list(component.cell),
        'part': component.part,
        'contacts': [
            {
                'start': [to_rational_pair(value) for value in contact.start],
                'end': [to_rational_pair(value) for value in contact.end],
            }
            for contact in component.contacts
        ],
    }


def decode_component(data: object) -> CellComponent:
    fields = _fields(data, {'cell', 'part', 'contacts'}, 'component')
    cell = fields['cell']
    part = fields['part']
    if not isinstance(cell, list) or len(cell) != 2:
        raise ValueError('a V1 component needs an original row and column')
    if any(type(index) is not int or index < 0 for index in (*cell, part)):
        raise ValueError('V1 component indices must be nonnegative integers')
    raw_contacts = fields['contacts']
    if not isinstance(raw_contacts, list) or not raw_contacts:
        raise ValueError('a V1 component needs at least one boundary contact')
    contacts = tuple(sorted(map(_decode_contact, raw_contacts), key=contact_sort_key))
    if len(set(contacts)) != len(contacts):
        raise ValueError('duplicate boundary contact in a V1 component')
    return CellComponent(cell[0], cell[1], part, contacts)


def encode_packet(packet: SheetPacket) -> str:
    payload = {
        'version': 1,
        'survey_id': packet.survey_id,
        'sheet_id': packet.sheet_id,
        'packet_id': packet.packet_id,
        'coverage': packet.coverage.coordinates,
        'components': [encode_component(component) for component in packet.components],
    }
    return json.dumps(payload, sort_keys=True, separators=(',', ':'))


def decode_packet(raw: str) -> SheetPacket:
    if not isinstance(raw, str):
        raise ValueError('a V1 packet must be JSON text')
    fields = _fields(
        json.loads(raw),
        {'version', 'survey_id', 'sheet_id', 'packet_id', 'coverage', 'components'},
        'packet',
    )
    if type(fields['version']) is not int or fields['version'] != 1:
        raise ValueError('unsupported packet version')
    coverage = CellRange.from_bounds(fields['coverage'])
    if not isinstance(fields['components'], list):
        raise ValueError('V1 packet components must be a list')
    components = tuple(sorted(map(decode_component, fields['components']), key=lambda item: item.identity))
    identities = set()
    for component in components:
        if not coverage.contains(*component.cell):
            raise ValueError(f'component outside packet coverage: {component.identity}')
        if component.identity in identities:
            raise ValueError(f'duplicate component identity: {component.identity}')
        identities.add(component.identity)
    return SheetPacket(
        _identifier(fields['survey_id']), _identifier(fields['sheet_id']),
        _identifier(fields['packet_id']), coverage, components,
    )
