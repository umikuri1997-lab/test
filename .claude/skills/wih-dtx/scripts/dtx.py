#!/usr/bin/env python3
"""Walk in home 共有ファイル (DTX Version 918) の読み書き。

  python3 dtx.py summary  FILE.dtx            セクションごとの件数と主な中身
  python3 dtx.py check    FILE.dtx            ヘッダ件数・行数の整合チェック
  python3 dtx.py diff     A.dtx B.dtx         セクション単位の差分
  python3 dtx.py extract  FILE.dtx > plan.json  対応セクションを plan JSON に変換
  python3 dtx.py build    plan.json OUT.dtx   plan JSON から DTX を作る

標準ライブラリのみ。ひな形は ../templates.json。
"""
import difflib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = "    0    0    0 "          # レコード区切り行(末尾スペースあり)
ENC = "cp932"

# TATE のヘッダ行数は「実際の行数 − 件数」で数える(見本どおり)
COUNT_MINUS_RECS = {"TATE"}


# ---------------------------------------------------------------- 入出力 ----
def read(path):
    text = open(path, encoding=ENC, newline="").read()
    lines = text.split("\r\n")
    head, secs, cur = [], [], None
    for ln in lines:
        m = re.match(r"^\[(\w{4})\]\s*(\d+)\s+(\d+)", ln)
        if m:
            cur = [m.group(1), ln[ln.index("\\"):], int(m.group(2)), int(m.group(3)), []]
            secs.append(cur)
        elif cur is None:
            head.append(ln)
        else:
            cur[4].append(ln)
    # 末尾の EOF と空行は最後のセクションから外す
    if secs and secs[-1][4][-2:] == ["EOF", ""]:
        secs[-1][4] = secs[-1][4][:-2]
    return head, secs


def write(path, head, secs):
    out = list(head)
    for name, tail, c, t, body in secs:
        out.append(f"[{name}]{c:5d}{t:5d}      {tail}")
        out += body
    out.append("EOF")
    with open(path, "w", encoding=ENC, newline="") as fp:
        fp.write("\r\n".join(out) + "\r\n")


def records(body):
    out, cur = [], None
    for ln in body:
        if ln == SEP:
            cur = [ln]
            out.append(cur)
        elif cur is not None:
            cur.append(ln)
    return out


def section(recs, name):
    body = [ln for r in recs for ln in r]
    t = len(body) - (len(recs) if name in COUNT_MINUS_RECS else 0)
    return len(recs), t, body


# ---------------------------------------------------------------- 書式 ------
def f(v):
    return f"{float(v):10.2f}"


def ints(vals):
    return "".join(f"{int(v):5d}" for v in vals)


def pt(p):
    return f(p[0]) + f(p[1])


def nums(line):
    return [float(v) for v in line.split()]


def set_ints(line, **idx):
    v = [int(x) for x in line.split()]
    for k, val in idx.items():
        v[int(k[1:])] = val
    return ints(v)


def set_floats(line, **idx):
    v = nums(line)
    for k, val in idx.items():
        v[int(k[1:])] = val
    return "".join(f(x) for x in v)


# ---------------------------------------------------------------- 生成 ------
def ccw(pts):
    """多角形の点を反時計回り(Y 上向き)にそろえる。始点は変えない。
    Walk in home は時計回りの部屋・畳・部分床・階段などを正しく扱えない。"""
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
            for i in range(len(pts)))
    return list(pts) if a >= 0 else [pts[0]] + list(reversed(pts[1:]))


def load_templates():
    return json.load(open(os.path.join(HERE, "..", "templates.json"), encoding="utf-8"))


# 部屋の種類コード
ROOM_CODES = {"玄関": 1, "廊下": 2, "和室": 3, "洋室": 4, "浴室": 6, "洗面": 7, "トイレ": 8, "収納": 13}


def build_room(r):
    """r: floor, name, code, points, label('tatami'|'none'|'blank'), living(bool), level, ceiling, extra"""
    pts = ccw(r["points"])
    level = r.get("level", -180.0 if r["code"] == 1 else 0.0)
    ceil = r.get("ceiling", 2400.0)
    p4 = r.get("p4", 0.0 if r["code"] in (1, 6) else 60.0)
    p5 = r.get("p5", 5.0 if r["code"] == 6 else 0.0)
    label = {"tatami": "（&J 帖）", "none": "なし", "blank": ""}[r.get("label", "blank")]
    return ([SEP, ints([r.get("floor", 1), len(pts), r["code"], 0, 0, 0, 1, 0]),
             f(level) + f(ceil) + f(0) + f(p4) + f(p5),
             r.get("name", "なし"), label]
            + [pt(p) for p in pts]
            + [f(level if r["code"] == 1 else 0) + f(ceil), "    0    0", f(0) + f(0), "    1    1", "",
               "    0", f"{2 if r.get('living') else 3:5d}", ""])


def build_wall(w, T):
    kind = w.get("kind", "normal")
    key = ("normal_out" if w.get("exterior") else "normal_in") if kind == "normal" else kind
    r = list(T["wall"][key])
    r[1] = set_ints(r[1], i0=w.get("floor", 1))
    if kind == "hang" and "bottom" in w:      # 下がり壁: 壁の下端高さ
        r[2] = set_floats(r[2], i0=w["bottom"])
    if kind == "waist" and "height" in w:     # 腰壁: 壁の高さ
        r[2] = set_floats(r[2], i1=w["height"])
    r[4] = pt(w["p1"]) + pt(w["p2"])
    return r


TATE_DEFAULT_NAME = {
    "window_slide": "引違い窓", "window_vert": "縦滑り出し", "window_bay": "引違い窓(2枚)",
    "door_ext": "片開きﾄﾞｱ", "door_in": "片開きﾄﾞｱ", "fusuma": "引違い戸(2枚)",
    "sliding_in": "引違い戸(2枚)", "opening_frame": "開口枠", "door_side": "片開きﾄﾞｱ(片袖)",
    "combo_fix": "FIX窓", "combo_vert": "縦滑り出し",
}


def build_tate(o, T, number):
    r = list(T["tate"][o["kind"]])
    r[1] = set_ints(r[1], i0=o.get("floor", 1), i2=o.get("hinge", int(r[1].split()[2])))
    r[2] = set_floats(r[2], i0=o["top"], i1=o["height"], **({"i2": o["depth"]} if "depth" in o else {}))
    r[3] = set_floats(r[3], i0=o["width"])
    r[4] = o.get("name", TATE_DEFAULT_NAME[o["kind"]])
    r[6] = pt(o["p1"]) + pt(o["p2"]) + f(0) + f(0)
    if number is not None:
        r[12] = set_ints(r[12], i4=number)
    if o.get("spec"):                       # 仕様メモ(玄関ﾄﾞｱ・型板・透明 など)
        r[20] = o["spec"]
    if o["kind"] in ("combo_fix", "combo_vert") and "combo" in o:   # 連窓: 全体の範囲
        c = o["combo"]
        r[47] = pt(c["p1"]) + pt(c["p2"]) + f(c["top"]) + f(c["width"] if o["kind"] == "combo_fix" else 0) + f(0)
    for i, line in o.get("raw", {}).items():  # 上記以外の行をそのまま指定(抽出時の差分保存用)
        r[int(i)] = line
    return r


def build_dim(dm, T):
    r = list(T["dim"])
    r[1] = ints([dm.get("floor", 1), 1, 0, 0, 0, dm["side"]])
    r[2] = pt(dm["p1"]) + pt(dm["p2"]) + pt(dm["p3"])
    return r


def build_simple(key, T, floor, pts=None, line=None):
    r = list(T[key])
    head = r[1].split()
    head[0] = str(floor)
    r[1] = ints(head) if key != "kcut" else f"{floor:5d}"
    return r


def build(plan):
    T = load_templates()
    head = T["skel"]["head"]
    secs = [list(s) for s in T["skel"]["sections"]]
    data = {}
    data["BUKN"] = [[ints([3, 1]), "PLANS-x-x", plan.get("name", "")] + [""] * 9]
    data["HEYA"] = [build_room(r) for r in plan.get("rooms", [])]
    data["KABE"] = [build_wall(w, T["tpl"]) for w in plan.get("walls", [])]
    # 建具番号: 記号(AW/AD/WD/WF)ごとに出現順で 1, 2, 3 …
    counters, tate, last_combo = {}, [], 0
    for o in plan.get("fittings", []):
        sym = T["tpl"]["tate"][o["kind"]][13]
        if o.get("number") is not None:
            num = o["number"]
        elif o["kind"] == "combo_vert":              # 連窓の 2 枚目は FIX と同じ番号のマイナス
            num = -last_combo
        else:
            counters[sym] = counters.get(sym, 0) + 1
            num = counters[sym]
        if o["kind"] == "combo_fix":
            last_combo = abs(num)
        tate.append(build_tate(o, T["tpl"], num))
    data["TATE"] = tate
    data["SUNP"] = [build_dim(dm, T["tpl"]) for dm in plan.get("dims", [])]
    data["GAIS"] = [[SEP, ints([g.get("floor", 1), len(g["points"])])] + [pt(p) for p in ccw(g["points"])]
                    for g in plan.get("outlines", [])]
    porc = []
    for q in plan.get("porches", []):
        r = list(T["tpl"]["porc"])
        r[1] = ints([q.get("floor", 1), len(q["points"]), q.get("type", 2), 1, 1, 0])
        r[2] = set_floats(r[2], i1=q.get("height", 150))
        porc.append(r[:3] + [pt(p) for p in ccw(q["points"])] + r[-2:])
    data["PORC"] = porc
    tata = []
    for t in plan.get("tatami", []):
        r = list(T["tpl"]["tata"])
        r[1] = ints([t.get("floor", 1), len(t["points"])] + [int(v) for v in r[1].split()[2:]])
        tata.append(r[:2] + [pt(p) for p in ccw(t["points"])] + [r[-1]])
    data["TATA"] = tata
    zdem = []
    for z in plan.get("bay_windows", []):
        r = list(T["tpl"]["zdem"])
        r[1] = set_ints(r[1], i0=z.get("floor", 1))
        r[2] = set_floats(r[2], i0=z["top"], i1=z["height"], i2=z["depth"])
        r[3] = pt(z["p1"]) + pt(z["p2"]) + f(0) + f(0)
        zdem.append(r)
    data["ZDEM"] = zdem
    agar = []
    for a in plan.get("agari", []):
        r = list(T["tpl"]["agar"])
        r[1] = set_ints(r[1], i0=a.get("floor", 1))
        r[2] = pt(a["p1"]) + pt(a["p2"]) + f(0)
        agar.append(r)
    data["AGAR"] = agar
    kaid = []
    for k in plan.get("stairs", []):
        r = list(T["tpl"]["kaid"])
        r[1] = set_ints(r[1], i0=k.get("floor", 1))
        r[3] = ints([1, k.get("steps", 11), len(k["points"]), 0, 0])
        r = r[:4] + [pt(p) for p in ccw(k["points"])] + r[8:]
        kaid.append(r)
    data["KAID"] = kaid
    data["KCUT"] = [[SEP, f"{c.get('floor', 1):5d}", pt(c["p1"]) + pt(c["p2"])] for c in plan.get("stair_cuts", [])]
    byuk = []
    for b in plan.get("floor_parts", []):
        r = list(T["tpl"]["byuk"])
        r[1] = set_ints(r[1], i0=b.get("floor", 1), i1=len(b["points"]))
        r[2] = set_floats(r[2], i0=b.get("level", -200))
        r = r[:3] + [pt(p) for p in ccw(b["points"])] + r[-2:]
        byuk.append(r)
    data["BYUK"] = byuk

    for s in secs:
        if s[0] in data:
            s[2], s[3], s[4] = section(data[s[0]], s[0])
    return head, secs


# ---------------------------------------------------------------- 抽出 ------
def extract(path):
    """DTX から plan JSON を作る(build と往復できる範囲)。"""
    T = load_templates()["tpl"]
    _, secs = read(path)
    d = {s[0]: s for s in secs}
    R = lambda n: records(d[n][4]) if n in d else []
    plan = {"name": d["BUKN"][4][2] if "BUKN" in d else ""}
    rooms = []
    for r in R("HEYA"):
        h = [int(v) for v in r[1].split()]
        n = h[1]
        v3 = nums(r[2])
        lbl = {"（&J 帖）": "tatami", "なし": "none"}.get(r[4], "blank")
        rooms.append({"floor": h[0], "name": r[3], "code": h[2], "label": lbl,
                      "living": r[-2].strip() == "2", "level": v3[0], "ceiling": v3[1],
                      "p4": v3[3], "p5": v3[4],
                      "points": [nums(x) for x in r[5:5 + n]]})
    plan["rooms"] = rooms
    walls = []
    for r in R("KABE"):
        h = r[1].split()
        kind = {"1": "normal", "2": "hang", "3": "waist"}[h[1]]
        v = nums(r[4])
        w = {"floor": int(h[0]), "kind": kind, "p1": v[:2], "p2": v[2:]}
        if kind == "normal":
            w["exterior"] = "24.00" in r[3]
        if kind == "hang":
            w["bottom"] = nums(r[2])[0]
        if kind == "waist":
            w["height"] = nums(r[2])[1]
        walls.append(w)
    plan["walls"] = walls
    by_code = {}
    for k, t in T["tate"].items():
        by_code.setdefault((t[1].split()[1], len(t)), k)
    fits = []
    for r in R("TATE"):
        h = r[1].split()
        kind = by_code.get((h[1], len(r)))
        if kind is None:
            print(f"warning: 未対応の建具コード {h[1]} ({r[4]}) は飛ばします", file=sys.stderr)
            continue
        v2, v3, v6 = nums(r[2]), nums(r[3]), nums(r[6])
        o = {"floor": int(h[0]), "kind": kind, "name": r[4], "hinge": int(h[2]),
             "top": v2[0], "height": v2[1], "width": v3[0], "p1": v6[:2], "p2": v6[2:4],
             "number": int(r[12].split()[4])}
        if v2[2]:
            o["depth"] = v2[2]
        if len(r) > 20 and r[20]:
            o["spec"] = r[20]
        if kind in ("combo_fix", "combo_vert"):
            v = nums(r[47])
            o["combo"] = {"p1": v[0:2], "p2": v[2:4], "top": v[4], "width": v[5]}
        built = build_tate(o, {"tate": T["tate"]}, o["number"])
        raw = {str(i): r[i] for i in range(len(r)) if built[i] != r[i]}
        if raw:
            o["raw"] = raw
        fits.append(o)
    plan["fittings"] = fits
    plan["dims"] = [{"floor": int(r[1].split()[0]), "side": int(r[1].split()[5]),
                     "p1": nums(r[2])[0:2], "p2": nums(r[2])[2:4], "p3": nums(r[2])[4:6]} for r in R("SUNP")]
    plan["outlines"] = [{"floor": int(r[1].split()[0]), "points": [nums(x) for x in r[2:]]} for r in R("GAIS")]
    plan["tatami"] = [{"floor": int(r[1].split()[0]), "points": [nums(x) for x in r[2:-1]]} for r in R("TATA")]
    plan["bay_windows"] = [{"floor": int(r[1].split()[0]), "top": nums(r[2])[0], "height": nums(r[2])[1],
                            "depth": nums(r[2])[2], "p1": nums(r[3])[0:2], "p2": nums(r[3])[2:4]} for r in R("ZDEM")]
    plan["agari"] = [{"floor": int(r[1].split()[0]), "p1": nums(r[2])[0:2], "p2": nums(r[2])[2:4]} for r in R("AGAR")]
    plan["stairs"] = [{"floor": int(r[1].split()[0]), "steps": int(r[3].split()[1]),
                       "points": [nums(x) for x in r[4:4 + int(r[3].split()[2])]]} for r in R("KAID")]
    plan["stair_cuts"] = [{"floor": int(r[1]), "p1": nums(r[2])[0:2], "p2": nums(r[2])[2:4]} for r in R("KCUT")]
    plan["porches"] = [{"floor": int(r[1].split()[0]), "type": int(r[1].split()[2]), "height": nums(r[2])[1],
                        "points": [nums(x) for x in r[3:3 + int(r[1].split()[1])]]} for r in R("PORC")]
    plan["floor_parts"] = [{"floor": int(r[1].split()[0]), "level": nums(r[2])[0],
                            "points": [nums(x) for x in r[3:3 + int(r[1].split()[1])]]} for r in R("BYUK")]
    return plan


# ---------------------------------------------------------------- 確認 ------
def check(path):
    _, secs = read(path)
    ok = True
    for name, _, c, t, body in secs:
        rs = records(body)
        if rs and c != len(rs):
            print(f"[{name}] 件数 {c} だが実レコード {len(rs)}")
            ok = False
        if body and rs:
            want = len(body) - (len(rs) if name in COUNT_MINUS_RECS else 0)
            if name not in ("HASR", "BKAB") and t != want:
                print(f"[{name}] 行数 {t} だが実際は {want}")
                ok = False
    print("OK" if ok else "NG")
    return ok


def summary(path):
    _, secs = read(path)
    for name, tail, c, t, body in secs:
        if c or body:
            print(f"{name} {tail.split()[1]:<12} {c:4d} 件")
    d = {s[0]: s for s in secs}
    if "HEYA" in d:
        print("部屋:", ", ".join(r[3] for r in records(d["HEYA"][4])))
    if "TATE" in d:
        print("建具:", ", ".join(f"{r[13]}{r[12].split()[4]} {r[4]}" for r in records(d["TATE"][4])))


def diff(a, b):
    _, sa = read(a)
    _, sb = read(b)
    da = {s[0]: s for s in sa}
    for name, _, c, t, body in sb:
        A = da.get(name)
        if A is None or A[4] != body:
            print(f"== [{name}] {A[2] if A else '-'} -> {c} 件")
            for ln in list(difflib.unified_diff(A[4] if A else [], body, lineterm="", n=0))[2:60]:
                print(ln)


def main():
    cmd, *args = sys.argv[1:] or ["-h"]
    if cmd == "summary":
        summary(args[0])
    elif cmd == "check":
        sys.exit(0 if check(args[0]) else 1)
    elif cmd == "diff":
        diff(args[0], args[1])
    elif cmd == "extract":
        json.dump(extract(args[0]), sys.stdout, ensure_ascii=False, indent=1)
    elif cmd == "build":
        plan = json.load(open(args[0], encoding="utf-8"))
        write(args[1], *build(plan))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
