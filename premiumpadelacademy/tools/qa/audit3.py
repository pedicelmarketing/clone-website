from playwright.sync_api import sync_playwright
import collections, json, sys
import os
B=os.environ.get("QA_BASE","http://127.0.0.1:8713")
PAGES=["index.html","clubs.html","camps.html","contacto.html",
       "en/index.html","en/clubs.html","en/camps.html","en/contact.html",
       "privacidad.html","en/privacy.html"]
JS = """() => {
  const out={small:[], overflow:[], overlap:[], docScroll:0};
  const vw=document.documentElement.clientWidth;
  // The authoritative horizontal-overflow test: can the page be scrolled sideways?
  out.docScroll = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  const clipped = (el) => {
    for (let p = el.parentElement; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.overflow === 'hidden' || cs.overflowX === 'hidden' || cs.overflow === 'clip') return true;
    }
    return false;
  };
  document.querySelectorAll('body *').forEach(el=>{
    const cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden'||cs.opacity==='0') return;
    const r=el.getBoundingClientRect();
    if(r.width===0&&r.height===0) return;
    const hasText=[...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
    if(hasText){
      const fs=Math.round(parseFloat(cs.fontSize)*10)/10;
      if(fs<15) out.small.push({tag:el.tagName.toLowerCase(), cls:(el.className||'').toString().slice(0,34), fs, txt:el.textContent.trim().slice(0,40)});
    }
    if((r.right>vw+1||r.left<-1) && !clipped(el)) out.overflow.push({tag:el.tagName.toLowerCase(), cls:(el.className||'').toString().slice(0,34), l:Math.round(r.left), r:Math.round(r.right)});
  });
  const imgs=[...document.querySelectorAll('img')].filter(i=>{const r=i.getBoundingClientRect();return r.width>0&&r.height>0&&!clipped(i);});
  for(let i=0;i<imgs.length;i++) for(let j=i+1;j<imgs.length;j++){
    const a=imgs[i].getBoundingClientRect(), b=imgs[j].getBoundingClientRect();
    const ox=Math.min(a.right,b.right)-Math.max(a.left,b.left);
    const oy=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);
    if(ox>4&&oy>4) out.overlap.push({a:imgs[i].getAttribute('src'), b:imgs[j].getAttribute('src'), ox:Math.round(ox), oy:Math.round(oy), inset:(imgs[i].classList.contains('img-inset')||imgs[j].classList.contains('img-inset')), aArea:Math.round(a.width*a.height), overlapArea:Math.round(ox*oy)});
  }
  return out;
}"""
fails=0
with sync_playwright() as p:
    br=p.chromium.launch()
    for vname,w,h in [("mobile",390,844),("desktop",1440,900)]:
        ctx=br.new_context(viewport={"width":w,"height":h}); pg=ctx.new_page()
        errs=[]; http=[]
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("response", lambda r: http.append((r.status, r.url)) if r.status>=400 else None)
        for path in PAGES:
            del errs[:], http[:]
            pg.goto(f"{B}/{path}", wait_until="networkidle"); pg.wait_for_timeout(500)
            d=pg.evaluate(JS)
            bad_overlap=[]
            for o in d['overlap']:
                designed = o['inset'] and vname=='desktop' and o['overlapArea'] <= 0.5*max(o['aArea'],1)
                if not designed: bad_overlap.append(o)
            d['overlap']=bad_overlap
            bad = len(d['small'])+len(d['overflow'])+len(d['overlap'])+len(errs)+len(http)+(1 if d['docScroll']>1 else 0)
            status = "OK " if bad==0 else "FAIL"
            if bad: fails+=1
            print(f"[{status}] {path:14} {vname:8} under15px={len(d['small'])} overflow={len(d['overflow'])} imgOverlap={len(d['overlap'])} hScroll={d['docScroll']}px pageErrors={len(errs)} http4xx5xx={len(http)}")
            for s in d['small'][:6]:  print(f"          small: {s['fs']}px <{s['tag']} class={s['cls']}> {s['txt']}")
            for o in d['overflow'][:4]: print(f"          overflow: <{o['tag']} class={o['cls']}> left={o['l']} right={o['r']}")
            for o in d['overlap'][:4]: print(f"          overlap: {o['a']} x {o['b']} = {o['ox']}x{o['oy']}px")
            for e in errs[:3]: print(f"          pageerror: {e[:110]}")
            for s,u in http[:5]: print(f"          http {s}: {u[-70:]}")
        ctx.close()
    br.close()
print("\nRESULT:", "ALL CLEAN" if fails==0 else f"{fails} failing cells")
sys.exit(1 if fails else 0)
