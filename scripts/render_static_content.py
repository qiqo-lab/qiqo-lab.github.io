#!/usr/bin/env python3
"""Render crawlable HTML from the same data used by the browser.

Run after editing assets/js/*-data.js. JavaScript still supplies filters, mobile
navigation and date-sensitive project status. Requires Node.js and beautifulsoup4.
"""
import datetime as dt
import html
import hashlib
import json
import re
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
NAV = [('home','Home','index.html'),('research','Research','research.html'),('people','People','people.html'),('publications','Publications','publications.html'),('projects','Projects','projects.html'),('facilities','Facilities','facilities.html'),('news','News','news.html'),('opportunities','Join us','opportunities.html'),('contact','Contact','contact.html')]

def esc(s): return html.escape(str(s or ''), quote=True)
def date(s): return dt.date.fromisoformat(s).strftime('%d %b %Y')
def link(url,label): return f'<a href="{esc(url)}" target="_blank" rel="noreferrer">{esc(label)}</a>'
def put(soup, selector, content):
    el=soup.select_one(selector)
    if el is not None:
        el.clear()
        el.append(BeautifulSoup(content,'html.parser'))

def header(page):
    nav=''.join(f'<a href="{url}"'+(' class="active"' if key==page else '')+f'>{label}</a>' for key,label,url in NAV)
    return '<header class="site-header"><div class="shell nav-wrap"><div class="header-logos"><a class="brand" href="index.html" aria-label="QIQO home"><img class="brand-logo" src="assets/img/logo/qiqo-logo-2.png" alt="QIQO Laboratory logo"></a><div class="partner-logos" aria-label="Partner institutions"><a class="partner-logo partner-logo-it" href="https://www.it.pt/" aria-label="Instituto de Telecomunicações"><img src="assets/img/logo/it-logo.png" alt="Instituto de Telecomunicações" width="525" height="188"></a><a class="partner-logo partner-logo-ipfn" href="https://www.ipfn.tecnico.ulisboa.pt/" aria-label="Instituto de Plasmas e Fusão Nuclear"><img src="assets/img/logo/ipfn-logo.png" alt="Instituto de Plasmas e Fusão Nuclear" width="428" height="179"></a></div></div><button class="nav-toggle" aria-expanded="false" aria-label="Toggle navigation"><span></span><span></span><span></span></button><nav class="main-nav" aria-label="Primary navigation">'+nav+'</nav></div></header>'

def pub_sort_key(p):
    value=str(p.get('date') or '')
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            return dt.date.fromisoformat(value)
    except ValueError:
        pass
    raw=f"{p.get('url','')} {p.get('venue','')}"
    m=re.search(r'(?:arxiv\.org/abs/|arXiv:)(\d{2})(\d{2})\.\d{4,5}',raw,re.I)
    if m:
        year=2000+int(m.group(1)); month=int(m.group(2))
        if 1 <= month <= 12:
            return dt.date(year,month,1)
    return dt.date(int(p.get('year') or 1),1,1)

def render_pubs(items):
    items=sorted(items,key=pub_sort_key,reverse=True)
    years=sorted({p['year'] for p in items},reverse=True)
    return ''.join(f'<section class="pub-year"><div class="pub-year-label">{year}</div><div>'+''.join(f'<article class="pub-item"><span class="topic">{esc(p["topic"])}</span><h3>{link(p["url"],p["title"])}</h3><p>{esc(p["authors"])}</p><p class="venue">{esc(p["venue"])}</p></article>' for p in items if p['year']==year)+'</div></section>' for year in years)

def cache_bust_page_assets(soup):
    if not soup.body:
        return
    page=soup.body.get('data-page')
    if page=='publications':
        targets={'assets/js/publications-data.js','assets/js/member-publications-data.js','assets/js/site.js'}
    elif page=='people':
        targets={'assets/js/people-data.js','assets/js/site.js'}
    else:
        return
    for script in soup.find_all('script',src=True):
        base=script['src'].split('?',1)[0]
        if base in targets:
            digest=hashlib.sha256((ROOT/base).read_bytes()).hexdigest()[:12]
            script['src']=f'{base}?v={digest}'

def render_news(items,home=False):
    if home:return ''.join(f'<a class="news-line" href="{esc(n["url"])}" target="_blank" rel="noreferrer"><time>{date(n["date"])}</time><strong>{esc(n["title"])}</strong><span>↗</span></a>' for n in items[:3])
    return ''.join(f'<article class="news-card"><time datetime="{esc(n["date"])}">{date(n["date"])}</time><h3>{esc(n["title"])}</h3><p>{esc(n["text"])}</p><a class="text-link" href="{esc(n["url"])}" target="_blank" rel="noreferrer">Read source ↗</a></article>' for n in items)

def render_people(items,large=False):
    cards=[]
    for p in items:
        avatar=(f'<img class="avatar avatar-photo" src="{esc(p["image"])}" alt="{esc(p["name"])}" loading="lazy">' if p.get('image') else f'<div class="avatar" aria-hidden="true">{esc(p["initials"])}</div>')
        links=([{'url':p['url'],'label':p.get('urlLabel','Profile')}] if p.get('url') else [])+p.get('links',[])
        buttons=''.join(f'<a class="mini-link" href="{esc(x["url"])}" target="_blank" rel="noreferrer">{esc(x["label"])} ↗</a>' for x in links)
        card_class='person-card person-card-large' if large else 'person-card'
        cards.append(f'<article class="{card_class}">{avatar}<div class="person-copy"><span class="eyebrow">{esc(p["role"])}</span><h3>{esc(p["name"])}</h3><p class="muted">{esc(p.get("affiliation") or p.get("team") or "")}</p><p>{esc(p.get("focus",""))}</p><div class="mini-links">{buttons}</div></div></article>')
    return ''.join(cards)

def main():
    code="""const fs=require('fs'),vm=require('vm');const c={window:{}};vm.createContext(c);for(const f of ['data.js','people-data.js','publications-data.js','member-publications-data.js','news-data.js'])vm.runInContext(fs.readFileSync('assets/js/'+f,'utf8'),c);process.stdout.write(JSON.stringify(c.window.QIQO_DATA));"""
    data=json.loads(subprocess.check_output(['node','-e',code],cwd=ROOT,text=True))
    for _,_,filename in NAV:
        path=ROOT/filename;soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
        put(soup,'[data-site-header]',header(soup.body.get('data-page','home')))
        put(soup,'[data-publications]',render_pubs(data['publications']))
        put(soup,'[data-news]',render_news(data['news']))
        put(soup,'[data-home-news]',render_news(data['news'],True))
        for selector,key,large in [('data-leadership','leadership',True),('data-postdocs','postdocs',False),('data-phd-students','phdStudents',False),('data-master-students','masterStudents',False),('data-bachelor-students','bachelorStudents',False),('data-steering','steering',True),('data-alumni','alumni',False)]:
            put(soup,f'[{selector}]',render_people(data.get(key,[]),large))
        cache_bust_page_assets(soup)
        path.write_text(str(soup).rstrip()+'\n',encoding='utf-8')
if __name__=='__main__':main()
