from collections.abc import Iterable, Sequence

from sheet.edge_contacts import contact_sort_key
from sheet.packet import CellComponent


Group = tuple[CellComponent, ...]


def _component_key(component: CellComponent) -> tuple:
    return component.row, component.column, tuple(map(contact_sort_key, component.contacts)), component.part


def group_sort_key(group: Group) -> tuple:
    return tuple(map(_component_key, group))


def build_groups(
    components: Sequence[CellComponent], links: Iterable[tuple[int, int]],
) -> tuple[Group, ...]:
    adjacency = [[] for _ in components]
    for left, right in links:
        adjacency[left].append(right)
        adjacency[right].append(left)

    visited = set()
    groups = []
    for start in range(len(components)):
        if start in visited:
            continue
        pending = [start]
        visited.add(start)
        members = []
        while pending:
            current = pending.pop()
            members.append(components[current])
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        groups.append(tuple(sorted(members, key=_component_key)))
    return tuple(sorted(groups, key=group_sort_key))
