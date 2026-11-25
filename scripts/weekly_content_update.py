#!/usr/bin/env python3
"""Discover QIQO content candidates and update data files for human review.

This script is intentionally conservative: it only writes candidate content to the
repository. A scheduled GitHub Action opens/refreshes a pull request and never
merges it automatically.
"""
from __future__ import annotations
import argparse, datetime as dt, html, json, re, sys, unicodedata, urllib.parse
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PUBS=ROOT/'assets/js/publications-data.js'
MEMBER_PUBS=ROOT/'assets/js/member-publications-data.js'
NEWS=ROOT/'assets/js/news-data.js'
PROJECTS=ROOT/'assets/js/projects-data.js'
HEADERS={'User-Agent':'QIQO-website-weekly-review/1.0 (+https://github.com/qiqo-lab/qiqo-lab.github.io)'}
TODAY=dt.date.today(); CUTOFF=TODAY-dt.timedelta(days=45)
ARXIV_AUTHORS=['Emmanuel Zambrini Cruzeiro','Hugo Tercas','Preeti Yadav','Flavien Hirsch','Ricardo Faleiro','Pedro Neto Mendes','Goncalo Teixeira','Jose Senart','Jose Luis Figueiredo','Carlo Alfisi']
ORCIDS=['0000-0003-3418-9131','0000-0003-2826-4377','0009-0004-1924-0407','0000-0002-4155-7396']
# Accepted-paper sources relevant to QIQO; media appearances are added manually.
APS_JOURNALS={
    'prl':'Physical Review Letters', 'pra':'Physical Review A',
    'prb':'Physical Review B', 'prd':'Physical Review D', 'pre':'Physical Review E',
    'prresearch':'Physical Review Research', 'prx':'Physical Review X',
    'prxquantum':'PRX Quantum', 'prapplied':'Physical Review Applied',
    'prmaterials':'Physical Review Materials', 'prfluids':'Physical Review Fluids',
}
APS_MAX_PAGES=50
APS_DATE_RE=re.compile(r'\bAccepted\s+(\d{1,2})\s+([A-Za-z]+),?\s+(20\d{2})\b')
APS_MONTHS={m:i for i,m in enumerate(('January','February','March','April','May','June',
    'July','August','September','October','November','December'),1)}
KEYWORDS=['qiqo','qulab','qumatt','motlab','quantum','keyless','qkpc','qkd','iberianqci','qsnp','quantumpuf','cold atom','ultracold','plasmon','axion','faleiro','hirsch','yadav','terças','tercas','cruzeiro']
SOURCE_WARNINGS=[]

def source_warning(source, error):
    SOURCE_WARNINGS.append(f'{source}: {error}')

def existing_project_acronyms():
    return {norm(x) for x in re.findall(r'(?:"?acronym"?)\s*:\s*"([^"]+)"', PROJECTS.read_text(encoding='utf-8'))}

def norm(s): return re.sub(r'\W+',' ',s.lower()).strip()
def existing_titles():
    txt='\n'.join(x.read_text(encoding='utf-8') for x in (PUBS,MEMBER_PUBS))
    return {norm(x) for x in re.findall(r'(?:"?title"?)\s*:\s*"([^"]+)"',txt)}
def existing_urls(path): return set(re.findall(r'(?:"?url"?)\s*:\s*"([^"]+)"',path.read_text(encoding='utf-8')))
def append_objects(path, objs):
    if not objs:return
    txt=path.read_text(encoding='utf-8')
    # The supplementary catalogue uses publications.push(...), not an array assignment.
    terminator=');' if 'window.QIQO_DATA.publications.push(' in txt else '];'
    idx=txt.rfind(terminator)
    if idx<0: raise RuntimeError(f'Cannot find array terminator in {path}')
    before=txt[:idx].rstrip()
    if not before.endswith(('[','(')): before+=','
    payload=',\n'.join(json.dumps(o,ensure_ascii=False,separators=(',',':')) for o in objs)
    path.write_text(before+'\n'+payload+'\n'+txt[idx:],encoding='utf-8')
def classify(title):
    t=title.lower()
    if any(k in t for k in ['bell','nonlocal','contextual','game','steering']): return 'Quantum foundations'
    if any(k in t for k in ['communication','cryptograph','qkd','keyless','network','satellite','free-space']): return 'Quantum communication'
    if any(k in t for k in ['sensor','metrolog','interferomet','thermomet']): return 'Quantum sensing'
    if any(k in t for k in ['plasma','plasmon','condens','spin','axion','semiconductor','moir']): return 'Quantum matter'
    return 'Quantum information'
def clean_title(s): return re.sub(r'\s+',' ',html.unescape(s or '')).strip()

def name_tokens(name):
    folded=''.join(c for c in unicodedata.normalize('NFKD',name) if not unicodedata.combining(c))
    return re.findall(r'[a-z]+',folded.lower())

def qiqo_author(authors):
    # Match complete names or initials within one author, never a surname alone.
    for author in re.split(r',|;|\band\b',authors):
        actual=name_tokens(author)
        for member in ARXIV_AUTHORS:
            expected=name_tokens(member)
            if (len(actual)==len(expected) and actual[-1]==expected[-1]
                    and all(a==e or a==e[0] for a,e in zip(actual[:-1],expected[:-1]))):
                return True
    return False

def aps_doi(url):
    match=re.search(r'10\.1103/[^\s?#"<>]+',urllib.parse.unquote(url),re.I)
    return match.group(0).lower().rstrip('/') if match else None

def parse_aps_listing(page_html, url, journal):
    soup=BeautifulSoup(page_html,'html.parser'); records=[]; seen=set()
    path=urllib.parse.urlparse(url).path.rstrip('/')
    detail_pattern=re.compile(r'^'+re.escape(path)+r'/10\.1103/[^/?#]+$',re.I)
    links=[]
    for anchor in soup.select('h2 a[href], h3 a[href]'):
        target=urllib.parse.urljoin(url,anchor['href']); parsed=urllib.parse.urlparse(target)
        if parsed.netloc=='journals.aps.org' and detail_pattern.match(parsed.path):
            links.append((anchor,target))
    for anchor,target in links:
        doi=aps_doi(target)
        if doi in seen: continue
        seen.add(doi)
        title=clean_title(anchor.get_text(' ',strip=True))
        # Use the smallest card containing this title and its acceptance date.
        # Do not borrow a date/author list from the next card or page footer.
        card=None; match=None
        for parent in anchor.parents:
            contained={a['href'] for a in parent.select('h2 a[href], h3 a[href]')
                       if '/accepted/10.1103/' in a['href']}
            if len(contained)>1: break
            text=clean_title(parent.get_text(' ',strip=True))
            match=APS_DATE_RE.search(text)
            if match:
                card=text; break
        if not card or not title or title not in card:
            source_warning(target,'Could not read accepted-paper metadata; skipped')
            continue
        try:
            accepted=dt.date(int(match[3]),APS_MONTHS[match[2].title()],int(match[1]))
        except (KeyError,ValueError):
            source_warning(target,'Invalid acceptance date; skipped'); continue
        title_end=card.index(title)+len(title)
        authors=clean_title(card[title_end:match.start()])
        if not authors:
            source_warning(target,'Missing accepted-paper authors; skipped'); continue
        records.append({'year':accepted.year,'date':accepted.isoformat(),
            'acceptedDate':accepted.isoformat(),'title':title,'authors':authors,
            'venue':f'{journal} (accepted {accepted.isoformat()})',
            'url':'https://doi.org/'+doi,'topic':classify(title)})
    if not links and not re.search(r'\b0 Results\b|no (?:accepted papers|articles|results)',soup.get_text(' ',strip=True),re.I):
        raise ValueError('No accepted-paper entries or explicit empty result; source may be unavailable or its layout changed')
    current=int(urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get('page',['1'])[0])
    next_url=None
    for anchor in soup.find_all('a',href=True):
        target=urllib.parse.urljoin(url,anchor['href']); parsed=urllib.parse.urlparse(target)
        if parsed.netloc!='journals.aps.org' or parsed.path.rstrip('/')!=path: continue
        if urllib.parse.parse_qs(parsed.query).get('page')==[str(current+1)]:
            next_url=target; break
    return records,next_url

def discover_aps_accepted(existing):
    known_dois={aps_doi(u) for path in (PUBS,MEMBER_PUBS) for u in existing_urls(path)}
    out=[]
    for slug,journal in APS_JOURNALS.items():
        url=f'https://journals.aps.org/{slug}/accepted'; visited=set(); fingerprints=set()
        while url:
            if url in visited or len(visited)>=APS_MAX_PAGES:
                source_warning(journal,'Accepted-paper pagination incomplete; page limit or repeated URL'); break
            visited.add(url)
            try:
                r=requests.get(url,headers=HEADERS,timeout=25); r.raise_for_status()
                records,next_url=parse_aps_listing(r.text,url,journal)
            except Exception as e:
                source_warning(f'APS accepted papers ({journal}) {url}',e); break
            fingerprint=tuple(p['url'] for p in records)
            if fingerprint and fingerprint in fingerprints:
                source_warning(journal,'Accepted-paper pagination repeated a page; scan incomplete'); break
            fingerprints.add(fingerprint)
            for record in records:
                if not CUTOFF.isoformat()<=record['date']<=TODAY.isoformat(): continue
                if not qiqo_author(record['authors']): continue
                doi=aps_doi(record['url'])
                if norm(record['title']) in existing or doi in known_dois: continue
                out.append(record); existing.add(norm(record['title'])); known_dois.add(doi)
            # Follow the listing's own next-page link, including pages beyond the
            # first five. Never interpret a blocked source as a successful empty scan.
            url=next_url
    return out

def discover_arxiv(existing):
    known_ids=set(re.findall(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', '\n'.join(p.read_text(encoding='utf-8') for p in (PUBS,MEMBER_PUBS)), re.I))
    q=' OR '.join(f'au:"{a}"' for a in ARXIV_AUTHORS)
    url='https://export.arxiv.org/api/query?'+urllib.parse.urlencode({'search_query':q,'start':0,'max_results':80,'sortBy':'submittedDate','sortOrder':'descending'})
    r=requests.get(url,headers=HEADERS,timeout=30); r.raise_for_status()
    root=ET.fromstring(r.text); ns={'a':'http://www.w3.org/2005/Atom'}; out=[]
    for e in root.findall('a:entry',ns):
        title=clean_title(e.findtext('a:title','',ns)); published=e.findtext('a:published','',ns)[:10]
        try: d=dt.date.fromisoformat(published)
        except: continue
        if d<CUTOFF or norm(title) in existing: continue
        authors=', '.join(a.findtext('a:name','',ns) for a in e.findall('a:author',ns))
        absurl=e.findtext('a:id','',ns); arxivid=absurl.rsplit('/',1)[-1]
        stable_id=re.sub(r'v\d+$','',arxivid)
        if stable_id in known_ids: continue
        known_ids.add(stable_id)
        out.append({'year':d.year,'date':published,'title':title,'authors':authors,'venue':f'arXiv:{arxivid} (preprint)','url':absurl,'topic':classify(title)})
        existing.add(norm(title))
    return out

def discover_crossref(existing):
    out=[]
    for orcid in ORCIDS:
        params={'filter':f'orcid:{orcid},from-pub-date:{CUTOFF.isoformat()}','rows':30,'select':'DOI,title,author,published-online,published-print,container-title,URL'}
        try:
            r=requests.get('https://api.crossref.org/works',params=params,headers=HEADERS,timeout=25); r.raise_for_status()
            items=r.json()['message']['items']
        except Exception as e:
            source_warning(f'Crossref ORCID {orcid}', e)
            continue
        for it in items:
            title=clean_title((it.get('title') or [''])[0]);
            if not title or norm(title) in existing: continue
            parts=(it.get('published-online') or it.get('published-print') or {}).get('date-parts',[[TODAY.year]])[0]
            year=int(parts[0]); authors=[]
            pubdate=None
            if len(parts)>=3:
                try: pubdate=dt.date(int(parts[0]),int(parts[1]),int(parts[2])).isoformat()
                except (TypeError,ValueError): pass
            for a in it.get('author') or []:
                n=' '.join(x for x in [a.get('given',''),a.get('family','')] if x); authors.append(n)
            doi=it.get('DOI',''); url=('https://doi.org/'+doi) if doi else it.get('URL','')
            venue=((it.get('container-title') or [''])[0] or 'Journal publication')+f' ({year})'
            record={'year':year,'title':title,'authors':', '.join(authors),'venue':venue,'url':url,'topic':classify(title)}
            if pubdate: record['date']=pubdate
            out.append(record)
            existing.add(norm(title))
    return out

def extract_date(text):
    for pat in [r'(20\d\d)-(\d\d)-(\d\d)',r'(\d{1,2})[-/](\d{1,2})[-/](20\d\d)']:
        m=re.search(pat,text)
        if not m: continue
        try:
            if pat.startswith('(20'): return dt.date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
            return dt.date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
        except: pass
    return None

def news_candidate(url):
    r=requests.get(url,headers=HEADERS,timeout=20); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
    title=clean_title((soup.find('h1') or soup.find('h2') or soup.title).get_text(' ',strip=True))
    meta=soup.find('meta',attrs={'name':'description'})
    desc=clean_title(meta.get('content','') if meta else '')
    if not desc:
        p=soup.find('p'); desc=clean_title(p.get_text(' ',strip=True) if p else '')[:360]
    text=clean_title(soup.get_text(' ',strip=True)); d=extract_date(text)
    if d is None:
        source_warning(url, 'No verifiable news date; skipped')
        return None
    return {'date':d.isoformat(),'title':title,'text':desc[:420],'url':url}
def discover_news(existing):
    out=[]; pages=['https://www.it.pt/News','https://www.ipfn.tecnico.ulisboa.pt/news-and-events/news']
    for page in pages:
        try:
            r=requests.get(page,headers=HEADERS,timeout=20);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
        except Exception as e:
            source_warning(page, e)
            continue
        links=[]
        for a in soup.find_all('a',href=True):
            u=urllib.parse.urljoin(page,a['href'])
            if ('/News/NewsPost/' in u or '/News/OtherPost/' in u or '/news-and-events/news/' in u) and u not in links: links.append(u)
        for u in links[:60]:
            if u in existing: continue
            label=clean_title(next((a.get_text(' ',strip=True) for a in soup.find_all('a',href=True) if urllib.parse.urljoin(page,a['href'])==u),''))
            if label and not any(k in label.lower() for k in KEYWORDS): continue
            try: c=news_candidate(u)
            except Exception as e:
                source_warning(u, e)
                continue
            if c is None or not CUTOFF.isoformat() <= c['date'] <= TODAY.isoformat(): continue
            hay=(c['title']+' '+c['text']).lower()
            if any(k in hay for k in KEYWORDS): out.append(c); existing.add(u)
    out.sort(key=lambda x:x['date'],reverse=True); return out

def discover_projects(existing):
    out=[]; acronyms=existing_project_acronyms()
    try:
        r=requests.get('https://www.it.pt/Members/Index/34614',headers=HEADERS,timeout=25);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
    except Exception as e:
        source_warning('IT project index', e)
        return out
    urls=[]
    for a in soup.find_all('a',href=True):
        u=urllib.parse.urljoin(r.url,a['href'])
        if '/Projects/Index/' in u and u not in urls:urls.append(u)
    for u in urls:
        if u in existing:continue
        try:
            rr=requests.get(u,headers=HEADERS,timeout=20);rr.raise_for_status();ss=BeautifulSoup(rr.text,'html.parser'); text=clean_title(ss.get_text(' ',strip=True))
            h=ss.find('h1'); acronym=clean_title(h.get_text(' ',strip=True) if h else '')
            mtitle=re.search(r'PROJECT:\s*(.*?)\s+ACRONYM:',text,re.I); title=mtitle.group(1).strip() if mtitle else acronym
            mac=re.search(r'ACRONYM:\s*(.*?)\s+MAIN OBJECTIVE:',text,re.I); acronym=mac.group(1).strip() if mac else acronym
            if not acronym or norm(acronym) in acronyms: continue
            md=re.search(r'Start Date:\s*(\d{2})-(\d{2})-(\d{4}).*?End Date:\s*(\d{2})-(\d{2})-(\d{4})',text,re.I)
            if not md:continue
            start=f'{md.group(3)}-{md.group(2)}-{md.group(1)}'; end=f'{md.group(6)}-{md.group(5)}-{md.group(4)}'
            mf=re.search(r'Funding:\s*(.*?)\s+Start Date:',text,re.I); funder=(mf.group(1).strip() if mf else 'Official IT project')[:120]
            obj=re.search(r'MAIN OBJECTIVE:\s*(.*?)\s+Reference:',text,re.I); summary=(obj.group(1).strip() if obj else title)[:420]
            out.append({'acronym':acronym,'title':title,'funder':funder,'startDate':start,'endDate':end,'dates':f'{start}–{end}','scope':'QuLab / IT','text':summary,'url':u});existing.add(u);acronyms.add(norm(acronym))
        except Exception as e:source_warning(u, e)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--summary',default='/tmp/qiqo-weekly-summary.md');args=ap.parse_args()
    titles=existing_titles(); news_urls=existing_urls(NEWS); project_urls=existing_urls(PROJECTS)
    SOURCE_WARNINGS.clear(); warnings=SOURCE_WARNINGS
    try: pubs=discover_arxiv(titles)
    except Exception as e: pubs=[];warnings.append(f'arXiv: {e}')
    try: pubs+=discover_crossref(titles)
    except Exception as e:warnings.append(f'Crossref: {e}')
    try: pubs+=discover_aps_accepted(titles)
    except Exception as e:warnings.append(f'APS accepted papers: {e}')
    try: news=discover_news(news_urls)
    except Exception as e: news=[];warnings.append(f'news scan: {e}')
    try: projects=discover_projects(project_urls)
    except Exception as e: projects=[];warnings.append(f'project scan: {e}')
    append_objects(MEMBER_PUBS,pubs); append_objects(NEWS,news); append_objects(PROJECTS,projects)
    lines=['# Weekly QIQO website content review','',f'Checked on {TODAY.isoformat()} (UTC); publication/news window starts {CUTOFF.isoformat()}.','',f'**Candidate changes:** {len(pubs)} publications · {len(news)} news items · {len(projects)} projects','']
    for label,items,key in [('Publications',pubs,'title'),('News',news,'title'),('Projects',projects,'acronym')]:
        if items:
            lines+=['## '+label]+[f'- [{x[key]}]({x["url"]})' for x in items]+['']
    if not pubs and not news and not projects: lines+=['No new candidates were found in the sources successfully checked.','']
    lines+=['## Review action','Merge this PR to publish the candidates. Close it if the candidates are not relevant; nothing is auto-merged. People/student changes remain manual.']
    if warnings: lines+=['','## Source warnings','The check is incomplete for the sources listed below; absence of candidates is not evidence that those sources have no updates.']+[f'- {w}' for w in warnings]
    Path(args.summary).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))
if __name__=='__main__': main()
