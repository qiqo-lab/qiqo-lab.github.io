#!/usr/bin/env python3
"""Render crawlable HTML from the same data used by the browser.

Run after editing assets/js/*-data.js. JavaScript still supplies filters, mobile
navigation and date-sensitive project status. Requires Node.js and beautifulsoup4.
"""
import datetime as dt
import html
import json
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

def render_pubs(items):
    years=sorted({p['year'] for p in items},reverse=True)
    return ''.join(f'<section class="pub-year"><div class="pub-year-label">{year}</div><div>'+''.join(f'<article class="pub-item"><span class="topic">{esc(p["topic"])}</span><h3>{link(p["url"],p["title"])}</h3><p>{esc(p["authors"])}</p><p class="venue">{esc(p["venue"])}</p></article>' for p in items if p['year']==year)+'</div></section>' for year in years)

def render_news(items,home=False):
    if home:return ''.join(f'<a class="news-line" href="{esc(n["url"])}" target="_blank" rel="noreferrer"><time>{date(n["date"])}</time><strong>{esc(n["title"])}</strong><span>↗</span></a>' for n in items[:3])
    return ''.join(f'<article class="news-card"><time datetime="{esc(n["date"])}">{date(n["date"])}</time><h3>{esc(n["title"])}</h3><p>{esc(n["text"])}</p><a class="text-link" href="{esc(n["url"])}" target="_blank" rel="noreferrer">Read source ↗</a></article>' for n in items)

def main():
    code="""const fs=require('fs'),vm=require('vm');const c={window:{}};vm.createContext(c);for(const f of ['data.js','publications-data.js','member-publications-data.js','news-data.js'])vm.runInContext(fs.readFileSync('assets/js/'+f,'utf8'),c);process.stdout.write(JSON.stringify(c.window.QIQO_DATA));"""
    data=json.loads(subprocess.check_output(['node','-e',code],cwd=ROOT,text=True))
    for _,_,filename in NAV:
        path=ROOT/filename;soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
        put(soup,'[data-site-header]',header(soup.body.get('data-page','home')))
        put(soup,'[data-publications]',render_pubs(data['publications']))
        put(soup,'[data-news]',render_news(data['news']))
        put(soup,'[data-home-news]',render_news(data['news'],True))
        path.write_text(str(soup).rstrip()+'\n',encoding='utf-8')
if __name__=='__main__':main()
