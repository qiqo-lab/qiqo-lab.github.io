#!/usr/bin/env python3
"""Discover QIQO content candidates and update data files for human review.

This script is intentionally conservative: it only writes candidate content to the
repository. A scheduled GitHub Action opens/refreshes a pull request and never
merges it automatically.
"""
from __future__ import annotations
import argparse, datetime as dt, html, json, re, urllib.parse
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
ARXIV_AUTHORS=['Emmanuel Zambrini Cruzeiro','Hugo Tercas','Preeti Yadav','Flavien Hirsch','Ricardo Faleiro','Pedro Neto Mendes','Goncalo Teixeira','Jose Senart','Jose Luis Figueiredo','Carlo Alfisi','Theo Abounnasr Martins']
ORCIDS=['0000-0003-3418-9131','0000-0003-2826-4377','0009-0004-1924-0407','0000-0002-4155-7396']
KEYWORDS=['qiqo','qulab','quantmatt','motlab','quantum','keyless','qkpc','qkd','iberianqci','qsnp','quantumpuf','cold atom','ultracold','plasmon','axion','faleiro','hirsch','yadav','terças','tercas','cruzeiro']

def norm(s): return re.sub(r'\W+',' ',s.lower()).strip()
def existing_titles():
    txt='\n'.join(x.read_text(encoding='utf-8') for x in (PUBS,MEMBER_PUBS))
    return {norm(x) for x in re.findall(r'(?:"?title"?)\s*:\s*"([^"]+)"',txt)}
def existing_urls(path): return set(re.findall(r'(?:"?url"?)\s*:\s*"([^"]+)"',path.read_text(encoding='utf-8')))
def append_objects(path, objs):
    if not objs:return
    txt=path.read_text(encoding='utf-8'); idx=txt.rfind('];')
    if idx<0: raise RuntimeError(f'Cannot find array terminator in {path}')
    before=txt[:idx].rstrip()
    if not before.endswith('['): before+=','
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

def discover_arxiv(existing):
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
        out.append({'year':d.year,'title':title,'authors':authors,'venue':f'arXiv:{arxivid} (preprint)','url':absurl,'topic':classify(title)})
        existing.add(norm(title))
    return out

def discover_crossref(existing):
    out=[]
    for orcid in ORCIDS:
        params={'filter':f'orcid:{orcid},from-pub-date:{CUTOFF.isoformat()}','rows':30,'select':'DOI,title,author,published-online,published-print,container-title,URL'}
        try:
            r=requests.get('https://api.crossref.org/works',params=params,headers=HEADERS,timeout=25); r.raise_for_status()
            items=r.json()['message']['items']
        except Exception: continue
        for it in items:
            title=clean_title((it.get('title') or [''])[0])
            if not title or norm(title) in existing: continue
            parts=(it.get('published-online') or it.get('published-print') or {}).get('date-parts',[[TODAY.year]])[0]
            year=int(parts[0]); authors=[]
            for a in it.get('author') or []:
                n=' '.join(x for x in [a.get('given',''),a.get('family','')] if x); authors.append(n)
            doi=it.get('DOI',''); url=('https://doi.org/'+doi) if doi else it.get('URL','')
            venue=((it.get('container-title') or [''])[0] or 'Journal publication')+f' ({year})'
            out.append({'year':year,'title':title,'authors':', '.join(authors),'venue':venue,'url':url,'topic':classify(title)})
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
    text=clean_title(soup.get_text(' ',strip=True)); d=extract_date(text) or TODAY
    return {'date':d.isoformat(),'title':title,'text':desc[:420],'url':url}
def discover_news(existing):
    out=[]; pages=['https://www.it.pt/News','https://www.ipfn.tecnico.ulisboa.pt/news-and-events/news']
    for page in pages:
        try:
            r=requests.get(page,headers=HEADERS,timeout=20);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
        except Exception: continue
        links=[]
        for a in soup.find_all('a',href=True):
            u=urllib.parse.urljoin(page,a['href'])
            if ('/News/NewsPost/' in u or '/News/OtherPost/' in u or '/news-and-events/news/' in u) and u not in links: links.append(u)
        for u in links[:60]:
            if u in existing: continue
            label=clean_title(next((a.get_text(' ',strip=True) for a in soup.find_all('a',href=True) if urllib.parse.urljoin(page,a['href'])==u),''))
            if label and not any(k in label.lower() for k in KEYWORDS): continue
            try: c=news_candidate(u)
            except Exception: continue
            hay=(c['title']+' '+c['text']).lower()
            if any(k in hay for k in KEYWORDS): out.append(c); existing.add(u)
    out.sort(key=lambda x:x['date'],reverse=True); return out

def discover_projects(existing):
    out=[]
    try:
        r=requests.get('https://www.it.pt/Members/Index/34614',headers=HEADERS,timeout=25);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
    except Exception:return out
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
            md=re.search(r'Start Date:\s*(\d{2})-(\d{2})-(\d{4}).*?End Date:\s*(\d{2})-(\d{2})-(\d{4})',text,re.I)
            if not md:continue
            start=f'{md.group(3)}-{md.group(2)}-{md.group(1)}'; end=f'{md.group(6)}-{md.group(5)}-{md.group(4)}'
            mf=re.search(r'Funding:\s*(.*?)\s+Start Date:',text,re.I); funder=(mf.group(1).strip() if mf else 'Official IT project')[:120]
            obj=re.search(r'MAIN OBJECTIVE:\s*(.*?)\s+Reference:',text,re.I); summary=(obj.group(1).strip() if obj else title)[:420]
            out.append({'acronym':acronym,'title':title,'funder':funder,'startDate':start,'endDate':end,'dates':f'{start}–{end}','scope':'QuLab / IT','text':summary,'url':u});existing.add(u)
        except Exception:continue
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--summary',default='/tmp/qiqo-weekly-summary.md');args=ap.parse_args()
    titles=existing_titles(); news_urls=existing_urls(NEWS); project_urls=existing_urls(PROJECTS)
    warnings=[]
    try: pubs=discover_arxiv(titles)
    except Exception as e: pubs=[];warnings.append(f'arXiv: {e}')
    try: pubs+=discover_crossref(titles)
    except Exception as e:warnings.append(f'Crossref: {e}')
    try: news=discover_news(news_urls)
    except Exception as e: news=[];warnings.append(f'news scan: {e}')
    try: projects=discover_projects(project_urls)
    except Exception as e: projects=[];warnings.append(f'project scan: {e}')
    append_objects(MEMBER_PUBS,pubs); append_objects(NEWS,news); append_objects(PROJECTS,projects)
    lines=['# Weekly QIQO website content review','',f'**Candidate changes:** {len(pubs)} publications · {len(news)} news items · {len(projects)} projects','']
    for label,items,key in [('Publications',pubs,'title'),('News',news,'title'),('Projects',projects,'acronym')]:
        if items:
            lines+=['## '+label]+[f'- {x[key]}' for x in items[:10]]+(['- …'] if len(items)>10 else [])+['']
    if not pubs and not news and not projects: lines+=['No new candidate content was found this week.','']
    lines+=['## Review action','Merge this PR to publish the candidates. Close it if the candidates are not relevant; nothing is auto-merged. People/student changes remain manual.']
    if warnings: lines+=['','## Source warnings']+[f'- {w}' for w in warnings]
    Path(args.summary).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))
if __name__=='__main__': main()
