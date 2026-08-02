from playwright.sync_api import sync_playwright
import sys
import os
B=os.environ.get("QA_BASE","http://127.0.0.1:8713")
ok=True
with sync_playwright() as p:
    br=p.chromium.launch()
    # --- motion ON ---
    ctx=br.new_context(viewport={"width":1440,"height":900}); pg=ctx.new_page()
    pg.goto(B+"/index.html", wait_until="networkidle"); pg.wait_for_timeout(700)
    before=pg.evaluate("""() => {
      const els=[...document.querySelectorAll('[data-anim],.stagger')];
      return {total:els.length, shown:els.filter(e=>e.classList.contains('is-in')).length,
              drift:getComputedStyle(document.querySelector('.hero-media')).getPropertyValue('--drift')};
    }""")
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight*0.55)"); pg.wait_for_timeout(1400)
    after=pg.evaluate("""() => {
      const els=[...document.querySelectorAll('[data-anim],.stagger')];
      const hidden=els.filter(e=>{const r=e.getBoundingClientRect();
        return r.top<innerHeight && r.bottom>0 && getComputedStyle(e).opacity==='0';});
      return {shown:els.filter(e=>e.classList.contains('is-in')).length,
              inViewButInvisible:hidden.length,
              drift:getComputedStyle(document.querySelector('.hero-media')).getPropertyValue('--drift')};
    }""")
    print(f"reveal: {before['shown']}/{before['total']} at top -> {after['shown']}/{before['total']} after scroll")
    print(f"hero drift: '{before['drift'].strip() or 'none'}' -> '{after['drift'].strip() or 'none'}'")
    print(f"visible-but-transparent elements after scroll: {after['inViewButInvisible']}")
    if after['shown'] <= before['shown']: print("  !! reveal never fired"); ok=False
    if after['inViewButInvisible'] > 0: print("  !! content stuck invisible"); ok=False
    if not after['drift'].strip(): print("  !! hero drift not applied"); ok=False
    ctx.close()

    # --- reduced motion: nothing may stay hidden ---
    ctx2=br.new_context(viewport={"width":1440,"height":900}, reduced_motion="reduce"); pg2=ctx2.new_page()
    pg2.goto(B+"/index.html", wait_until="networkidle"); pg2.wait_for_timeout(800)
    rm=pg2.evaluate("""() => {
      const els=[...document.querySelectorAll('[data-anim],.stagger')];
      return {invisible: els.filter(e=>getComputedStyle(e).opacity==='0').length, total: els.length,
              heroT: getComputedStyle(document.querySelector('.hero-media img')).transform};
    }""")
    print(f"reduced-motion: {rm['invisible']}/{rm['total']} invisible (must be 0); hero transform={rm['heroT'][:24]}")
    if rm['invisible']>0: print("  !! content hidden for reduced-motion users"); ok=False
    ctx2.close()

    # --- menu still centred on v2 ---
    ctx3=br.new_context(viewport={"width":390,"height":844}); pg3=ctx3.new_page()
    pg3.goto(B+"/index.html", wait_until="networkidle"); pg3.wait_for_timeout(400)
    pg3.click(".nav-toggle"); pg3.wait_for_timeout(500)
    g=pg3.evaluate("""() => {
      const nav=document.getElementById('primary-nav'); const r=nav.getBoundingClientRect();
      const off=[...nav.querySelectorAll('a')].map(a=>{const b=a.getBoundingClientRect();return Math.abs(b.left+b.width/2-innerWidth/2);});
      return {covers:(r.top===0&&r.left===0&&Math.round(r.width)===innerWidth&&Math.round(r.height)===innerHeight), worst:Math.max(...off)};
    }""")
    print(f"menu: covers viewport={g['covers']}  worst centre offset={g['worst']}px")
    if not g['covers'] or g['worst']>1: print("  !! menu regressed"); ok=False
    br.close()
print("\nMOTION+MENU:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
