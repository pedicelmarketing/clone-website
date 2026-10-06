import json, re, sys, unicodedata, difflib
obs=json.load(open(sys.argv[1]))
build=json.load(open(sys.argv[2]))
MAP={"inicio":"index.html","clubs":"clubs.html","camps":"camps.html","contacto":"contacto.html"}
def norm(s):
    s=unicodedata.normalize("NFC", s)
    s=re.sub(r"\s+"," ",s).strip()
    return s
def texts(nodes):
    out=[]
    for x in nodes:
        if x.get("font") in ("Arial","Helvetica","Wix Madefor Text"): continue
        t=norm(x.get("text") or "")
        if len(t)>=12 and not t.startswith("Ir al contenido"): out.append(t)
    return out
for route,page in MAP.items():
    src=texts(obs[f"{route}|desktop"]["nodes"])
    new=texts(build[page])
    missing=[s for s in src if not any(difflib.SequenceMatcher(None,s,n).ratio()>0.90 for n in new)]
    print("="*22, route, "->", page)
    print(f"  source strings: {len(src)}   build strings: {len(new)}   not matched: {len(missing)}")
    for m in missing:
        best=max(new, key=lambda n: difflib.SequenceMatcher(None,m,n).ratio(), default="")
        r=difflib.SequenceMatcher(None,m,best).ratio()
        print(f"   SRC : {m[:150]}")
        print(f"   BLD : {best[:150] if r>0.5 else '(no close match)'}   [{r:.2f}]")
