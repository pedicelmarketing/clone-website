"""List English strings in pages/ that strings/<lang>.json does not translate yet.

python3 extract.py   -> strings/todo-de.json, strings/todo-fr.json   ({english: ""}, page order)
"""
import json
from build import PAGES, STRINGS, routes, tmap
from textlayer import strings_in


def main() -> None:
    for lang in ("de", "fr"):
        have, todo = tmap(lang), {}
        for _, f in routes():
            for s in strings_in(f.read_text(encoding="utf-8")):
                if not have.get(s):
                    todo.setdefault(s, "")
        STRINGS.mkdir(exist_ok=True)
        (STRINGS / f"todo-{lang}.json").write_text(json.dumps(todo, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{lang}: {len(todo)} strings to translate")


if __name__ == "__main__":
    main()
