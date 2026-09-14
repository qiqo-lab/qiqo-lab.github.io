"""Regression checks for duplicate projects and incomplete source scans."""
import unittest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
import weekly_content_update as scan


def response(text):
    return Mock(text=text, url='https://www.it.pt/Members/Index/34614')


class WeeklyScanTests(unittest.TestCase):
    def setUp(self):
        scan.SOURCE_WARNINGS.clear()

    def test_append_to_supplementary_publications_push(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'members.js'
            path.write_text('window.QIQO_DATA.publications.push(\n{title:"Old"}\n);\n')
            scan.append_objects(path,[{'title':'New'}])
            self.assertIn('"New"',path.read_text())
            subprocess.run(['node','--check',str(path)],check=True,capture_output=True)

    def test_project_with_existing_acronym_and_new_url_is_not_added(self):
        index = response('<a href="/Projects/Index/4927">ComSense</a>')
        project = response('<h1>ComSense</h1><p>PROJECT: Sensors ACRONYM: ComSense MAIN OBJECTIVE: Test Reference: X Start Date: 01-10-2024 End Date: 01-09-2027</p>')
        with patch.object(scan, 'existing_project_acronyms', return_value={'comsense'}), patch.object(scan.requests, 'get', side_effect=[index, project]):
            self.assertEqual(scan.discover_projects(set()), [])

    def test_crossref_failure_is_reported_for_each_orcid(self):
        with patch.object(scan.requests, 'get', side_effect=RuntimeError('unavailable')):
            self.assertEqual(scan.discover_crossref(set()), [])
        self.assertEqual(len(scan.SOURCE_WARNINGS), len(scan.ORCIDS))
        self.assertTrue(all('unavailable' in w for w in scan.SOURCE_WARNINGS))

    def test_undated_news_is_not_given_todays_date(self):
        with patch.object(scan.requests, 'get', return_value=response('<h1>Quantum news</h1><p>No date.</p>')):
            self.assertIsNone(scan.news_candidate('https://example.org/news'))
        self.assertIn('No verifiable news date', scan.SOURCE_WARNINGS[0])


if __name__ == '__main__':
    unittest.main()
