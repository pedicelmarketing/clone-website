from playwright.sync_api import sync_playwright
import json, sys
OUT=sys.argv[1]
B="https://97jnvjsg4j.wixsite.com/riki-coach"
ROUTES=[("inicio",B),("clubs",B+"/home"),("camps",B+"/camps"),("contacto",B+"/contacto")]

STRUCT = """() => {
  const seen=[];
  const walk=(el,depth)=>{
    for(const c of el.children){
      const cs=getComputedStyle(c), r=c.getBoundingClientRect();
      if(cs.display==='none'||cs.visibility==='hidden'){continue;}
      const tag=c.tagName.toLowerCase();
      const ownText=[...c.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).join(' ').trim();
      if(/^(h1|h2|h3|h4|h5|p|li|a|button|img|input|textarea|label)$/.test(tag)){
        seen.push({tag, depth,
          text: ownText.slice(0,300) || (tag==='img'? '' : c.innerText.trim().slice(0,300)),
          src: c.getAttribute('src')||null, alt: c.getAttribute('alt')||null,
          href: c.getAttribute('href')||null,
          font: cs.fontFamily.split(',')[0].replace(/["']/g,''),
          size: Math.round(parseFloat(cs.fontSize)*10)/10,
          weight: cs.fontWeight, color: cs.color, ls: cs.letterSpacing,
          transform: cs.textTransform,
          y: Math.round(r.top+scrollY), h: Math.round(r.height), w: Math.round(r.width)
        });
      }
      walk(c,depth+1);
    }
  };
  walk(document.body,0);
  // background colours of large blocks = section palette
  const bands=[];
  document.querySelectorAll('div,section,main,footer,header').forEach(e=>{
    const r=e.getBoundingClientRect(), cs=getComputedStyle(e);
    if(r.height>200 && r.width>=innerWidth*0.9 && cs.backgroundColor!=='rgba(0, 0, 0, 0)'){
      bands.push({y:Math.round(r.top+scrollY), h:Math.round(r.height), bg:cs.backgroundColor, bgImage:cs.backgroundImage.slice(0,120)});
    }
  });
  return {nodes:seen, bands, docHeight: document.body.scrollHeight, vw: innerWidth};
}"""

res={}
with sync_playwright() as p:
    br=p.chromium.launch()
    for vname,w,h in [("desktop",1440,900),("mobile",390,844)]:
        ctx=br.new_context(viewport={"width":w,"height":h})
        pg=ctx.new_page()
        for name,url in ROUTES:
            pg.goto(url, wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(5000)
            for _ in range(10):
                pg.mouse.wheel(0,1500); pg.wait_for_timeout(250)
            pg.wait_for_timeout(1500)
            d=pg.evaluate(STRUCT)
            res[f"{name}|{vname}"]=d
            pg.screenshot(path=f"{OUT}/src-{name}-{vname}.png", full_page=True)
            print(f"  {name}/{vname}: {len(d['nodes'])} nodes, doc {d['docHeight']}px", flush=True)
        ctx.close()
    br.close()
json.dump(res, open(f"{OUT}/observation.json","w"), ensure_ascii=False, indent=1)
print("OBSERVE DONE")
