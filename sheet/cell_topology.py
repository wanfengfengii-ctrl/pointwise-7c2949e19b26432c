from fractions import Fraction

from sheet.edge_contacts import BoundaryContact, contact_sort_key, edge_zero_set


_ZERO = Fraction(0)
_ONE = Fraction(1)
_VERTICES = ((_ZERO, _ZERO), (_ONE, _ZERO), (_ZERO, _ONE), (_ONE, _ONE))
_EDGES = ((0, 1), (0, 2), (1, 3), (2, 3))
# Each cell corner paired with the two corners across its incident edges.
_CORNER_NEIGHBORS = ((1, 2), (0, 3), (0, 3), (1, 2))


LocalPieces = tuple[tuple[BoundaryContact, ...], ...]


def _boundary_contacts(values: tuple[Fraction, ...]) -> tuple[BoundaryContact, ...]:
    contacts = set()
    for first, last in _EDGES:
        contact = edge_zero_set(_VERTICES[first], _VERTICES[last], values[first], values[last])
        if contact is not None:
            contacts.add(contact)
    spans = tuple(contact for contact in contacts if not contact.is_point)
    distinct = (
        contact for contact in contacts
        if not contact.is_point or not any(span.contains_point(contact.start) for span in spans)
    )
    return tuple(sorted(distinct, key=contact_sort_key))


def _corner_index(contact: BoundaryContact) -> int | None:
    for index, vertex in enumerate(_VERTICES):
        if contact.start == vertex:
            return index
    return None


def _is_isolated_corner(values: tuple[Fraction, ...], corner: int) -> bool:
    # A zero corner whose two edge-neighbor corners share a sign only touches the
    # level set; with opposite signs the contour enters the cell through it.
    first, second = _CORNER_NEIGHBORS[corner]
    return values[first] * values[second] > 0


def _edge_index(contact: BoundaryContact) -> int:
    x, y = contact.start
    if y == _ZERO:
        return 0
    if x == _ZERO:
        return 1
    if x == _ONE:
        return 2
    return 3


def _saddle_pieces(
    values: tuple[Fraction, ...], contacts: list[BoundaryContact],
) -> list[tuple[BoundaryContact, ...]]:
    by_edge = {}
    for contact in contacts:
        by_edge[_edge_index(contact)] = contact
    # The bilinear saddle value is rise / run; its sign picks which diagonal
    # corner pair the two contour branches isolate.
    rise = values[0] * values[3] - values[1] * values[2]
    if rise == 0:
        return [tuple(sorted(contacts, key=contact_sort_key))]
    run = values[0] - values[1] - values[2] + values[3]
    if values[0] * rise * run < 0:
        pairs = ((0, 1), (2, 3))
    else:
        pairs = ((0, 2), (1, 3))
    return [
        tuple(sorted((by_edge[first], by_edge[second]), key=contact_sort_key))
        for first, second in pairs
    ]


def classify_cell(
    corners: tuple[Fraction, Fraction, Fraction, Fraction], level: Fraction,
) -> LocalPieces:
    values = tuple(Fraction(value) - Fraction(level) for value in corners)
    contacts = _boundary_contacts(values)
    if not contacts:
        return ()
    if any(not contact.is_point for contact in contacts):
        return (contacts,)
    pieces = []
    endpoints = []
    for contact in contacts:
        corner = _corner_index(contact)
        if corner is not None and _is_isolated_corner(values, corner):
            pieces.append((contact,))
        else:
            endpoints.append(contact)
    if len(endpoints) == 2:
        pieces.append(tuple(sorted(endpoints, key=contact_sort_key)))
    elif len(endpoints) == 4:
        pieces.extend(_saddle_pieces(values, endpoints))
    elif endpoints:
        raise ValueError('inconsistent cell boundary contacts')
    return tuple(sorted(pieces, key=lambda piece: tuple(map(contact_sort_key, piece))))
