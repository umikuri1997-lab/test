# 同じ 1 階データを Walk in home 共有ファイル (DTX Version 918) で出力する。
# 仕様書がないため、Walk in home 2024 が出力した見本 DTX から作ったひな形 (dtx_template.json) の
# レコードをコピーし、座標・名称・寸法だけを差し替える。
#   座標: 見本に合わせて上端 Y=0、下へマイナス。
import json

import make_cedxm as m

D, W = m.D, m.W
T = json.load(open("dtx_template.json", encoding="utf-8"))
tpl = T["tpl"]


def f(v):
    return f"{v:10.2f}"


def xy(x, y):
    return f(x) + f(y - D)


def ints(vals):
    return "".join(f"{v:5d}" for v in vals)


# ---- 部屋 -------------------------------------------------------------------
# 種類コード(見本より: 1=玄関・土間 2=廊下 4=洋室 6=浴室 7=洗面 8=トイレ 13=収納。3=和室は推定)
ROOM = {
    "食堂・居間": (4, "4"), "台所": (4, "4"), "ホール": (4, "4n"), "和室": (3, "4"),
    "階段": (2, "2"), "廊下": (2, "2"), "勝手口": (2, "2"),
    "玄関": (1, "1"), "下足入": (1, "1"),
    "収納": (13, "13"), "物入": (13, "13"),
    "洗面": (7, "7"), "便所": (8, "8"), "浴室": (6, "6"),
}


def room_rec(name, poly):
    code, key = ROOM[name]
    t = tpl["room"][key]
    h2 = t[1].split()
    h2[0], h2[1], h2[2] = "1", str(len(poly)), str(code)
    return ([t[0], ints(map(int, h2)), t[2], name, t[4]]
            + [xy(x, y) for x, y in poly] + t[9:])   # 見本は 4 点: 先頭 5 行 + 点 4 行 + 残り


# ---- 壁 ---------------------------------------------------------------------
outer = {((0, 0), (W, 0)), ((W, 0), (W, D)), ((W, D), (0, D)), ((0, D), (0, 0))}


def on_outer(a, b):
    for (p, q) in outer:
        if (p[0] == q[0] == a[0] == b[0]) or (p[1] == q[1] == a[1] == b[1]):
            return True
    return False


def wall_rec(a, b):
    t = tpl["wall_out"] if on_outer(a, b) else tpl["wall_in"]
    return t[:4] + [xy(*a) + xy(*b)] + t[5:]


# ---- 建具 -------------------------------------------------------------------
def tate_rec(kind, name, a, b, ow, oh, top):
    ext = on_outer(a, b)
    if kind == 1:
        if name == "縦すべり窓":
            t, nm, code = tpl["win_vert"], "縦滑り出し", 13
        else:                       # 引違い窓・掃出し窓・出窓
            t, nm, code = tpl["win_slide"], "引違い窓", 1
    elif name == "引違い戸(2枚)":
        t, nm, code = tpl["sliding2"], "引違い戸(2枚)", 101
    else:                           # 片開きドア・玄関ドア・折戸
        t, nm, code = (tpl["door_out"] if ext else tpl["door_in"]), "片開きﾄﾞｱ", 104
    r = list(t)
    h2 = [int(v) for v in r[1].split()]
    h2[1] = code
    r[1] = ints(h2)
    v3 = r[2].split()
    v3[0], v3[1] = f"{top:.2f}", f"{oh:.2f}"
    r[2] = "".join(f"{float(v):10.2f}" for v in v3)
    v4 = r[3].split()
    v4[0] = f"{ow:.2f}"
    r[3] = "".join(f"{float(v):10.2f}" for v in v4)
    r[4], r[5] = nm, ""
    r[6] = xy(*a) + xy(*b) + f(0) + f(0)
    return r


# ---- 寸法線 -----------------------------------------------------------------
def dim_rec(p1, p2, p3, side):
    t = tpl["dim"]
    return [t[0], ints([1, 1, 0, 0, 0, side]), xy(*p1) + xy(*p2) + xy(*p3)] + t[3:]


dims = []


def chain(cuts, edge):
    """edge: bottom/top/left/right。区切り寸法(1365 外)と全体寸法(1820 外)。"""
    cuts = sorted(cuts)
    segs = list(zip(cuts, cuts[1:])) + [(cuts[0], cuts[-1])]
    for i, (a, b) in enumerate(segs):
        off = 1820 if i == len(segs) - 1 else 1365
        if edge == "bottom":
            dims.append(dim_rec((b, 0), (a, 0), (a, -off), -1))
        elif edge == "top":
            dims.append(dim_rec((b, D), (a, D), (a, D + off), 1))
        elif edge == "right":
            dims.append(dim_rec((W, b), (W, a), (W + off, a), -1))
        else:
            dims.append(dim_rec((0, b), (0, a), (-off, a), 1))


chain([0, m.p(4), m.p(7), W], "bottom")
chain([0, m.p(3), m.p(7), m.p(9), W], "top")
chain([0, 910, 3640, 5460, D], "left")
chain([0, 3640, 4550, 5915, D], "right")

# ---- 組み立て ---------------------------------------------------------------
data = {
    "BUKN": [[ints([3, 1]), "PLANS-x-x", "1階平面図"] + [""] * 9],
    "HEYA": [room_rec(n, p) for n, p in m.rooms],
    "KABE": [wall_rec(a, b) for a, b in m.walls],
    "TATE": [tate_rec(k, n, a, b, ow, oh, top) for _, k, n, a, b, ow, oh, top in m.openings],
    "SUNP": dims,
    "GAIS": [["    0    0    0 ", ints([1, 4])] + [xy(*q) for q in [(W, 0), (W, D), (0, D), (0, 0)]]],
}

out = list(T["skel"]["head"])
for name, tail, c, t, body in T["skel"]["sections"]:
    if name in data:
        recs = data[name]
        body = [line for r in recs for line in r]
        c = len(recs)
        t = len(body) - (c if name == "TATE" else 0)   # 見本の TATE は件数分少なく数える
    out.append(f"[{name}]{c:5d}{t:5d}      {tail}")
    out += body
out.append("EOF")

with open("1F.dtx", "w", encoding="cp932", newline="") as fp:
    fp.write("\r\n".join(out) + "\r\n")
