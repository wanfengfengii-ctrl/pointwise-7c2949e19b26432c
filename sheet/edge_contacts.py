from dataclasses import dataclass
from fractions import Fraction


Point = tuple[Fraction, Fraction]


@dataclass(frozen=True)
class BoundaryContact:
    start: Point
    end: Point

    def __post_init__(self) -> None:
        if any(
            not isinstance(point, tuple) or len(point) != 2
            or any(type(value) not in (Fraction, int) for value in point)
            for point in (self.start, self.end)
        ):
            raise ValueError('contact endpoints must be exact planar points')
        if self.start > self.end:
            raise ValueError('contact endpoints must be ordered')
        if self.start[0] != self.end[0] and self.start[1] != self.end[1]:
            raise ValueError('a boundary contact must be axis-aligned')

    @property
    def is_point(self) -> bool:
        return self.start == self.end

    def contains_point(self, point: Point) -> bool:
        return all(low <= value <= high for low, value, high in zip(self.start, point, self.end))


def contact_sort_key(contact: BoundaryContact) -> tuple[Point, Point]:
    return contact.start, contact.end


def edge_zero_set(
    start: Point,
    end: Point,
    first_value: Fraction,
    last_value: Fraction,
) -> BoundaryContact | None:
    if first_value == last_value:
        return BoundaryContact(start, end) if first_value == 0 else None
    if first_value * last_value > 0:
        return None
    parameter = Fraction(first_value) / (first_value - last_value)
    x = start[0] + parameter * (end[0] - start[0])
    y = start[1] + parameter * (end[1] - start[1])
    return BoundaryContact((x, y), (x, y))
