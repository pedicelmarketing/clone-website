from playwright.sync_api import sync_playwright
import sys
U="https://immigrants-energy-marine-abstract.trycloudflare.com"
PAGES=["/","/clubs.html","/camps.html","/contacto.html"]
ok=True
with sync_playwright() as p:
    br=p.chromium.launch()
    for vn,w,h in [("mobile",390,844),("desktop",1440,900)]:
        ctx=br.new_context(viewport={"width":w,"height":h}); pg=ctx.new_page()
        errs=[]; bad=[]
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("response", lambda r: bad.append((r.status,r.url)) if r.status>=400 else None)
        for path in PAGES:
            del errs[:], bad[:]
            pg.goto(U+path, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(1200)
            d=pg.evaluate("""() => {
              const mails=[...document.querySelectorAll('a[href^="mailto:"]')].map(a=>({href:a.getAttribute('href'), text:a.textContent.trim()}));
              const stubs=[...document.querySelectorAll('a[href*="email-protection"]')].length;
              const body=document.body.innerText;
              return {mails, stubs,
                      hasOldEmail: /rikicoach/i.test(body),
                      hasPhone: /600\\s*000\\s*000/.test(body),
                      hasWix: /wix/i.test(body),
                      hasNewEmail: /Infopremiumpadelacademy@gmail\\.com/i.test(body),
                      title: document.title};
            }""")
            good = d['hasNewEmail'] and not d['hasOldEmail'] and not d['hasPhone'] and not d['hasWix'] and d['stubs']==0 and not errs and not bad
            ok = ok and good
            print(f"[{'OK ' if good else 'FAIL'}] {path:15} {vn:8} mailto={len(d['mails'])} unresolvedStubs={d['stubs']} newEmail={d['hasNewEmail']} oldEmail={d['hasOldEmail']} phone={d['hasPhone']} wix={d['hasWix']} errs={len(errs)} http4xx={len(bad)}")
            if d['mails'][:1]: print(f"          resolved href: {d['mails'][0]['href']}")
            for s,u in bad[:3]: print(f"          http {s}: {u[-60:]}")
        ctx.close()
    br.close()
print("\nLIVE:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
