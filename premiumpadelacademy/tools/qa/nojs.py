from playwright.sync_api import sync_playwright
import sys
import os
B=os.environ.get("QA_BASE","http://127.0.0.1:8713"); ok=True
with sync_playwright() as p:
    br=p.chromium.launch()
    # JS disabled: nothing may be invisible
    ctx=br.new_context(viewport={"width":1440,"height":900}, java_script_enabled=False); pg=ctx.new_page()
    for f in ["index.html","clubs.html","camps.html","contacto.html"]:
        pg.goto(f"{B}/{f}", wait_until="load"); pg.wait_for_timeout(400)
        d=pg.evaluate_handle("1")  # no-op; use locator counts instead
        hidden=pg.locator("[data-anim], .stagger").count()
        # measure via CSS: with JS off the .js class is absent so opacity must be 1
        vis=pg.eval_on_selector_all("[data-anim], .stagger",
            "els=>els.filter(e=>getComputedStyle(e).opacity==='0').length") if hidden else 0
        txt=len(pg.inner_text("body"))
        status = "OK " if vis==0 and txt>800 else "FAIL"
        if vis: ok=False
        print(f"[{status}] JS-OFF {f:14} reveal blocks={hidden} invisible={vis} bodyTextChars={txt}")
    ctx.close()
    br.close()
print("\nNO-JS:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
