from playwright.sync_api import sync_playwright
import json, sys
import os
B=os.environ.get("QA_BASE","http://127.0.0.1:8713"); out={}
JS="""() => [...document.querySelectorAll('h1,h2,h3,h4,h5,p,li,a,label,button')]
  .map(e=>({text:(e.innerText||'').trim(), font:'x'})).filter(o=>o.text)"""
with sync_playwright() as p:
    br=p.chromium.launch(); ctx=br.new_context(viewport={"width":1440,"height":900}); pg=ctx.new_page()
    for page in ["index.html","clubs.html","camps.html","contacto.html"]:
        pg.goto(f"{B}/{page}", wait_until="networkidle"); pg.wait_for_timeout(400)
        out[page]=pg.evaluate(JS)
    br.close()
json.dump(out, open(sys.argv[1],"w"), ensure_ascii=False)
print("build text captured")
