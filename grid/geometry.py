from dataclasses import dataclass
from fractions import Fraction

from grid.rationals import RationalInput, parse_rational


@dataclass(frozen=True)
class GridGeometry:
    origin_x: Fraction
    origin_y: Fraction
    step_x: Fraction
    step_y: Fraction

    def vertex(self, row: int, column: int) -> tuple[Fraction, Fraction]:
        return self.origin_x + column * self.step_x, self.origin_y + row * self.step_y

    def cell_bounds(self, row: int, column: int) -> tuple[Fraction, Fraction, Fraction, Fraction]:
        left, bottom = self.vertex(row, column)
        right, top = self.vertex(row + 1, column + 1)
        return left, bottom, right, top

    @property
    def origin(self) -> tuple[Fraction, Fraction]:
        return self.origin_x, self.origin_y

    @property
    def spacing(self) -> tuple[Fraction, Fraction]:
        return self.step_x, self.step_y


def _axis_pair(values: object, name: str) -> tuple[Fraction, Fraction]:
    if not isinstance(values, (list, tuple)) or len(values) != 2:
        raise ValueError(f'{name} must contain X and Y values')
    return parse_rational(values[0]), parse_rational(values[1])


def build_geometry(
    origin: tuple[RationalInput, RationalInput],
    spacing: tuple[RationalInput, RationalInput],
) -> GridGeometry:
    origin_x, origin_y = _axis_pair(origin, 'origin')
    step_x, step_y = _axis_pair(spacing, 'spacing')
    if step_x <= 0 or step_y <= 0:
        raise ValueError('both axis spacings must be positive')
    return GridGeometry(origin_x, origin_y, step_x, step_y)
