from fractions import Fraction

from sheet.edge_contacts import BoundaryContact, contact_sort_key, edge_zero_set


_ZERO = Fraction(0)
_ONE = Fraction(1)
_VERTICES = ((_ZERO, _ZERO), (_ONE, _ZERO), (_ZERO, _ONE), (_ONE, _ONE))
_EDGES = ((0, 1), (0, 2), (1, 3), (2, 3))


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


def _perimeter_position(contact: BoundaryContact) -> Fraction:
    x, y = contact.start
    if y == 0:
        return 1 - x
    if x == 0:
        return 1 + y
    if y == 1:
        return 2 + x
    return 4 - y


def classify_cell(
    corners: tuple[Fraction, Fraction, Fraction, Fraction], level: Fraction,
) -> LocalPieces:
    values = tuple(Fraction(value) - Fraction(level) for value in corners)
    contacts = _boundary_contacts(values)
    if not contacts:
        return ()
    if any(not contact.is_point for contact in contacts):
        return (contacts,)

    perimeter = sorted(contacts, key=_perimeter_position)
    pieces = [
        tuple(sorted(perimeter[start:start + 2], key=contact_sort_key))
        for start in range(0, len(perimeter), 2)
    ]
    return tuple(sorted(pieces, key=lambda piece: tuple(map(contact_sort_key, piece))))
