import json
from pathlib import Path
from tempfile import TemporaryDirectory

from grid.intake import initialize_grid, read_grid_revision, register_grid
from grid.revisions import RevisionStore
from ledger.catalog import ReportCatalog
from ledger.history import read_review
from review.assemble import issue_review
from sheet.publish import publish_sheet
from sheet.store import SheetStore, read_sheet
from survey.catalog import SurveyCatalog
from survey.register import open_survey


def report_signature(report):
    return [
        [
            [component.row, component.column, component.part,
             [[str(value) for point in (contact.start, contact.end) for value in point]
              for contact in component.contacts]]
            for component in group
        ]
        for group in report.groups
    ]


def run(root: Path, sample: dict, expected: dict) -> None:
    source = RevisionStore(root / 'source.sqlite')
    surveys = SurveyCatalog(root / 'surveys.sqlite')
    sheets = SheetStore(root / 'sheets.sqlite')
    reports = ReportCatalog(root / 'reports.sqlite')
    initialize_grid(source)
    surveys.initialize()
    sheets.initialize()
    reports.initialize()

    def register(elevations):
        return register_grid(source, sample['grid_id'], sample['origin'], sample['spacing'], elevations)

    revision_id = register(sample['elevations'])
    order = open_survey(source, surveys, revision_id, sample['level'], sample['sheets'])
    left = publish_sheet(source, surveys, sheets, order.survey_id, 'left')
    right = publish_sheet(source, surveys, sheets, order.survey_id, 'right')
    raw_left = read_sheet(sheets, left.packet_id)
    raw_right = read_sheet(sheets, right.packet_id)
    if (sheets.read_receipt(left.packet_id), sheets.read_receipt(right.packet_id)) != (left.receipt, right.receipt):
        raise RuntimeError('sheet receipts differ from the issued receipts')

    corrected = register(sample['correction'])
    initialize_grid(source)
    surveys.initialize()
    old_sample = read_grid_revision(source, order.revision_id).samples.rows[0][0]
    updated_sample = read_grid_revision(source, corrected).samples.rows[0][0]
    if (old_sample, updated_sample) != (2, 3) or surveys.read(order.survey_id) != order:
        raise RuntimeError('fixed survey lost its original revision')
    source.path.rename(root / 'source.offline')

    offline_surveys = SurveyCatalog(surveys.path)
    left_issue = issue_review(offline_surveys, reports, order.survey_id, ['left'], [raw_left])
    both_issue = issue_review(offline_surveys, reports, order.survey_id, ['right', 'left'], [raw_right, raw_left])
    offline_reports = ReportCatalog(reports.path)
    offline_reports.initialize()
    left_record = read_review(offline_reports, left_issue.report_id)
    both_record = read_review(offline_reports, both_issue.report_id)
    actual = {'left': report_signature(left_record.report), 'both': report_signature(both_record.report)}
    if actual != expected:
        raise RuntimeError(f'CONTOUR_HANDOFF_MISMATCH expected={expected!r} actual={actual!r}')
    records = ((left_issue, left_record, (('left', left.packet_id),)),
               (both_issue, both_record, (('left', left.packet_id), ('right', right.packet_id))))
    for issued, record, adopted in records:
        if (record.report_id, record.receipt, record.report.adopted) != (issued.report_id, issued.receipt, adopted):
            raise RuntimeError('reopened report differs from its issued identity or selection')

    downstream = {
        'source_present': source.path.exists(),
        'left_adopted': [name for name, _ in left_record.report.adopted],
        'both_adopted': [name for name, _ in both_record.report.adopted],
        'both_group_cell_counts': [len({member.cell for member in group}) for group in both_record.report.groups],
    }
    downstream_expected = {
        'source_present': False, 'left_adopted': ['left'], 'both_adopted': ['left', 'right'],
        'both_group_cell_counts': [1, 2],
    }
    if downstream != downstream_expected:
        raise RuntimeError(f'offline handover mismatch: {downstream!r}')
    print('Reopened both fixed reviews with the source library offline.')
    print('POINTWISE_SCENARIO ' + json.dumps({
        'case_id': 'v5',
        'input': sample,
        'expected': expected,
        'actual': actual,
        'downstream_expected': downstream_expected,
        'downstream_actual': downstream,
        'code_paths': ['sheet/cell_topology.py', 'sheet/evidence.py', 'sheet/publish.py',
                       'review/contacts.py', 'review/assemble.py', 'ledger/history.py'],
        'oracle': 'Independent hand calculation of four edge roots in the left cell, their branch pairs, and the shared 1/3 contact with the right cell.',
    }, sort_keys=True))


def main() -> None:
    samples = Path(__file__).resolve().parent / 'samples'
    sample = json.loads((samples / 'riverbank.json').read_text(encoding='utf-8'))
    expected = json.loads((samples / 'riverbank_expected.json').read_text(encoding='utf-8'))
    with TemporaryDirectory(prefix='cheng-an-handover-') as directory:
        run(Path(directory), sample, expected)


if __name__ == '__main__':
    main()
