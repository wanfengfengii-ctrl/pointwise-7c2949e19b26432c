from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from grid.geometry import GridGeometry
from review.contacts import contacts_intersect
from sheet.edge_contacts import BoundaryContact
from sheet.packet import CellComponent, SheetPacket, decode_packet
from survey.catalog import SurveyOrder
from survey.selection import resolve_selected_sheets


@dataclass(frozen=True)
class ReviewSelection:
    adopted: tuple[tuple[str, str], ...]
    components: tuple[CellComponent, ...]


def _lies_on_cell_boundary(contact: BoundaryContact, bounds: tuple) -> bool:
    left, bottom, right, top = bounds
    x0, y0 = contact.start
    x1, y1 = contact.end
    if not (left <= x0 <= x1 <= right and bottom <= y0 <= y1 <= top):
        return False
    return x0 == x1 in (left, right) or y0 == y1 in (bottom, top)


def _validate_geometry(packet: SheetPacket, geometry: GridGeometry) -> None:
    earlier_parts = defaultdict(list)
    for component in packet.components:
        bounds = geometry.cell_bounds(*component.cell)
        prior_contacts = earlier_parts[component.cell]
        for contact in component.contacts:
            if not _lies_on_cell_boundary(contact, bounds):
                raise ValueError(f'contact outside cell boundary: {component.identity}')
            if any(contacts_intersect(contact, other) for other in prior_contacts):
                raise ValueError(f'distinct pieces touch inside cell {component.cell}')
        prior_contacts.extend(component.contacts)


def validate_review_selection(
    order: SurveyOrder, sheet_ids: Iterable[str], packets: Iterable[str],
) -> ReviewSelection:
    selected = dict(resolve_selected_sheets(order, sheet_ids))
    if isinstance(packets, (str, bytes)) or not isinstance(packets, Iterable):
        raise ValueError('packets must be an iterable of V1 documents')
    supplied = {}
    packet_ids = set()
    for raw in packets:
        packet = decode_packet(raw)
        if packet.survey_id != order.survey_id:
            raise ValueError(f'packet {packet.packet_id!r} belongs to a different survey')
        if packet.sheet_id not in selected:
            raise ValueError(f'packet supplied for an unselected sheet: {packet.sheet_id!r}')
        if packet.sheet_id in supplied or packet.packet_id in packet_ids:
            raise ValueError(f'duplicate packet for sheet {packet.sheet_id!r}')
        if packet.coverage != selected[packet.sheet_id]:
            raise ValueError(f'packet coverage differs from survey for {packet.sheet_id!r}')
        _validate_geometry(packet, order.geometry)
        supplied[packet.sheet_id] = packet
        packet_ids.add(packet.packet_id)
    missing = selected.keys() - supplied.keys()
    if missing:
        raise ValueError(f'missing selected packets: {sorted(missing)}')
    return ReviewSelection(
        tuple((sheet_id, supplied[sheet_id].packet_id) for sheet_id in selected),
        tuple(component for sheet_id in selected for component in supplied[sheet_id].components),
    )
