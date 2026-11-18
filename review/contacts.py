from collections import defaultdict
from collections.abc import Iterator, Sequence

from sheet.edge_contacts import BoundaryContact, Point
from sheet.packet import CellComponent


_FORWARD_NEIGHBORS = ((0, 1), (1, -1), (1, 0), (1, 1))


def contacts_intersect(left: BoundaryContact, right: BoundaryContact) -> bool:
    return all(
        max(left.start[axis], right.start[axis]) <= min(left.end[axis], right.end[axis])
        for axis in (0, 1)
    )


def _junction_keys(component: CellComponent) -> set[Point]:
    return {
        contact.start for contact in component.contacts
        if all(value.denominator == 1 for value in contact.start)
    }


def iter_contact_links(components: Sequence[CellComponent]) -> Iterator[tuple[int, int]]:
    by_cell = defaultdict(list)
    for index, component in enumerate(components):
        by_cell[component.cell].append((index, _junction_keys(component)))
    for (row, column), entries in by_cell.items():
        for row_offset, col_offset in _FORWARD_NEIGHBORS:
            neighbor = row + row_offset, column + col_offset
            for left, left_keys in entries:
                for right, right_keys in by_cell.get(neighbor, ()):
                    if left_keys & right_keys:
                        yield left, right
