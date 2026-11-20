"""逐块定位 TTL 语法错误:按空行切块,逐块尝试解析。"""
import sys
from pathlib import Path

import rdflib

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

header = """@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix hm:   <https://example.org/ontology/honeymom#> .
"""

blocks = [b for b in text.split("\n\n") if b.strip()]
bad = 0
for i, b in enumerate(blocks, 1):
    if b.lstrip().startswith("@prefix"):
        continue
    g = rdflib.Graph()
    try:
        g.parse(data=header + "\n" + b, format="turtle")
    except Exception as e:
        bad += 1
        line_no = text[: text.index(b)].count("\n") + 1 if b in text else -1
        print(f"--- BLOCK {i} (file line ~{line_no}) FAILED ---")
        print(b[:600])
        print("ERROR:", str(e)[:400])
        print()
        if bad >= 3:
            break
if not bad:
    print("all blocks parse OK")
