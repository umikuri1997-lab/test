# スキャン平面図(1階)から読み取った概略データで CEDXM 風 XML を作る。
# 座標: 建物左下を原点、X=右、Y=上、単位 mm、モジュール 910。
import xml.etree.ElementTree as ET

P = 910
W, D = 11 * P, 7735  # 建物外形 10010 x 7735

walls = [  # 外壁
    ((0, 0), (W, 0)), ((W, 0), (W, D)), ((W, D), (0, D)), ((0, D), (0, 0)),
]
walls += [  # 主な内壁
    ((3 * P, 6 * P), (3 * P, D)),          # LD / 台所
    ((4 * P, 0), (4 * P, 4 * P)),          # LD / 玄関・ホール
    ((4 * P, 4 * P), (4 * P, 6 * P)),      # LD / 階段
    ((3 * P, 6 * P), (7 * P, 6 * P)),      # 台所 / 階段
    ((7 * P, 0), (7 * P, D)),              # 和室・水回り / 中央
    ((7 * P, 4 * P), (W, 4 * P)),          # 和室 / 廊下
    ((7 * P, 5 * P), (W, 5 * P)),          # 廊下 / 物入・洗面
    ((9 * P, 5 * P), (9 * P, D)),          # 洗面・浴室 / 物入・便所
    ((8 * P, 6.5 * P), (8 * P, D)),        # 便所 / 勝手口
    ((7 * P, 6.5 * P), (W, 6.5 * P)),      # 洗面 / 浴室・便所
    ((4 * P, 2 * P), (7 * P, 2 * P)),      # 玄関 / ホール
    ((5 * P, 0), (5 * P, 2 * P)),          # 下足入 / 玄関
]

rooms = [
    ("食堂・居間", [(0, 0), (4 * P, 0), (4 * P, 6 * P), (3 * P, 6 * P), (3 * P, D), (0, D)]),
    ("台所", [(3 * P, 6 * P), (7 * P, 6 * P), (7 * P, D), (3 * P, D)]),
    ("階段", [(4 * P, 4 * P), (6 * P, 4 * P), (6 * P, 6 * P), (4 * P, 6 * P)]),
    ("収納", [(6 * P, 4 * P), (7 * P, 4 * P), (7 * P, 6 * P), (6 * P, 6 * P)]),
    ("ホール", [(4 * P, 2 * P), (7 * P, 2 * P), (7 * P, 4 * P), (4 * P, 4 * P)]),
    ("玄関", [(5 * P, 0), (7 * P, 0), (7 * P, 2 * P), (5 * P, 2 * P)]),
    ("下足入", [(4 * P, 0), (5 * P, 0), (5 * P, 2 * P), (4 * P, 2 * P)]),
    ("和室", [(7 * P, 0), (W, 0), (W, 4 * P), (7 * P, 4 * P)]),
    ("廊下", [(7 * P, 4 * P), (W, 4 * P), (W, 5 * P), (7 * P, 5 * P)]),
    ("物入", [(7 * P, 5 * P), (9 * P, 5 * P), (9 * P, 6.5 * P), (7 * P, 6.5 * P)]),
    ("洗面", [(9 * P, 5 * P), (W, 5 * P), (W, 6.5 * P), (9 * P, 6.5 * P)]),
    ("勝手口", [(7 * P, 6.5 * P), (8 * P, 6.5 * P), (8 * P, D), (7 * P, D)]),
    ("便所", [(8 * P, 6.5 * P), (9 * P, 6.5 * P), (9 * P, D), (8 * P, D)]),
    ("浴室", [(9 * P, 6.5 * P), (W, 6.5 * P), (W, D), (9 * P, D)]),
]

# (記号, 種別, 始点, 終点)  幅は図面の記号から、位置は目測
openings = [
    ("H-1612", "窓", (1000, D), (2700, D)),
    ("H-1606", "窓", (4100, D), (5800, D)),
    ("WO-0720", "ドア", (6400, D), (7200, D)),
    ("T-0408", "窓", (7500, D), (7950, D)),
    ("H-0708", "窓", (9000, D), (9750, D)),
    ("F-0418/T-0414", "出窓", (0, 4700), (0, 7100)),
    ("HK-1620", "掃出し窓", (0, 1200), (0, 2950)),
    ("BAY-1614", "出窓", (1100, 0), (2800, 0)),
    ("GE 1223MM", "玄関ドア", (5100, 0), (6300, 0)),
    ("HK-1618", "掃出し窓", (7280, 0), (9100, 0)),
    ("H-1614", "窓", (W, 900), (W, 2700)),
    ("T-0410", "窓", (W, 5000), (W, 5500)),
]

root = ET.Element("CEDXM", Version="rough", Note="スキャン図面からの概略変換。正式仕様に未準拠")
b = ET.SubElement(root, "Building", Name="1階平面図", Module=str(P))
f = ET.SubElement(b, "Floor", No="1", Name="1F")
g = ET.SubElement(f, "Grids")
for i in range(12):
    ET.SubElement(g, "Grid", Dir="X", Name=f"X{i}", Pos=str(i * P))
for i, y in enumerate([0, 910, 1820, 2730, 3640, 4550, 5460, 5915, 6370, 7280, D]):
    ET.SubElement(g, "Grid", Dir="Y", Name=f"Y{i}", Pos=str(int(y)))
ws = ET.SubElement(f, "Walls")
for n, ((x1, y1), (x2, y2)) in enumerate(walls, 1):
    ET.SubElement(ws, "Wall", ID=f"W{n}", Type="外壁" if n <= 4 else "内壁",
                  X1=str(int(x1)), Y1=str(int(y1)), X2=str(int(x2)), Y2=str(int(y2)), Thickness="120")
ops = ET.SubElement(f, "Openings")
for n, (code, kind, (x1, y1), (x2, y2)) in enumerate(openings, 1):
    ET.SubElement(ops, "Opening", ID=f"O{n}", Code=code, Kind=kind,
                  X1=str(int(x1)), Y1=str(int(y1)), X2=str(int(x2)), Y2=str(int(y2)))
rs = ET.SubElement(f, "Rooms")
for n, (name, pts) in enumerate(rooms, 1):
    area = abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2 / 1e6
    r = ET.SubElement(rs, "Room", ID=f"R{n}", Name=name, Area=f"{area:.2f}")
    for x, y in pts:
        ET.SubElement(r, "Point", X=str(int(x)), Y=str(int(y)))
ET.indent(root)
ET.ElementTree(root).write("1F_rough.cedxm.xml", encoding="utf-8", xml_declaration=True)

# 確認用 SVG
s = 0.05
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*s+40}" height="{D*s+40}" style="background:#fff">',
       f'<g transform="translate(20,{D*s+20}) scale(1,-1)">']
for name, pts in rooms:
    svg.append('<polygon fill="#eef" stroke="none" points="' + " ".join(f"{x*s},{y*s}" for x, y in pts) + '"/>')
for (x1, y1), (x2, y2) in walls:
    svg.append(f'<line x1="{x1*s}" y1="{y1*s}" x2="{x2*s}" y2="{y2*s}" stroke="#000" stroke-width="4"/>')
for _, _, (x1, y1), (x2, y2) in openings:
    svg.append(f'<line x1="{x1*s}" y1="{y1*s}" x2="{x2*s}" y2="{y2*s}" stroke="#e33" stroke-width="6"/>')
svg.append('</g>')
for name, pts in rooms:
    cx = sum(p[0] for p in pts) / len(pts) * s + 20
    cy = D * s + 20 - sum(p[1] for p in pts) / len(pts) * s
    svg.append(f'<text x="{cx}" y="{cy}" font-size="11" text-anchor="middle">{name}</text>')
svg.append('</svg>')
open("1F_rough_preview.svg", "w").write("\n".join(svg))
