import unittest


def main() -> int:
    suite = unittest.defaultTestLoader.discover('tests', top_level_dir='.')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() and result.testsRun else 1


if __name__ == '__main__':
    raise SystemExit(main())
