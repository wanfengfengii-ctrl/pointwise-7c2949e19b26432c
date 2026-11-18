from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class CellRange:
    row_start: int
    col_start: int
    row_stop: int
    col_stop: int

    def __post_init__(self) -> None:
        if any(type(value) is not int for value in self.coordinates):
            raise ValueError('cell bounds must be integers')
        if not (0 <= self.row_start < self.row_stop and 0 <= self.col_start < self.col_stop):
            raise ValueError('cell bounds must describe a nonempty rectangle')

    @property
    def coordinates(self) -> tuple[int, int, int, int]:
        return self.row_start, self.col_start, self.row_stop, self.col_stop

    def cells(self) -> Iterator[tuple[int, int]]:
        for row in range(self.row_start, self.row_stop):
            for column in range(self.col_start, self.col_stop):
                yield row, column

    def contains(self, row: int, column: int) -> bool:
        return self.row_start <= row < self.row_stop and self.col_start <= column < self.col_stop

    def overlaps(self, other: 'CellRange') -> bool:
        return (
            max(self.row_start, other.row_start) < min(self.row_stop, other.row_stop)
            and max(self.col_start, other.col_start) < min(self.col_stop, other.col_stop)
        )

    @classmethod
    def from_bounds(cls, bounds: object) -> 'CellRange':
        if not isinstance(bounds, (tuple, list)) or len(bounds) != 4:
            raise ValueError('a cell range needs four bounds')
        return cls(*bounds)


@dataclass(frozen=True)
class SheetLayout:
    entries: tuple[tuple[str, CellRange], ...]

    def items(self) -> Iterator[tuple[str, CellRange]]:
        return iter(self.entries)

    def sheet_ids(self) -> tuple[str, ...]:
        return tuple(sheet_id for sheet_id, _ in self.entries)


def validate_layout(
    ranges: Mapping[str, CellRange | tuple[int, int, int, int]],
    cell_shape: tuple[int, int],
) -> SheetLayout:
    if not isinstance(ranges, Mapping) or not ranges:
        raise ValueError('a survey needs at least one named sheet')
    height, width = cell_shape
    entries = []
    for sheet_id, bounds in ranges.items():
        if not isinstance(sheet_id, str) or not sheet_id.strip():
            raise ValueError('a nonempty sheet identifier is required')
        area = bounds if isinstance(bounds, CellRange) else CellRange.from_bounds(bounds)
        if area.row_stop > height or area.col_stop > width:
            raise ValueError(f'sheet {sheet_id!r} lies outside the surveyed grid')
        entries.append((sheet_id, area))
    for (left_id, left), (right_id, right) in combinations(entries, 2):
        if left.overlaps(right):
            raise ValueError(f'sheets {left_id!r} and {right_id!r} overlap')
    return SheetLayout(tuple(sorted(entries)))
