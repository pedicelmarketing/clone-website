from playwright.sync_api import sync_playwright
import sys
B=sys.argv[1]; OUT=sys.argv[2]; TAG=sys.argv[3]
PAGES=[("index.html","home"),("clubs.html","clubs"),("camps.html","camps"),("contacto.html","contacto")]
with sync_playwright() as p:
    br=p.chromium.launch()
    for vn,w,h in [("desktop",1440,900),("mobile",390,844)]:
        ctx=br.new_context(viewport={"width":w,"height":h}, device_scale_factor=2 if vn=="mobile" else 1)
        pg=ctx.new_page()
        for path,name in PAGES:
            pg.goto(f"{B}/{path}", wait_until="networkidle")
            # scroll the whole page so IntersectionObserver reveals everything
            pg.evaluate("""async () => {
              const step = innerHeight*0.7;
              for (let y=0; y<document.body.scrollHeight; y+=step) {
                window.scrollTo(0,y); await new Promise(r=>setTimeout(r,320));
              }
              window.scrollTo(0,0); await new Promise(r=>setTimeout(r,1400));
            }""")
            pg.wait_for_timeout(500)
            pg.screenshot(path=f"{OUT}/{TAG}-{name}-{vn}.png", full_page=True)
        ctx.close()
    br.close()
print("shots done")
