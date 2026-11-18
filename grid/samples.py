from dataclasses import dataclass
from fractions import Fraction

from grid.rationals import parse_rational


Corners = tuple[Fraction, Fraction, Fraction, Fraction]


@dataclass(frozen=True)
class SampleMatrix:
    rows: tuple[tuple[Fraction, ...], ...]

    @property
    def cell_shape(self) -> tuple[int, int]:
        return len(self.rows) - 1, len(self.rows[0]) - 1

    def cell_corners(self, row: int, column: int) -> Corners:
        height, width = self.cell_shape
        if not (0 <= row < height and 0 <= column < width):
            raise IndexError(f'cell outside the sample matrix: {(row, column)}')
        lower, upper = self.rows[row:row + 2]
        return lower[column], lower[column + 1], upper[column], upper[column + 1]


def validate_samples(elevations: object) -> SampleMatrix:
    if not isinstance(elevations, (list, tuple)) or len(elevations) < 2:
        raise ValueError('at least two rows of elevations are required')
    first = elevations[0]
    if not isinstance(first, (list, tuple)) or len(first) < 2:
        raise ValueError('at least two columns of elevations are required')
    width = len(first)
    rows = []
    for row_index, row in enumerate(elevations):
        if not isinstance(row, (list, tuple)) or len(row) != width:
            raise ValueError(f'elevation row {row_index} must have {width} samples')
        samples = []
        for column, value in enumerate(row):
            try:
                samples.append(parse_rational(value))
            except ValueError as error:
                raise ValueError(f'invalid elevation at {(row_index, column)}') from error
        rows.append(tuple(samples))
    return SampleMatrix(tuple(rows))
