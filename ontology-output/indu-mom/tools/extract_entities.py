#!/usr/bin/env python3
"""从 HoneyMOM 的 schema*.py 静态抽取实体模型(JSON)。

不导入应用(避免依赖 sqlalchemy/运行时),直接用 ast 解析源码里的
E(...) / F(...) 定义,并合并各模块 extend() 里追加的字段与子表。

用法:
    python tools/extract_entities.py            # 打印 JSON
    python tools/extract_entities.py --summary  # 打印人类可读摘要
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO / "honeymom"
FILES = ["schema.py", "schema_exec.py", "schema_factory.py", "schema_impl.py", "schema_erp.py"]

FIELD_HELPERS = {"S", "T", "I", "N", "B", "D", "DT", "EN", "R", "J", "CODE", "NAME"}


def lit(node):
    """取字面量;_tr('x') 之类的包装取内层字符串。"""
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Call):
        for a in node.args:
            v = lit(a)
            if isinstance(v, str):
                return v
        return None
    return None


def enum_dict(node):
    """EN(..., {...}) 的取值字典。"""
    if isinstance(node, ast.Dict):
        return {lit(k): lit(v) for k, v in zip(node.keys, node.values)}
    return None


def parse_field(call):
    """解析一个字段调用,返回 dict 或 None。"""
    fn = call.func
    name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
    if name not in FIELD_HELPERS:
        return None
    f = {"fname": name}
    if name in ("CODE", "NAME"):
        # CODE(label, auto) / NAME(label) —— 固定字段名 code / name
        f["name"] = "code" if name == "CODE" else "name"
        f["label"] = lit(call.args[0]) if call.args else ("编码" if name == "CODE" else "名称")
        f["t"] = "str"
        if name == "CODE":
            for kw in call.keywords:
                if kw.arg == "auto":
                    f["auto"] = lit(kw.value)
        return f
    if len(call.args) < 2:
        return None
    f["name"] = lit(call.args[0])
    f["label"] = lit(call.args[1])
    f["t"] = {"S": "str", "T": "text", "I": "int", "N": "float", "B": "bool",
              "D": "date", "DT": "datetime", "EN": "enum", "R": "ref", "J": "json"}[name]
    if name == "R" and len(call.args) >= 3:
        f["ref"] = lit(call.args[2])
    if name == "EN" and len(call.args) >= 3:
        f["enum"] = enum_dict(call.args[2])
    for kw in call.keywords:
        if kw.arg == "req":
            f["req"] = bool(lit(kw.value))
        elif kw.arg == "unique":
            f["unique"] = bool(lit(kw.value))
        elif kw.arg == "ro":
            f["ro"] = bool(lit(kw.value))
        elif kw.arg == "hint":
            f["hint"] = lit(kw.value)
        elif kw.arg == "default":
            f["default"] = lit(kw.value)
    return f


def parse_entity(call):
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "E"):
        return None
    if len(call.args) < 4:
        return None
    ent = {
        "name": lit(call.args[0]),
        "label": lit(call.args[1]),
        "module": lit(call.args[2]),
        "fields": [],
        "children": [],
        "actions": {},
    }
    for f in call.args[3].elts:
        if isinstance(f, ast.Call):
            pf = parse_field(f)
            if pf:
                ent["fields"].append(pf)
    for kw in call.keywords:
        if kw.arg == "children" and isinstance(kw.value, ast.List):
            for c in kw.value.elts:
                if isinstance(c, ast.Tuple) and len(c.elts) >= 2:
                    ent["children"].append([lit(c.elts[0]), lit(c.elts[1])])
        elif kw.arg == "actions" and isinstance(kw.value, ast.Dict):
            ent["actions"] = {lit(k): lit(v) for k, v in zip(kw.value.keys, kw.value.values)}
        elif kw.arg in ("internal", "menu"):
            ent[kw.arg] = bool(lit(kw.value))
    return ent


def collect(tree):
    """返回该模块定义的实体列表,以及 extend() 里追加的字段/子表。"""
    entities, extra_fields, extra_children = [], {}, {}
    for node in ast.walk(tree):
        # 顶层 ENTITIES* = [ E(...) ]  (Assign 或 AnnAssign)
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            targets, value = [], None
        for tgt in targets:
            if isinstance(tgt, ast.Name) and tgt.id.startswith("ENTITIES") and value is not None:
                for el in getattr(value, "elts", []):
                    e = parse_entity(el)
                    if e:
                        entities.append(e)
        # extend() 里的 add('ent', F(...)) 与 by['x'].children.extend([...])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add":
            if node.args and isinstance(node.args[0], ast.Constant):
                ent = node.args[0].value
                for a in node.args[1:]:
                    if isinstance(a, ast.Call):
                        pf = parse_field(a)
                        if pf:
                            extra_fields.setdefault(ent, []).append(pf)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "extend":
            v = node.func.value
            if isinstance(v, ast.Subscript) and isinstance(v.slice, ast.Constant):
                ent = v.slice.value
                if isinstance(v.value, ast.Attribute) and v.value.attr == "children":
                    for a in node.args:
                        for el in getattr(a, "elts", []):
                            if isinstance(el, ast.Tuple) and len(el.elts) >= 2:
                                extra_children.setdefault(ent, []).append([lit(el.elts[0]), lit(el.elts[1])])
    return entities, extra_fields, extra_children


def main():
    entities, ef, ec = [], {}, {}
    for fn in FILES:
        p = SCHEMA_DIR / fn
        if not p.exists():
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        ents, xf, xc = collect(tree)
        for e in ents:
            e["source"] = fn
        entities.extend(ents)
        for k, v in xf.items():
            ef.setdefault(k, []).extend(v)
        for k, v in xc.items():
            ec.setdefault(k, []).extend(v)

    # 合并 extend() 追加的字段与子表
    by = {e["name"]: e for e in entities}
    for ent, fields in ef.items():
        if ent not in by:
            continue
        have = {f["name"] for f in by[ent]["fields"]}
        for f in fields:
            if f["name"] not in have:
                by[ent]["fields"].append(f)
                have.add(f["name"])
    for ent, ch in ec.items():
        if ent not in by:
            continue
        for c in ch:
            if c not in by[ent]["children"]:
                by[ent]["children"].append(c)

    # 去重 + 统计
    for e in entities:
        seen, uniq = set(), []
        for f in e["fields"]:
            if f["name"] and f["name"] not in seen:
                seen.add(f["name"])
                uniq.append(f)
        e["fields"] = uniq

    if "--fields" in sys.argv:
        names = set(sys.argv[sys.argv.index("--fields") + 1].split(","))
        for e in entities:
            if e["name"] not in names:
                continue
            print(f"== {e['name']} ({e['label']}) [{e['module']}]")
            for f in e["fields"]:
                extra = f" -> ref:{f['ref']}" if f.get("ref") else ""
                if f.get("enum"):
                    extra += " enum:" + str(list(f["enum"].values())[:10])
                if f.get("req"):
                    extra += " [req]"
                if f.get("ro"):
                    extra += " [ro]"
                print(f"   {f['name']:<16} {f['t']:<8} {f['label']}{extra}")
            print()
    elif "--summary" in sys.argv:
        mods = {}
        for e in entities:
            mods.setdefault(e["module"], []).append(e)
        for m, es in mods.items():
            print(f"\n=== {m} ({len(es)}) ===")
            for e in es:
                refs = [f"{f['name']}→{f['ref']}" for f in e["fields"] if f.get("ref")]
                print(f"  {e['name']:<22} {e['label']:<14} 链接: {', '.join(refs) or '-'}")
        print(f"\n总计 {len(entities)} 个实体, {sum(len(e['fields']) for e in entities)} 个字段")
    else:
        print(json.dumps(entities, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
