from playwright.sync_api import sync_playwright
import sys
import os
B=os.environ.get("QA_BASE","http://127.0.0.1:8713"); ok=True
with sync_playwright() as p:
    br=p.chromium.launch()
    for vn,w,h in [("desktop",1440,900),("mobile",390,844)]:
        ctx=br.new_context(viewport={"width":w,"height":h}); pg=ctx.new_page()
        for f in ["index.html","clubs.html","camps.html","contacto.html"]:
            pg.goto(f"{B}/{f}", wait_until="networkidle"); pg.wait_for_timeout(300)
            n=pg.eval_on_selector_all("[data-anim], .stagger","els=>els.length")
            bad=[]
            for i in range(n):
                # jump straight to each block, as a fast flick would
                pg.evaluate(f"""() => {{
                  const el=document.querySelectorAll('[data-anim], .stagger')[{i}];
                  window.scrollTo(0, el.getBoundingClientRect().top + scrollY - innerHeight*0.45);
                }}""")
                pg.wait_for_timeout(2500)
                st=pg.evaluate(f"""() => {{
                  const el=document.querySelectorAll('[data-anim], .stagger')[{i}];
                  return {{op:getComputedStyle(el).opacity, cls:el.className.slice(0,28)}};
                }}""")
                if st["op"] != "1": bad.append((i, st["cls"], st["op"]))
            status="OK " if not bad else "FAIL"
            if bad: ok=False
            print(f"[{status}] {vn:8} {f:14} blocks={n} not-revealed-when-scrolled-to={len(bad)} {bad[:2]}")
        ctx.close()
    br.close()
print("\nREVEAL-ON-SCROLL:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
