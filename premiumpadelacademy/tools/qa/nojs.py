from playwright.sync_api import sync_playwright
import sys
import os
B=os.environ.get("QA_BASE","http://127.0.0.1:8713"); ok=True
PAGES=["index.html","clubs.html","camps.html","contacto.html",
       "en/index.html","en/clubs.html","en/camps.html","en/contact.html"]
# Floor for "the page actually rendered something" with JS off. contacto.html
# is a short contact form and legitimately sits at ~580 chars, so an 800 floor
# mislabels it. This threshold now feeds the verdict instead of only the label —
# previously the two disagreed and the row printed FAIL on a passing run.
MIN_TEXT=400
with sync_playwright() as p:
    br=p.chromium.launch()
    # JS disabled: nothing may be invisible
    ctx=br.new_context(viewport={"width":1440,"height":900}, java_script_enabled=False); pg=ctx.new_page()
    for f in PAGES:
        pg.goto(f"{B}/{f}", wait_until="load"); pg.wait_for_timeout(400)
        d=pg.evaluate_handle("1")  # no-op; use locator counts instead
        hidden=pg.locator("[data-anim], .stagger").count()
        # measure via CSS: with JS off the .js class is absent so opacity must be 1
        vis=pg.eval_on_selector_all("[data-anim], .stagger",
            "els=>els.filter(e=>getComputedStyle(e).opacity==='0').length") if hidden else 0
        txt=len(pg.inner_text("body"))
        good = vis==0 and txt>MIN_TEXT
        status = "OK " if good else "FAIL"
        if not good: ok=False
        print(f"[{status}] JS-OFF {f:16} reveal blocks={hidden} invisible={vis} bodyTextChars={txt}")
    ctx.close()
    br.close()
print("\nNO-JS:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
