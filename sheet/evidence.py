from fractions import Fraction

from grid.geometry import GridGeometry
from grid.samples import SampleMatrix
from sheet.cell_topology import classify_cell
from sheet.edge_contacts import BoundaryContact, Point
from sheet.packet import CellComponent
from survey.layout import CellRange


def _place_piece(
    piece: tuple[BoundaryContact, ...],
    bounds: tuple[Fraction, Fraction, Fraction, Fraction],
) -> tuple[BoundaryContact, ...]:
    left, bottom, right, top = bounds
    width, height = right - left, top - bottom

    def place(point: Point) -> Point:
        x, y = point
        return left + x * width, bottom + y * height

    return tuple(BoundaryContact(place(contact.start), place(contact.end)) for contact in piece)


def build_sheet_evidence(
    samples: SampleMatrix, geometry: GridGeometry, level: Fraction, coverage: CellRange,
) -> tuple[CellComponent, ...]:
    evidence = []
    for row, column in coverage.cells():
        corners = samples.cell_corners(row, column)
        bounds = geometry.cell_bounds(row, column)
        for part, piece in enumerate(classify_cell(corners, level)):
            evidence.append(CellComponent(row, column, part, _place_piece(piece, bounds)))
    return tuple(evidence)
