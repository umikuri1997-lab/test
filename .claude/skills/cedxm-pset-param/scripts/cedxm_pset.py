#!/usr/bin/env python3
"""Cedxm_Pset_param の生成・検証（仕様書 2026-03-06 版）。"""
import argparse
import json
import re
import sys
import uuid

PSET = "Cedxm_Pset_param"

SYURUI = {
    "kuda", "tooshi", "han", "kaidan", "porch", "turizuka", "jizuka", "yukazuka", "koyazuka",
    "dodai", "oobiki", "hiuchi", "hari", "moya", "munagi", "sumiki", "taniki", "nobori",
    "mabasira", "sujikai", "madodai", "madomagusa", "neda", "taruki", "hafu", "hanakakushi",
    "hirokomai", "noboriyodo",
}
HORIZONTAL_END = {
    "ari", "gyakuari", "yoseari", "ooire", "oobiki", "ketasasi", "dousasi", "makurasasi",
    "aritugiosu", "aritugimesu", "kamatugiosu", "kamatugimesu", "okkakeosu", "okkakemesu",
    "daimotiosu", "daimotimesu", "katto",
}
COLUMN_END = {"hirahozo", "yosehozo", "kakuhozo", "katto"}

NUM = re.compile(r"^[+-]?\d+(\.\d+)?$")
POS = re.compile(r"^\d+(\.\d+)?$")

# 名前: (IFC 型, 許容値 set / 正規表現 / None)
SPEC = {
    "mokuzai": ("IFCBOOLEAN", None),
    "syurui": ("IFCLABEL", SYURUI),
    "jyusyu": ("IFCTEXT", None),
    "toukyuu": ("IFCTEXT", None),
    "kesyou": ("IFCBOOLEAN", None),
    "siten_keijyou": ("IFCLABEL", HORIZONTAL_END),
    "syuuten_keijyou": ("IFCLABEL", HORIZONTAL_END),
    "joutan_keijyou": ("IFCLABEL", COLUMN_END),
    "katan_keijyou": ("IFCLABEL", COLUMN_END),
    "w": ("IFCTEXT", POS),
    "h": ("IFCTEXT", POS),
    "hasira_w1": ("IFCTEXT", POS),
    "hasira_w2": ("IFCTEXT", POS),
    "sinzure": ("IFCTEXT", NUM),
    "hasira_sinzure_x": ("IFCTEXT", NUM),
    "hasira_sinzure_y": ("IFCTEXT", NUM),
}
# 仕様書本文の誤記
ALIASES = {"sitan_keijyou": "siten_keijyou", "jyoutan_keijyou": "joutan_keijyou"}


def validate(name, ifc_type, value):
    """問題があればメッセージのリストを返す。"""
    if name in ALIASES:
        return [f"{name}: 仕様書本文の誤記と思われる名前。'{ALIASES[name]}' を使う"]
    if name not in SPEC:
        return [f"{name}: 仕様にないプロパティ（警告）"]
    want, allowed = SPEC[name]
    errs = []
    if ifc_type != want:
        errs.append(f"{name}: 型は {want}（実際 {ifc_type}）")
    if want == "IFCBOOLEAN":
        if value not in (".T.", ".F."):
            errs.append(f"{name}: 値は .T. か .F.（実際 {value}）")
    elif isinstance(allowed, set) and value not in allowed:
        errs.append(f"{name}: 許容外の値 '{value}'")
    elif isinstance(allowed, re.Pattern) and not allowed.match(value):
        errs.append(f"{name}: 半角数字ではない '{value}'")
    return errs


def ifc_guid():
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
    n = uuid.uuid4().int
    out = [chars[(n >> 126) & 0x3]]
    for i in range(21):
        out.append(chars[(n >> (120 - 6 * i)) & 0x3F])
    return "".join(out)


def to_ifc_value(name, v):
    want = SPEC[name][0] if name in SPEC else "IFCTEXT"
    if want == "IFCBOOLEAN":
        if isinstance(v, str):
            v = v.strip().lower() in ("true", ".t.", "t", "1")
        return want, ".T." if v else ".F."
    s = str(v)
    if isinstance(v, float) and v.is_integer():
        s = str(int(v))
    return want, s


def cmd_gen(a):
    data = json.load(open(a.input, encoding="utf-8"))
    n = a.start
    lines, refs, errs = [], [], []
    for name, v in data.items():
        t, val = to_ifc_value(name, v)
        errs += validate(name, t, val)
        arg = f"{t}({val})" if t == "IFCBOOLEAN" else f"{t}('{val}')"
        lines.append(f"#{n}=IFCPROPERTYSINGLEVALUE('{name}',$,{arg},$);")
        refs.append(f"#{n}")
        n += 1
    pset_id, rel_id = n, n + 1
    lines.append(f"#{pset_id}=IFCPROPERTYSET('{ifc_guid()}',$,'{PSET}',$,({','.join(refs)}));")
    if a.targets:
        tg = ",".join(f"#{t.strip().lstrip('#')}" for t in a.targets.split(","))
        lines.append(f"#{rel_id}=IFCRELDEFINESBYPROPERTIES('{ifc_guid()}',$,'{PSET}',$,({tg}),#{pset_id});")
    for e in errs:
        print("ERROR:", e, file=sys.stderr)
    print("\n".join(lines))
    return 1 if any("警告" not in e for e in errs) else 0


ENTITY = re.compile(r"#(\d+)\s*=\s*(\w+)\s*\((.*)\);\s*$")
SINGLE = re.compile(r"^'([^']*)'\s*,\s*[^,]*,\s*(\w+)\s*\(\s*'?(.*?)'?\s*\)\s*,")


def cmd_check(a):
    text = open(a.ifc, encoding="utf-8", errors="replace").read()
    ents = {}
    for stmt in re.split(r";\s*\n", text):
        m = ENTITY.match(stmt.strip() + ";")
        if m:
            ents[m.group(1)] = (m.group(2).upper(), m.group(3))
    found, problems = 0, []
    for eid, (typ, body) in ents.items():
        if typ != "IFCPROPERTYSET" or f"'{PSET}'" not in body:
            continue
        found += 1
        for ref in re.findall(r"#(\d+)", body.split("(", 1)[-1]):
            if ref not in ents or ents[ref][0] != "IFCPROPERTYSINGLEVALUE":
                problems.append(f"#{eid}: #{ref} が IFCPROPERTYSINGLEVALUE ではない")
                continue
            m = SINGLE.match(ents[ref][1])
            if not m:
                problems.append(f"#{ref}: 解析できない")
                continue
            for e in validate(m.group(1), m.group(2).upper(), m.group(3)):
                problems.append(f"#{eid}/#{ref} {e}")
    print(f"{PSET}: {found} 件")
    for p in problems:
        print(p)
    return 1 if any("警告" not in p for p in problems) else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen", help="JSON から IFC 行を生成")
    g.add_argument("input")
    g.add_argument("--start", type=int, default=9000, help="最初の行番号")
    g.add_argument("--targets", help="適用先の要素番号（カンマ区切り）")
    c = sub.add_parser("check", help="IFC 内の Cedxm_Pset_param を検証")
    c.add_argument("ifc")
    a = ap.parse_args()
    sys.exit(cmd_gen(a) if a.cmd == "gen" else cmd_check(a))


if __name__ == "__main__":
    main()
