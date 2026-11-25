"""Regression checks for duplicate projects and incomplete source scans."""
import unittest
import datetime as dt
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
import weekly_content_update as scan


def response(text):
    return Mock(text=text, url='https://www.it.pt/Members/Index/34614')


def aps_card(title='Axion magnetohydrodynamics and reconnection-driven axion bursts',
             authors='Hugo Terças', accepted='12 November, 2026', doi='6lkb-18jb'):
    # Card structure inspected on the public PRL accepted listing, 2026-11-25.
    return f'''<div class="content align-start"><section class="headline">
    <h2 class="title"><a href="/prl/accepted/10.1103/{doi}"><span>{title}</span></a></h2>
    </section><section class="citation-container font-normal"><p>{authors}</p>
    <p><span>Accepted {accepted}</span></p></section><section class="summary-container"></section></div>'''


class APSAcceptedTests(unittest.TestCase):
    def setUp(self):
        scan.SOURCE_WARNINGS.clear()
        for name,value in [('TODAY',dt.date(2026,11,25)),('CUTOFF',dt.date(2026,10,11)),
                           ('APS_JOURNALS',{'prl':'Physical Review Letters'})]:
            patcher=patch.object(scan,name,value); patcher.start(); self.addCleanup(patcher.stop)

    def discover(self, pages, existing=None, known_urls=()):
        with patch.object(scan,'existing_urls',return_value=set(known_urls)), \
             patch.object(scan.requests,'get',side_effect=[response(p) for p in pages]) as get:
            result=scan.discover_aps_accepted(set() if existing is None else existing)
        return result,get

    def test_hugo_is_found_after_page_five_and_marked_accepted(self):
        pages=[aps_card(title=f'Unrelated paper {i}',authors='A. Stranger',doi=f'unrelated-{i}')+
               f'<a href="?page={i+1}">»</a>' for i in range(1,6)]
        pages.append(aps_card())
        records,get=self.discover(pages)
        self.assertEqual(len(records),1)
        self.assertEqual(get.call_count,6)
        self.assertEqual(get.call_args.args[0],'https://journals.aps.org/prl/accepted?page=6')
        self.assertEqual(records[0]['url'],'https://doi.org/10.1103/6lkb-18jb')
        self.assertEqual(records[0]['acceptedDate'],'2026-11-12')
        self.assertEqual(records[0]['venue'],'Physical Review Letters (accepted 2026-11-12)')
        self.assertEqual(records[0]['topic'],'Quantum matter')
        self.assertEqual(scan.SOURCE_WARNINGS,[])

    def test_author_matching_accepts_initials_accents_and_full_names(self):
        for author in ['Hugo Terças','H. Terças','E. Zambrini Cruzeiro',
                       'E. Z. Cruzeiro','Gonçalo Teixeira','J. L. Figueiredo',
                       'Other Person, P. Neto Mendes, and A. Stranger']:
            with self.subTest(author=author): self.assertTrue(scan.qiqo_author(author))
        for author in ['Terças','Henry Terças','Hugo Else, X. Terças','A. Cruzeiro']:
            with self.subTest(author=author): self.assertFalse(scan.qiqo_author(author))

    def test_known_title_or_doi_is_not_duplicated(self):
        title='Axion magnetohydrodynamics and reconnection-driven axion bursts'
        self.assertEqual(self.discover([aps_card()],{scan.norm(title)})[0],[])
        self.assertEqual(self.discover([aps_card()],known_urls={
            'https://journals.aps.org/prl/abstract/10.1103/6LKB-18JB'})[0],[])

    def test_window_rejects_old_and_future_acceptances(self):
        page=(aps_card(accepted='10 October, 2026',doi='old')+
              aps_card(accepted='26 November, 2026',doi='future')+
              aps_card(title='Boundary paper',accepted='11 October, 2026',doi='boundary'))
        records,_=self.discover([page])
        self.assertEqual([r['title'] for r in records],['Boundary paper'])

    def test_card_without_date_does_not_borrow_neighbor_metadata(self):
        page=aps_card(title='Missing date',doi='missing').replace('Accepted 12 November, 2026','')+aps_card()
        records,_=self.discover([page])
        self.assertEqual(len(records),1)
        self.assertIn('Could not read',scan.SOURCE_WARNINGS[0])

    def test_blocked_or_changed_page_is_reported(self):
        records,_=self.discover(['<h1>Just a moment...</h1>'])
        self.assertEqual(records,[])
        self.assertIn('layout changed',scan.SOURCE_WARNINGS[0])

    def test_explicit_empty_listing_is_successful(self):
        records,_=self.discover(['<h1>Accepted Papers</h1><p>0 Results</p>'])
        self.assertEqual(records,[])
        self.assertEqual(scan.SOURCE_WARNINGS,[])

    def test_repeated_page_is_reported_and_does_not_loop(self):
        records,get=self.discover([aps_card()+'<a href="?page=2">»</a>',
                                  aps_card()+'<a href="?page=3">»</a>'])
        self.assertEqual(len(records),1)
        self.assertEqual(get.call_count,2)
        self.assertIn('repeated a page',scan.SOURCE_WARNINGS[0])

    def test_source_failure_does_not_stop_other_journals(self):
        with patch.object(scan,'APS_JOURNALS',{'prl':'Physical Review Letters','pra':'Physical Review A'}), \
             patch.object(scan,'existing_urls',return_value=set()), \
             patch.object(scan.requests,'get',side_effect=[RuntimeError('403 Forbidden'),
                 response(aps_card().replace('/prl/','/pra/'))]):
            records=scan.discover_aps_accepted(set())
        self.assertEqual(len(records),1)
        self.assertIn('Physical Review A',records[0]['venue'])
        self.assertIn('403 Forbidden',scan.SOURCE_WARNINGS[0])


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
