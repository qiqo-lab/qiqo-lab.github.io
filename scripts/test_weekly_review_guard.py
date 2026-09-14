import datetime as dt
import unittest
from weekly_review_guard import merged_review_today

REPO = 'qiqo-lab/qiqo-lab.github.io'
def pr(merged='2026-09-14T08:58:00Z', branch='automation/weekly-content-review', repo=REPO):
    return {'number': 1, 'merged_at': merged, 'head': {'ref': branch, 'repo': {'full_name': repo}}, 'base': {'ref': 'main', 'repo': {'full_name': REPO}}}

class GuardTests(unittest.TestCase):
    now = dt.datetime.fromisoformat('2026-09-14T14:42:00+00:00')
    def test_merged_today_on_later_api_page(self):
        self.assertEqual(merged_review_today([[], [pr()]], REPO, self.now), 1)
    def test_closed_unmerged_does_not_block(self):
        self.assertIsNone(merged_review_today([[pr(None)]], REPO, self.now))
    def test_previous_day_does_not_block(self):
        self.assertIsNone(merged_review_today([[pr('2026-09-13T08:00:00Z')]], REPO, self.now))
    def test_unrelated_branch_or_fork_does_not_block(self):
        self.assertIsNone(merged_review_today([[pr(branch='other'), pr(repo='someone/fork')]], REPO, self.now))
    def test_lisbon_day_crosses_utc_midnight(self):
        self.assertEqual(merged_review_today([[pr('2026-09-13T23:30:00Z')]], REPO, self.now), 1)

if __name__ == '__main__':
    unittest.main()
