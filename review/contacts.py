from collections import defaultdict
from collections.abc import Iterator, Sequence

from sheet.edge_contacts import BoundaryContact
from sheet.packet import CellComponent


_FORWARD_NEIGHBORS = ((0, 1), (1, -1), (1, 0), (1, 1))


def contacts_intersect(left: BoundaryContact, right: BoundaryContact) -> bool:
    return all(
        max(left.start[axis], right.start[axis]) <= min(left.end[axis], right.end[axis])
        for axis in (0, 1)
    )


def _components_touch(left: CellComponent, right: CellComponent) -> bool:
    return any(
        contacts_intersect(first, second)
        for first in left.contacts
        for second in right.contacts
    )


def iter_contact_links(components: Sequence[CellComponent]) -> Iterator[tuple[int, int]]:
    by_cell = defaultdict(list)
    for index, component in enumerate(components):
        by_cell[component.cell].append(index)
    for (row, column), indices in by_cell.items():
        for row_offset, col_offset in _FORWARD_NEIGHBORS:
            neighbor = row + row_offset, column + col_offset
            for left in indices:
                for right in by_cell.get(neighbor, ()):
                    if _components_touch(components[left], components[right]):
                        yield left, right
