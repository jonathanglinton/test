#!/usr/bin/env python3
"""Pitch Inbox Build - Expanded V2 + Yahoo Finance + Insider Flag"""
import json, pathlib, argparse
from datetime import datetime
from html import escape

REQUIRED_FIELDS = ["pitch_id","discovered_at","published_at","primary_ticker","tickers","company","sector","subsector","coverage_match","stance","source_name","source_type","title","one_liner","url","quality","status","run_id"]

def load_feed(path):
    records=[]
    with open(path) as f:
        for i,line in enumerate(f,1):
            line=line.strip()
            if not line: continue
            try: records.append(json.loads(line))
            except Exception as e: raise ValueError(f"Feed line {i}: {e}")
    records.sort(key=lambda r: r.get("published_at",""), reverse=True)
    return records

def load_json(p):
    with open(p) as f: return json.load(f)

def fmt_mcap(v):
    if not v: return ""
    try:
        v=float(v)
        if v>=1e12: return f"${v/1e12:.1f}T"
        if v>=1e9: return f"${v/1e9:.1f}B"
        if v>=1e6: return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"
    except: return str(v)

def fmt_price(v):
    if v is None: return ""
    try: return f"${float(v):.2f}"
    except: return str(v)

def feed_metadata(records, state):
    """Prefer metadata carried by the feed over stale render-state metadata."""
    latest = max(records, key=lambda r: r.get("discovered_at", ""), default={})
    updated = latest.get("discovered_at") or state.get("last_successful_refresh", "")
    run_id = latest.get("run_id") or state.get("run_id", "")
    return updated, run_id

def render_html(records, state, coverage, sources, output_path):
    last_refresh, feed_run_id = feed_metadata(records, state)
    try:
        dt = datetime.fromisoformat(last_refresh.replace("Z","+00:00"))
        last_refresh_str = dt.strftime("%Y-%m-%d %H:%M UTC")
    except: last_refresh_str = last_refresh
    src_status = state.get("sources",{})
    total = len(records)
    sectors = sorted(set(r.get("sector","") for r in records))
    subsectors = sorted(set(r.get("subsector","") for r in records))
    source_names = sorted(set(r.get("source_name","") for r in records))
    html=[]
    html.append("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Pitch Inbox — Full Coverage + Yahoo</title><style>")
    html.append(":root{--bg:#0a0a0b;--card:#141416;--card-hover:#1a1a1e;--border:#232326;--text:#e8e8ea;--muted:#9a9aa0;--accent:#d6ff57;--accent-2:#8a7dff;--long:#2de2a8;--short:#ff6b6b;--exact:#d6ff57;--sector:#8a7dff;--housing:#ff8a5c;--renew:#4ad6ff;--event:#ffb84a;--warn:#ff4d4d;--ok:#2de2a8;}")
    html.append("*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;line-height:1.5}")
    html.append(".wrap{max-width:1080px;margin:0 auto;padding:32px 20px 80px}")
    html.append("header{border:1px solid var(--border);padding:20px;background:var(--card);margin-bottom:16px}")
    html.append("h1{font-size:22px;margin:0 0 8px} .meta{color:var(--muted);font-size:12px;display:flex;flex-wrap:wrap;gap:12px} .meta b{color:var(--text)}")
    html.append(".coverage{margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;font-size:11px} .chip{border:1px solid var(--border);padding:3px 8px;border-radius:999px;background:#0f0f10} .chip.ok{border-color:#2a3d2a;color:#9fdb9f} .chip.fail{border-color:#4a2a2a;color:#ff9a9a} .chip.unavail{color:var(--muted)}")
    html.append(".controls{border:1px solid var(--border);background:var(--card);padding:12px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px;position:sticky;top:0;z-index:10}")
    html.append(".controls input,.controls select,.controls button{background:#0f0f10;border:1px solid var(--border);color:var(--text);padding:8px 10px;font-family:inherit;font-size:12px;border-radius:6px} .controls input{flex:1 1 220px;min-width:180px} .controls button{cursor:pointer} .controls button.active{background:var(--text);color:var(--bg)} .count{font-size:12px;color:var(--muted);margin-left:auto}")
    html.append(".list{display:flex;flex-direction:column;gap:1px;border:1px solid var(--border);background:var(--border)}")
    html.append(".item{background:var(--card);padding:14px 16px;display:grid;grid-template-columns:1fr auto;gap:8px 12px} .item:hover{background:var(--card-hover)}")
    html.append(".item-top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px} .ticker{background:var(--text);color:var(--bg);padding:2px 6px;font-weight:700;font-size:11px} .company{font-weight:600} .date{color:var(--muted);margin-left:auto} .price{color:var(--accent);font-weight:600}")
    html.append(".item-mid{display:flex;gap:6px;flex-wrap:wrap;font-size:11px} .badge{border:1px solid var(--border);padding:2px 6px;border-radius:999px} .badge.source{color:var(--muted)} .badge.exact{color:var(--exact);border-color:#3a3d2a} .badge.sector{color:var(--sector);border-color:#2a2a4a} .badge.long{color:var(--long);border-color:#1a3a32} .badge.short{color:var(--short);border-color:#4a2a2a} .badge.housing{color:var(--housing);border-color:#4a332a} .badge.renew{color:var(--renew);border-color:#2a3a4a} .badge.event{color:var(--event);border-color:#4a3a2a} .badge.warn{color:var(--warn);border-color:#4a2a2a;background:#1a0f0f} .badge.ok{color:var(--ok);border-color:#1a3a2a} .badge.yahoo{color:var(--accent-2);border-color:#2a2a4a}")
    html.append(".thesis{grid-column:1/-1;font-size:13px;line-height:1.5;margin-top:2px;cursor:pointer;user-select:none} .thesis:hover{color:var(--accent)} .expand-hint{color:var(--muted);font-size:11px;margin-left:6px}")
    html.append(".details{grid-column:1/-1;display:none;border-top:1px dashed var(--border);margin-top:8px;padding-top:10px;font-size:12px} .details.show{display:block} .details ul{margin:6px 0 10px 18px;padding:0} .details li{margin-bottom:5px}")
    html.append(".detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px} @media(max-width:640px){.detail-grid{grid-template-columns:1fr}}")
    html.append(".detail-box{border:1px solid var(--border);background:#0f0f10;padding:8px 10px;border-radius:6px} .detail-box b{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em} .detail-box div{margin-top:3px}")
    html.append(".yahoo-bar{grid-column:1/-1;display:flex;gap:12px;flex-wrap:wrap;font-size:11px;color:var(--muted);border:1px solid var(--border);background:#0f0f10;padding:6px 10px;border-radius:6px;margin-top:6px} .yahoo-bar b{color:var(--text)}")
    html.append(".source-link{margin-top:10px;font-size:11px} .source-link a{color:var(--muted);text-decoration:none;border-bottom:1px dotted #444} .source-link a:hover{color:var(--accent)}")
    html.append(".open{grid-column:2;grid-row:1/span 5;align-self:start;font-size:11px;color:var(--muted);text-decoration:none;border:1px solid var(--border);padding:6px 10px;border-radius:999px;margin-top:2px} .open:hover{color:var(--text);border-color:var(--text)} @media(max-width:640px){.item{grid-template-columns:1fr} .open{grid-column:1;justify-self:start}}")
    html.append("footer{margin-top:24px;color:var(--muted);font-size:11px;border-top:1px solid var(--border);padding-top:16px}")
    html.append("</style></head><body><div class='wrap'><header><h1>Pitch Inbox — Full Coverage + Yahoo Finance</h1><div class='meta'>")
    html.append(f"<span>Feed updated: <b>{escape(last_refresh_str)}</b></span><span>Feed: <b>{total} pitches</b></span><span>Window: <b>90 days</b></span><span>Feed run: <b>{escape(feed_run_id)}</b></span></div><div class='coverage'><span style='color:var(--muted)'>Sources:</span>")
    for sid, info in src_status.items():
        st = info.get("status","unknown"); cls="ok" if st=="complete" else "fail" if st=="failed" else "unavail"; label=f"{sid} {st}";
        html.append(f"<span class='chip {cls}'>{escape(label)}</span>")
    html.append("</div><div style='margin-top:10px;font-size:11px;color:var(--muted)'>Yahoo Finance: price, mkt cap, 52w, insider sales flagged. <span style='color:var(--warn)'>⚠️ = insider sales >$1M in 90d</span> <span style='color:var(--ok)'>✓ = no sales</span></div></header>")
    html.append("<div class='controls'><input id='q' type='search' placeholder='Search ticker, thesis, bullets, insider...'><select id='sectorFilter'><option value=''>All sectors</option>")
    for s in sectors: html.append(f"<option value='{escape(s)}'>{escape(s)}</option>")
    html.append("</select><select id='subsectorFilter'><option value=''>All subsectors</option>")
    for s in subsectors: html.append(f"<option value='{escape(s)}'>{escape(s)}</option>")
    html.append("</select><select id='sourceFilter'><option value=''>All sources</option>")
    for src in source_names: html.append(f"<option value='{escape(src)}'>{escape(src)}</option>")
    html.append("</select><select id='insiderFilter'><option value=''>All insider</option><option value='sale'>Has sales</option><option value='no_sale'>No sales</option></select>")
    html.append("<div style='display:flex;gap:6px;'><button data-days='30' class='timeBtn'>30d</button><button data-days='90' class='timeBtn active'>90d</button><button data-days='9999' class='timeBtn'>All</button></div><span class='count' id='count'></span></div>")
    html.append("<div class='list' id='list'>")
    for r in records:
        ticker=escape(r.get("primary_ticker","")); company=escape(r.get("company","")); pub=escape(r.get("published_at","")); source=escape(r.get("source_name","")); cm=escape(r.get("coverage_match","")); stance=escape(r.get("stance","")); one_liner=escape(r.get("one_liner","")); url=escape(r.get("url","")); title=escape(r.get("title","")); subsector=escape(r.get("subsector","")); sector=escape(r.get("sector",""));
        bullets=r.get("bullets",[]); catalyst=escape(r.get("catalyst","")); valuation=escape(r.get("valuation","")); risks=escape(r.get("risks",""));
        yahoo=r.get("yahoo",{}) or {}; price=yahoo.get("price"); mcap=yahoo.get("market_cap"); high52=yahoo.get("high_52w"); low52=yahoo.get("low_52w"); insider_flag=escape(yahoo.get("insider_flag","") or ""); insider_type=yahoo.get("insider_type",""); # sale/no_sale
        search_blob=" ".join([r.get("primary_ticker",""), r.get("company",""), r.get("one_liner",""), r.get("title",""), r.get("subsector",""), r.get("sector",""), " ".join(bullets), insider_flag]).lower(); search_blob=escape(search_blob);
        sector_cls="housing" if sector=="Housing" else "renew" if sector=="Renewables" else "event" if sector=="Event-Driven" else "";
        cm_cls="exact" if cm=="exact_company" else "sector";
        # insider badge
        insider_badge=""
        if insider_type=="sale":
            insider_badge=f"<span class='badge warn'>⚠️ {insider_flag}</span>"
        elif insider_type=="no_sale":
            insider_badge=f"<span class='badge ok'>✓ {insider_flag}</span>"
        elif insider_flag:
            insider_badge=f"<span class='badge warn'>{insider_flag}</span>"
        html.append(f"<div class='item' data-pub='{pub}' data-sector='{sector}' data-subsector='{subsector}' data-source='{source}' data-search='{search_blob}' data-insider='{insider_type}'>")
        html.append(f"<div class='item-top'><span class='ticker'>{ticker}</span><span class='company'>{company}</span><span class='price'>{fmt_price(price)}</span><span class='date'>{pub}</span></div>")
        html.append(f"<div class='item-mid'><span class='badge source'>{source}</span><span class='badge {cm_cls}'>{cm}</span><span class='badge {stance}'>{stance}</span><span class='badge {sector_cls}'>{sector}</span><span class='badge source'>{subsector}</span>{insider_badge}<span class='badge yahoo'>{fmt_mcap(mcap)} {('52w '+fmt_price(low52)+'–'+fmt_price(high52)) if high52 else ''}</span></div>")
        html.append(f"<div class='yahoo-bar'><span>Price: <b>{fmt_price(price)}</b></span><span>MktCap: <b>{fmt_mcap(mcap)}</b></span><span>52w: <b>{fmt_price(low52)}–{fmt_price(high52)}</b></span><span>{insider_flag or 'No insider flag'}</span></div>")
        html.append(f"<div class='thesis' onclick='toggleDetails(this)'><span>{one_liner}</span><span class='expand-hint'>[expand]</span></div>")
        html.append("<div class='details'>")
        if bullets:
            html.append("<ul>")
            for b in bullets: html.append(f"<li>{escape(b)}</li>")
            html.append("</ul>")
        html.append("<div class='detail-grid'>")
        if catalyst: html.append(f"<div class='detail-box'><b>Catalyst</b><div>{catalyst}</div></div>")
        if valuation: html.append(f"<div class='detail-box'><b>Valuation</b><div>{valuation}</div></div>")
        if risks: html.append(f"<div class='detail-box'><b>Risks</b><div>{risks}</div></div>")
        # Yahoo detail box
        if yahoo:
            html.append(f"<div class='detail-box'><b>Yahoo Finance</b><div>Price {fmt_price(price)} | MktCap {fmt_mcap(mcap)} | 52w {fmt_price(low52)}–{fmt_price(high52)}<br>{insider_flag}<br><a href='https://finance.yahoo.com/quote/{ticker}/holders' target='_blank'>Insiders @ Yahoo →</a></div></div>")
        html.append("</div>")
        html.append(f"<div class='source-link'><a href='{url}' target='_blank' rel='noopener'>Source: {title} — {url} →</a> | <a href='https://finance.yahoo.com/quote/{ticker}' target='_blank'>Yahoo Finance {ticker} →</a></div>")
        html.append("</div>")
        html.append(f"<a class='open' href='{url}' target='_blank' rel='noopener'>Open →</a></div>")
    html.append("</div>")
    html.append("<footer><div>Expanded coverage: REITs + Housing + Renewables + Event-Driven. Yahoo Finance enrichment: price, mkt cap, 52w, insider sales flagged. Click thesis to expand.</div></footer></div>")
    html.append("<script>function toggleDetails(el){const d=el.nextElementSibling;const isShow=d.classList.contains('show');document.querySelectorAll('.details').forEach(x=>x.classList.remove('show'));document.querySelectorAll('.thesis').forEach(x=>{x.classList.remove('expanded');const h=x.querySelector('.expand-hint');if(h)h.textContent='[expand]'});if(!isShow){d.classList.add('show');el.classList.add('expanded');const h=el.querySelector('.expand-hint');if(h)h.textContent='[collapse]'}} const q=document.getElementById('q');const sectorFilter=document.getElementById('sectorFilter');const subsectorFilter=document.getElementById('subsectorFilter');const sourceFilter=document.getElementById('sourceFilter');const insiderFilter=document.getElementById('insiderFilter');const timeBtns=document.querySelectorAll('.timeBtn');const countEl=document.getElementById('count');let daysWindow=90;function parseDate(s){const d=new Date(s);return isNaN(d)?null:d}function filter(){const term=q.value.toLowerCase().trim();const sector=sectorFilter.value;const subsector=subsectorFilter.value;const src=sourceFilter.value;const insider=insiderFilter.value;const now=new Date();const items=document.querySelectorAll('.item');let visible=0;items.forEach(el=>{const search=el.dataset.search||'';const pub=parseDate(el.dataset.pub);const sec=el.dataset.sector||'';const sub=el.dataset.subsector||'';const source=el.dataset.source||'';const ins=el.dataset.insider||'';let ok=true;if(term&&!search.includes(term))ok=false;if(sector&&sec!==sector)ok=false;if(subsector&&sub!==subsector)ok=false;if(src&&source!==src)ok=false;if(insider&&ins!==insider)ok=false;if(daysWindow<9999&&pub){const diff=(now-pub)/(1000*60*60*24);if(diff>daysWindow)ok=false}el.style.display=ok?'':'none';if(ok)visible++});countEl.textContent=visible+' shown'}q.addEventListener('input',filter);sectorFilter.addEventListener('change',filter);subsectorFilter.addEventListener('change',filter);sourceFilter.addEventListener('change',filter);insiderFilter.addEventListener('change',filter);timeBtns.forEach(btn=>{btn.addEventListener('click',()=>{timeBtns.forEach(b=>b.classList.remove('active'));btn.classList.add('active');daysWindow=parseInt(btn.dataset.days,10);filter()})});filter();</script></body></html>")
    with open(output_path,"w") as out: out.write("".join(html))
    return output_path

def main():
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("--input",default="pitches.jsonl"); parser.add_argument("--output",default="pitch_inbox.html"); parser.add_argument("--state",default="state.json"); parser.add_argument("--coverage",default="coverage.json"); parser.add_argument("--sources",default="sources.json"); args=parser.parse_args();
    base=pathlib.Path(__file__).parent;
    inp=base/args.input; out=base/args.output; state_p=base/args.state; cov_p=base/args.coverage; src_p=base/args.sources;
    records=load_feed(inp); state=load_json(state_p) if state_p.exists() else {}; coverage=load_json(cov_p) if cov_p.exists() else {}; sources=load_json(src_p) if src_p.exists() else {};
    render_html(records, state, coverage, sources, out); print(f"Rendered {len(records)} pitches -> {out}")

if __name__=='__main__': main()
