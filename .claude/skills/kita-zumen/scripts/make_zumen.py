#!/usr/bin/env python3
"""DTX (Walk in home) から喜多ハウジング仕様の平面図 (JWW) を仕上げる。

  python3 make_zumen.py IN.dtx OUT.jww [--name 工事名称] [--number 工事番号]
                        [--date 2026/10/03] [--floor 1] [--wall 160] [--preview OUT.svg]

図面枠 (../assets/kita_frame.jww) に次を書き込む。
  グループ1 プラン① (1/100) : 壁の輪郭線・建具・寸法線
  グループ9 プラン①【書き込み】: 壁のソリッド着色・部屋名・面積表・図面名称
  グループF 共通                : 工事名称・工事番号・設計年月日
"""
import argparse
import datetime
import math
import os
import sys

from shapely import constrained_delaunay_triangles
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "wih-dtx", "scripts"))
import dtx  # noqa: E402
import jww  # noqa: E402

FRAME = os.path.join(HERE, "..", "assets", "kita_frame.jww")
SCALE = 100.0                    # グループ1・9 の縮尺 (JWW の座標は図寸 mm = 実寸 / 縮尺)
AREA_CENTER = (-17.0, 8.0)       # 用紙(A3)上で図を置く中心。面積表・タイトル欄を避けた位置
JO = 1.6562                      # 1 帖 = 910 x 1820 mm

G_PLAN, G_NOTE, G_COMMON = 1, 9, 15
L_WALL, L_FIT, L_DIM = 1, 3, 13          # グループ1: 壁線・建具・寸法
L_WALLFILL, L_ROOM, L_TABLE = 6, 13, 0   # グループ9: 壁着色(凡例と同じ)・部屋名(書き込み)・面積表
WALL_RGB = 0xC0C0C0                      # 凡例「壁」の色

WINDOWS = {"window_slide", "window_vert", "window_bay"}
SWINGS = {"door_in", "door_ext", "door_side"}
SLIDES = {"sliding_in", "fusuma"}


def text_width(s, size):
    return size * sum(1.0 if ord(c) > 0xFF else 0.5 for c in s)


class Sheet:
    def __init__(self, j, center_real):
        self.j = j
        self.cx, self.cy = center_real

    def p(self, x, y):
        return ((x - self.cx) / SCALE + AREA_CENTER[0], (y - self.cy) / SCALE + AREA_CENTER[1])

    def line(self, a, b, layer, color=1, glayer=G_PLAN):
        (x1, y1), (x2, y2) = self.p(*a), self.p(*b)
        self.j.line(x1, y1, x2, y2, layer=layer, glayer=glayer, color=color)

    def text(self, x, y, s, size, layer, glayer, angle=0.0, center=False, right=False):
        w = text_width(s, size)
        if center:
            x -= w / 2
        elif right:
            x -= w
        self.j.text(x, y, s, size=size, angle=angle, kind=0, layer=layer, glayer=glayer, color=1)


# ---------------------------------------------------------------- 図形 -------
def outward(p1, p2, inside_poly):
    """p1→p2 の線分に対し、建物の外側を向く単位法線。"""
    L = math.dist(p1, p2)
    ux, uy = (p2[0] - p1[0]) / L, (p2[1] - p1[1]) / L
    nx, ny = -uy, ux
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    return (nx, ny) if not inside_poly.contains(Point(mx + nx * 50, my + ny * 50)) else (-nx, -ny)


def draw_bays(sh, bays, inside_poly):
    for z in bays:
        p1, p2, d = z["p1"], z["p2"], z["depth"]
        nx, ny = outward(p1, p2, inside_poly)
        q1, q2 = (p1[0] + nx * d, p1[1] + ny * d), (p2[0] + nx * d, p2[1] + ny * d)
        sh.line(p1, q1, L_WALL, color=2)
        sh.line(q2, p2, L_WALL, color=2)
        sh.line(q1, q2, L_WALL, color=2)


def wall_polygon(walls, fits, t):
    shapes = [LineString([w["p1"], w["p2"]]).buffer(t / 2, cap_style="square", join_style="mitre")
              for w in walls if w.get("kind", "normal") == "normal"]
    body = unary_union(shapes)
    holes = []
    for o in fits:
        a, b = o["p1"], o["p2"]
        L = math.dist(a, b)
        if L == 0:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        cxm, cym = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        half = min(L, o["width"] + 90) / 2
        seg = LineString([(cxm - ux * half, cym - uy * half), (cxm + ux * half, cym + uy * half)])
        holes.append(seg.buffer(t / 2 + 5, cap_style="flat"))
    return body.difference(unary_union(holes)) if holes else body


def polys(g):
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return [x for x in getattr(g, "geoms", []) if isinstance(x, Polygon)]


def draw_walls(sh, poly, ref_solid):
    for pg in polys(poly):
        for tri in constrained_delaunay_triangles(pg).geoms:
            c = list(tri.exterior.coords)[:3]
            p1, p2, p3 = (sh.p(*q) for q in c)
            e = jww.Ent("CDataSolid", layer=L_WALLFILL, glayer=G_NOTE, color=10, style=ref_solid.style,
                        width=ref_solid.width, flag=ref_solid.flag,
                        v=(p1[0], p1[1], p3[0], p3[1], p2[0], p2[1], p3[0], p3[1]), extra={"rgb": WALL_RGB})
            sh.j.ents.append(e)
        for ring in [pg.exterior, *pg.interiors]:
            cs = list(ring.coords)
            for a, b in zip(cs, cs[1:]):
                sh.line(a, b, L_WALL, color=2)


def draw_fitting(sh, o, t):
    a, b = o["p1"], o["p2"]
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -uy, ux
    cxm, cym = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    half = min(L, o["width"] + 90) / 2
    e1 = (cxm - ux * half, cym - uy * half)
    e2 = (cxm + ux * half, cym + uy * half)
    off = lambda q, d: (q[0] + nx * d, q[1] + ny * d)
    k = o["kind"]
    if k in WINDOWS:
        for d in (-t / 6, t / 6):
            sh.line(off(e1, d), off(e2, d), L_FIT)
        sh.line(off(e1, 0), off(e2, 0), L_FIT)
    elif k in SLIDES:
        ov = 40
        sh.line(off(e1, t / 8), off((cxm + ux * ov, cym + uy * ov), t / 8), L_FIT)
        sh.line(off((cxm - ux * ov, cym - uy * ov), -t / 8), off(e2, -t / 8), L_FIT)
    elif k in SWINGS:
        hinge, other = (e1, e2) if o.get("hinge", 1) >= 0 else (e2, e1)
        r = math.dist(hinge, other)
        s = 1 if k != "door_ext" else -1                      # 勝手口は外開き
        tip = (hinge[0] + nx * r * s, hinge[1] + ny * r * s)
        sh.line(hinge, tip, L_FIT)
        a_tip = math.atan2(tip[1] - hinge[1], tip[0] - hinge[0])
        a_oth = math.atan2(other[1] - hinge[1], other[0] - hinge[0])
        start, sweep = a_tip, (a_oth - a_tip) % (2 * math.pi)
        if sweep > math.pi:
            start, sweep = a_oth, 2 * math.pi - sweep
        hx, hy = sh.p(*hinge)
        sh.j.arc(hx, hy, r / SCALE, start, sweep, layer=L_FIT, glayer=G_PLAN, color=1)


def draw_dim(sh, dm):
    p1, p2, p3 = dm["p1"], dm["p2"], dm["p3"]
    horiz = abs(p1[1] - p2[1]) < 1e-6
    val = abs(p1[0] - p2[0]) if horiz else abs(p1[1] - p2[1])
    if val < 1:
        return
    if horiz:
        y = p3[1]
        a, b = (p1[0], y), (p2[0], y)
        for q in (p1, p2):
            sh.line(q, (q[0], y + math.copysign(150, y - q[1])), L_DIM)
    else:
        x = p3[0]
        a, b = (x, p1[1]), (x, p2[1])
        for q in (p1, p2):
            sh.line(q, (x + math.copysign(150, x - q[0]), q[1]), L_DIM)
    sh.line(a, b, L_DIM)
    for q in (a, b):                                           # 端部の斜線
        sh.line((q[0] - 60, q[1] - 60), (q[0] + 60, q[1] + 60), L_DIM)
    s = f"{val:,.0f}"
    mx, my = sh.p((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if horiz:
        sh.text(mx, my + 0.6, s, 3.0, L_DIM, G_PLAN, center=True)
    else:
        w = text_width(s, 3.0)
        sh.j.text(mx - 0.6, my - w / 2, s, size=3.0, angle=90.0, kind=0, layer=L_DIM, glayer=G_PLAN, color=1)


def draw_rooms(sh, rooms):
    for r in rooms:
        if r["name"] in ("なし", ""):
            continue
        pg = Polygon(r["points"])
        if not pg.is_valid or pg.area <= 0:
            continue
        c = pg.point_on_surface() if not pg.contains(pg.centroid) else pg.centroid
        x, y = sh.p(c.x, c.y)
        minx, miny, maxx, maxy = pg.bounds
        room_w = (maxx - minx) / SCALE * 0.85                   # 壁厚ぶん内側
        room_h = (maxy - miny) / SCALE * 0.85
        size = max(2.0, min(4.0, room_w / max(text_width(r["name"], 1.0), 0.5)))
        sub = f"({pg.area / 1e6 / JO:.1f}帖)"
        sub_size = max(2.0, min(3.0, room_w / text_width(sub, 1.0)))
        if r.get("label") == "tatami" and room_h > size + sub_size + 2:
            sh.text(x, y + 0.6, r["name"], size, L_ROOM, G_NOTE, center=True)
            sh.text(x, y - sub_size - 0.6, sub, sub_size, L_ROOM, G_NOTE, center=True)
        else:
            sh.text(x, y - size / 2, r["name"], size, L_ROOM, G_NOTE, center=True)


# ---------------------------------------------------------------- 書き込み ---
def find_text(j, glayer, text):
    return next((e for e in j.ents if e.cls == "CDataMoji" and e.glayer == glayer and e.extra["text"] == text), None)


def replace_text(e, s):
    if e is None:
        return
    e.extra["text"] = s
    e.v[2] = e.v[0] + text_width(s, e.v[5])


def floor_area(plan, floor):
    outs = [Polygon(g["points"]) for g in plan.get("outlines", []) if g["floor"] == floor]
    rooms = [Polygon(r["points"]).buffer(0) for r in plan.get("rooms", []) if r["floor"] == floor]
    if floor == 1 and outs:
        return unary_union(outs).area / 1e6
    return unary_union(rooms).area / 1e6 if rooms else 0.0


def fill_table(j, a1, a2):
    ref = find_text(j, G_NOTE, "1階床面積")
    rows = [(22.6, a1), (10.6, a2), (-13.4, a1 + a2)]
    for y, a in rows:
        if a <= 0:
            continue
        for x_unit, val in ((174.4, f"{a:.2f}"), (193.7, f"{a * 0.3025:.2f}")):
            w = text_width(val, 3.0)
            j.ents.append(jww.Ent("CDataMoji", layer=ref.layer, glayer=G_NOTE, color=ref.color, style=ref.style,
                                  flag=ref.flag, v=(x_unit - w, y, x_unit, y, 0, 3.0, 3.0, 0.0, 0.0),
                                  extra={"font": ref.extra["font"], "text": val}))


# ---------------------------------------------------------------- 本体 -------
def make(dtx_path, out, name=None, number=None, date=None, floor=1, wall=160.0, preview=None):
    plan = dtx.extract(dtx_path)
    j = jww.Jww(FRAME)
    walls = [w for w in plan["walls"] if w["floor"] == floor]
    fits = [o for o in plan["fittings"] if o["floor"] == floor]
    rooms = [r for r in plan["rooms"] if r["floor"] == floor]
    dims = [d for d in plan["dims"] if d["floor"] == floor]

    pts = [q for w in walls for q in (w["p1"], w["p2"])] + [d["p3"] for d in dims]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    sh = Sheet(j, ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))

    ref_solid = next(e for e in j.ents if e.cls == "CDataSolid" and e.glayer == G_NOTE and e.layer == L_WALLFILL
                     and e.extra.get("rgb") == WALL_RGB)
    bays = [z for z in plan.get("bay_windows", []) if z["floor"] == floor]
    cuts = fits + [{"p1": z["p1"], "p2": z["p2"], "width": math.dist(z["p1"], z["p2"]) - 90} for z in bays]
    inside = unary_union([Polygon(r["points"]).buffer(0) for r in rooms])
    draw_walls(sh, wall_polygon(walls, cuts, wall), ref_solid)
    draw_bays(sh, bays, inside)
    for o in fits:
        draw_fitting(sh, o, wall)
    for d in dims:
        draw_dim(sh, d)
    draw_rooms(sh, rooms)

    fill_table(j, floor_area(plan, 1), floor_area(plan, 2))
    replace_text(find_text(j, G_NOTE, "○○図1F"), f"{floor}階平面図")
    replace_text(find_text(j, G_COMMON, "喜多　太郎邸　改築工事"), name or plan.get("name") or "")
    if number:
        replace_text(find_text(j, G_COMMON, "0000000"), number)
    replace_text(find_text(j, G_COMMON, "2025/11/11"), date or datetime.date.today().strftime("%Y/%m/%d"))
    j.save(out)
    if preview:
        write_preview(j, preview, groups={G_PLAN, G_NOTE, G_COMMON})


def write_preview(j, path, groups):
    """表示グループ(1・9・F)の用紙範囲だけを SVG にする(確認用)。"""
    X0, X1, Y0, Y1 = -211, 211, -150, 150
    k = 3.0
    T = lambda x, y: ((x - X0) * k, (Y1 - y) * k)
    inside = lambda x, y: X0 <= x <= X1 and Y0 <= y <= Y1
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{(X1 - X0) * k:.0f}" height="{(Y1 - Y0) * k:.0f}" '
           f'style="background:#fff">']
    for e in j.ents:
        if e.glayer not in groups:
            continue
        if e.cls == "CDataSolid":
            v = e.v
            q = [(v[0], v[1]), (v[4], v[5]), (v[6], v[7]), (v[2], v[3])]
            if not any(inside(*p) for p in q):
                continue
            rgb = e.extra.get("rgb", 0xC0C0C0)
            col = f"#{rgb & 0xFF:02x}{(rgb >> 8) & 0xFF:02x}{(rgb >> 16) & 0xFF:02x}"
            out.append('<polygon fill="%s" points="%s"/>' % (col, " ".join("%.1f,%.1f" % T(*p) for p in q)))
    for e in j.ents:
        if e.glayer not in groups:
            continue
        if e.cls == "CDataSen" and (inside(e.v[0], e.v[1]) or inside(e.v[2], e.v[3])):
            (a, b), (c, d) = T(e.v[0], e.v[1]), T(e.v[2], e.v[3])
            out.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" stroke="#000" '
                       f'stroke-width="{0.9 if e.color == 2 else 0.4}"/>')
        elif e.cls == "CDataEnko" and inside(e.v[0], e.v[1]):
            cx, cy, r, st, sw = e.v[:5]
            if e.v[7]:
                a, b = T(cx, cy)
                out.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{r * k:.1f}" fill="none" stroke="#000" stroke-width="0.4"/>')
            else:
                p1 = T(cx + r * math.cos(st), cy + r * math.sin(st))
                p2 = T(cx + r * math.cos(st + sw), cy + r * math.sin(st + sw))
                large = 1 if sw > math.pi else 0
                out.append(f'<path d="M{p1[0]:.1f},{p1[1]:.1f} A{r * k:.1f},{r * k:.1f} 0 {large} 0 {p2[0]:.1f},{p2[1]:.1f}" '
                           f'fill="none" stroke="#000" stroke-width="0.4"/>')
        elif e.cls == "CDataMoji" and inside(e.v[0], e.v[1]):
            a, b = T(e.v[0], e.v[1])
            ang = -e.v[8]
            s = e.extra["text"].replace("&", "&amp;").replace("<", "&lt;")
            out.append(f'<text x="{a:.1f}" y="{b:.1f}" font-size="{e.v[6] * k:.1f}" '
                       f'transform="rotate({ang} {a:.1f} {b:.1f})" font-family="sans-serif">{s}</text>')
    out.append("</svg>")
    open(path, "w", encoding="utf-8").write("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dtx")
    ap.add_argument("out")
    ap.add_argument("--name", help="工事名称(省略時は DTX の物件名)")
    ap.add_argument("--number", help="工事番号")
    ap.add_argument("--date", help="設計年月日 YYYY/MM/DD(省略時は今日)")
    ap.add_argument("--floor", type=int, default=1)
    ap.add_argument("--wall", type=float, default=160.0, help="壁厚 mm(柱105角=160, 120角=175)")
    ap.add_argument("--preview", help="確認用 SVG の出力先")
    a = ap.parse_args()
    make(a.dtx, a.out, a.name, a.number, a.date, a.floor, a.wall, a.preview)


if __name__ == "__main__":
    main()
