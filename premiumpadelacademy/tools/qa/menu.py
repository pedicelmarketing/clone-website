from playwright.sync_api import sync_playwright
import sys
import os
B=os.environ.get("QA_BASE","http://127.0.0.1:8713"); OUT=sys.argv[1]
ok=True
with sync_playwright() as p:
    br=p.chromium.launch()
    ctx=br.new_context(viewport={"width":390,"height":844}, device_scale_factor=2); pg=ctx.new_page()
    for path in ["index.html","clubs.html","camps.html","contacto.html"]:
        pg.goto(f"{B}/{path}", wait_until="networkidle"); pg.wait_for_timeout(300)
        pg.click(".nav-toggle"); pg.wait_for_timeout(450)
        g=pg.evaluate("""() => {
          const nav=document.getElementById('primary-nav');
          const r=nav.getBoundingClientRect(), cs=getComputedStyle(nav);
          const links=[...nav.querySelectorAll('a')].map(a=>{const b=a.getBoundingClientRect();
            return {t:a.textContent.trim(), cx:b.left+b.width/2, top:Math.round(b.top), bottom:Math.round(b.bottom)};});
          // does the panel actually hide what is behind it?
          const mid=document.elementFromPoint(innerWidth/2, innerHeight/2);
          return {top:Math.round(r.top), left:Math.round(r.left), w:Math.round(r.width), h:Math.round(r.height),
                  vw:innerWidth, vh:innerHeight, bg:cs.backgroundColor, links,
                  hitAtCentre: mid ? (mid.id||mid.className||mid.tagName) : null,
                  navContainsHit: mid ? nav.contains(mid)||mid===nav : false};
        }""")
        covers = g['top']==0 and g['left']==0 and g['w']==g['vw'] and g['h']==g['vh']
        centred = all(abs(l['cx']-g['vw']/2) <= 1 for l in g['links'])
        inview  = all(0 <= l['top'] and l['bottom'] <= g['vh'] for l in g['links'])
        opaque  = g['navContainsHit']
        good = covers and centred and inview and opaque
        ok = ok and good
        print(f"[{'OK ' if good else 'FAIL'}] {path:14} panel={g['w']}x{g['h']} at ({g['left']},{g['top']}) vs viewport {g['vw']}x{g['vh']}")
        print(f"        covers viewport={covers}  links centred={centred}  all links in view={inview}  panel intercepts centre={opaque} (hit: {g['hitAtCentre']})")
        if not inview:
            for l in g['links']: print(f"           {l['t']:9} top={l['top']} bottom={l['bottom']}")
        if path=="index.html":
            pg.screenshot(path=f"{OUT}/new-menu-open.png")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    br.close()
print("\nMENU:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
