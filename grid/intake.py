from grid.geometry import build_geometry
from grid.revisions import GridRevision, RevisionStore
from grid.samples import validate_samples


def initialize_grid(source: RevisionStore) -> None:
    source.initialize()


def register_grid(
    source: RevisionStore,
    grid_id: str,
    origin,
    spacing,
    elevations,
) -> str:
    if not isinstance(grid_id, str) or not grid_id.strip():
        raise ValueError('a nonempty grid identifier is required')
    geometry = build_geometry(origin, spacing)
    samples = validate_samples(elevations)
    return source.append(grid_id, geometry, samples)


def read_grid_revision(source: RevisionStore, revision_id: str) -> GridRevision:
    return source.read(revision_id)
