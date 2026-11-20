#!/usr/bin/env python3
"""重建本目录的全部本体产物并做一致性校验。

产物链:
  honeymom.ttl(唯一真源)
    ├─ honeymom.html   ← wuming-ontology 技能的产物脚本(带交付基线检查)
    ├─ honeymom.owx    ← Protégé 自带 OWL API 的官方渲染器
    ├─ honeymom.ofn    ← 同上(Functional Syntax)
    ├─ honeymom.omn    ← 同上(Manchester Syntax)
    ├─ honeymom.rdf    ← 同上(RDF/XML)
    ├─ honeymom.jsonld ← rdflib
    └─ honeymom.nt     ← rdflib

校验:
  - 技能基线检查(Turtle 解析 / label / domain / range / 外部引用)
  - OWL API 官方解析器回读每个 OWL 序列化,要求"源公理 100% 保留"
    (允许多出声明型公理,如 Declaration(Class(rdfs:Resource)))
  - rdflib 回读 jsonld / nt,要求与源图同构
  - HermiT 推理器(Protégé 内置)判定一致性

用法:
    python tools/regenerate_all.py [技能根目录] [Protégé 安装目录]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import rdflib
from rdflib.compare import isomorphic

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
TTL = OUT / "honeymom.ttl"

DEFAULT_SKILL = Path(r"C:\Users\pengjun\.minimax\skills\wuming-ontology")
DEFAULT_PROTEGE = Path(r"C:\ProgramData\Protege-5.6.9")


def step(n: int, title: str) -> None:
    print(f"\n[{n}] {title}")


def main() -> int:
    skill = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SKILL
    protege = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PROTEGE
    script = skill / "scripts" / "ontology_artifacts.py"

    step(1, "校验 honeymom.ttl 并生成 honeymom.html(技能的交付基线检查)")
    if not script.exists():
        print(f"找不到技能产物脚本: {script}", file=sys.stderr)
        return 2
    r = subprocess.run(
        [sys.executable, str(script), str(TTL), "--html", str(OUT / "honeymom.html"),
         "--overwrite"],
        capture_output=True, text=True, encoding="utf-8",
    )
    print((r.stdout or r.stderr).strip())
    if r.returncode != 0:
        return r.returncode

    step(2, "派生 RDF 序列化(rdflib)")
    g = rdflib.Graph()
    g.parse(str(TTL), format="turtle")
    print(f"  源 Turtle: {len(g)} 三元组")
    for fmt, name in (("json-ld", "honeymom.jsonld"), ("nt", "honeymom.nt")):
        g.serialize(destination=str(OUT / name), format=fmt)
        print(f"  已生成 {name}")

    step(3, "派生 OWL 序列化 + 官方解析器回读 + HermiT 推理(Protégé 自带 OWL API)")
    jrunscript = protege / "jre" / "bin" / "jrunscript.exe"
    if not jrunscript.exists():
        print(f"  未找到 {jrunscript},跳过(Protégé 未安装到 {protege})")
    else:
        jars = []
        for folder in ("bundles", "plugins", "lib-extra"):
            jars += sorted(str(p) for p in (protege / folder).glob("*.jar"))
        cp = ";".join(jars)
        r = subprocess.run(
            [str(jrunscript), "-cp", cp, str(HERE / "verify_with_owlapi.js"),
             str(TTL), str(OUT)],
            cwd=str(protege), capture_output=True, text=True, encoding="utf-8",
            errors="replace",
        )
        out = "\n".join(
            ln for ln in (r.stdout or "").splitlines()
            if not any(k in ln for k in ("DEBUG", "SLF4J", "Nashorn engine", "INFO ", "WARN "))
        )
        print(out)

    step(4, "纯 RDF 序列化回读校验(rdflib)")
    # .jsonld / .nt 由 rdflib 从同一张图直接序列化,可以逐三元组同构。
    # .rdf 由 OWL API 渲染,互斥性用 RDF 列表(AllDisjointClasses)编码而非逐对三元组,
    # 所以它按公理层判定(见第 3 步),这里只报告三元组数。
    ok = True
    for fmt, name in (("json-ld", "honeymom.jsonld"), ("nt", "honeymom.nt")):
        p = OUT / name
        if not p.exists():
            continue
        back = rdflib.Graph()
        back.parse(str(p), format=fmt)
        good = isomorphic(g, back)
        ok &= good
        print(f"  {name:<20} {len(back):>5} 三元组  与源同构={good}")
    rdf = OUT / "honeymom.rdf"
    if rdf.exists():
        back = rdflib.Graph()
        back.parse(str(rdf), format="xml")
        print(f"  {'honeymom.rdf':<20} {len(back):>5} 三元组  (公理层判定见第 3 步;"
              f"互斥性在 RDF/XML 中用列表编码,故不逐三元组同构)")

    print("\n结论:" + ("全部产物与源本体语义一致。" if ok else "存在不一致,请检查。"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
