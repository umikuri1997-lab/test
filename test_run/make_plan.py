# スキャン図面 (1階平面図) を読み取った plan JSON を作る。座標は DTX 座標 (上端 0、下へマイナス)。
import json
import math

W, D = 10010, -7735

def rect(x1, y1, x2, y2):
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

# 弓形出窓 (左側 y -910〜-3640、出幅 945) を折れ線で近似
bow = [[0, -910]]
for k in range(1, 8):
    t = math.pi * k / 8
    bow.append([round(-945 * math.sin(t), 2), round(-910 - 2730 * (1 - math.cos(t)) / 2, 2)])
bow.append([0, -3640])

rooms = [
    dict(name="食堂・居間", code=4, label="tatami", living=True,
         points=[[0, 0], [2730, 0], [2730, -2275], [3640, -2275], [3640, D], [0, D]]),
    dict(name="台所", code=4, label="tatami", living=True,
         points=[[2730, 0], [6370, 0], [6370, -1820], [5460, -1820], [5460, -2275], [2730, -2275]]),
    dict(name="収納", code=13, label="blank", points=rect(3640, -2275, 5460, -3185)),
    dict(name="なし", code=2, label="none", points=rect(3640, -3185, 5460, -4095)),          # 階段
    dict(name="ホール", code=4, label="none", living=True,
         points=[[3640, -4095], [5460, -4095], [5460, -1820], [6370, -1820], [6370, -5915],
                 [4550, -5915], [4550, -5005], [3640, -5005]]),
    dict(name="玄関", code=1, label="none", points=rect(4550, -5915, 6370, -7128)),
    dict(name="下足入", code=1, label="none", points=rect(3640, -5005, 4550, -7128)),
    dict(name="和室", code=3, label="tatami", living=True, points=rect(6370, -4095, W, D)),
    dict(name="押入", code=13, label="blank", points=rect(6370, -3185, 8190, -4095)),
    dict(name="なし", code=2, label="none", points=rect(6370, -1820, 8190, -2730)),         # 廊下
    dict(name="物入", code=13, label="blank", points=rect(6370, -2730, 8190, -3185)),
    dict(name="床の間", code=13, label="blank", points=rect(8190, -3640, W, -4095)),
    dict(name="洗面", code=7, label="tatami", points=rect(8190, -1820, W, -3640)),
    dict(name="勝手口", code=2, label="tatami", points=rect(6370, 0, 7280, -1820)),
    dict(name="便所", code=8, label="blank", points=rect(7280, 0, 8190, -1820)),
    dict(name="浴室", code=6, label="tatami", points=rect(8190, 0, W, -1820)),
    dict(name="なし", code=4, label="blank", living=True, p5=30.0, points=bow),             # 弓形出窓の張り出し
]
for r in rooms:
    r["floor"] = 1

outline = [[0, 0], [W, 0], [W, D], [6370, D], [6370, -7128], [3640, -7128], [3640, D], [0, D]]

# 壁: 部屋の辺を集めて重複を除き、交点で分割。壁を立てない境界は OPEN に書く。
OPEN = [((3640, -4095), (5460, -4095)),    # 階段 / ホール
        ((4550, -5915), (6370, -5915)),    # ホール / 玄関 (上り框)
        ((6370, -1820), (7280, -1820)),    # 勝手口 / 廊下 (勝手口の入口、下がり壁)
        ((5460, -3185), (5460, -4095)),    # 階段の上り口 / ホール
        ((6370, -1820), (6370, -2730)),    # ホール / 廊下 (下がり壁)
        ((8190, -4095), (W, -4095)),       # 床の間 / 和室
        ((4550, -5005), (4550, -5915)),    # 下足入 / ホール (下足入の扉面)
        ((0, -910), (0, -3640))]           # 弓形出窓の付け根
def on(p, a, b):
    return (min(a[0], b[0]) - 1 <= p[0] <= max(a[0], b[0]) + 1 and min(a[1], b[1]) - 1 <= p[1] <= max(a[1], b[1]) + 1
            and abs((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) < 1e-3 * math.dist(a, b) + 1e-6)
edges = []
for r in rooms:
    ps = r["points"]
    edges += [(tuple(ps[i]), tuple(ps[(i + 1) % len(ps)])) for i in range(len(ps))]
verts = {p for e in edges for p in e}
segs = set()
for a, b in edges:
    cut = sorted([p for p in verts if on(p, a, b)], key=lambda p: math.dist(a, p))
    for p, q in zip(cut, cut[1:]):
        if math.dist(p, q) > 1:
            segs.add(tuple(sorted((p, q))))
def is_open(s):
    return any(on(s[0], a, b) and on(s[1], a, b) for a, b in OPEN)
def on_outline(s):
    return any(on(s[0], tuple(outline[i]), tuple(outline[(i + 1) % len(outline)])) and
               on(s[1], tuple(outline[i]), tuple(outline[(i + 1) % len(outline)])) for i in range(len(outline)))
walls = []
for s in sorted(segs):
    if is_open(s):
        continue
    ext = on_outline(s) or (s[0][0] <= 0 and s[1][0] <= 0 and (s[0][0] < 0 or s[1][0] < 0))
    walls.append(dict(floor=1, kind="normal", exterior=ext, p1=list(s[0]), p2=list(s[1])))
walls += [dict(floor=1, kind="normal", exterior=False, p1=[3640, -8190], p2=[3640, -8645]),   # ポーチ袖壁
          dict(floor=1, kind="normal", exterior=False, p1=[6370, -8190], p2=[6370, -8645]),
          dict(floor=1, kind="hang", bottom=2000, p1=[7280, -1820], p2=[6370, -1820]),
          dict(floor=1, kind="hang", bottom=2000, p1=[6370, -2730], p2=[6370, -1820]),
          dict(floor=1, kind="hang", bottom=2000, p1=[W, -4095], p2=[8190, -4095])]
# 弓形出窓の外周も外壁
for p, q in zip(bow, bow[1:]):
    walls = [w for w in walls if not (tuple(sorted((tuple(p), tuple(q)))) == tuple(sorted((tuple(w["p1"]), tuple(w["p2"])))))]
    walls.append(dict(floor=1, kind="normal", exterior=True, p1=p, p2=q))

F = lambda kind, p1, p2, width, height, top, **kw: dict(floor=1, kind=kind, p1=p1, p2=p2, width=width,
                                                         height=height, top=top, **kw)
fittings = [
    # 外部
    F("window_slide", [910, 455], [2730, 455], 1620, 1170, 1850),            # H-1612 (造作出窓)
    F("window_slide", [3640, 0], [5460, 0], 1620, 600, 1850),                # H-1606 台所
    F("door_ext", [7280, 0], [6370, 0], 690, 2000, 2000, hinge=-1),          # WO-0720 勝手口
    F("window_vert", [7280, 0], [8190, 0], 405, 800, 1850, spec="型板"),      # T-0408 便所
    F("window_slide", [8190, 0], [9100, 0], 710, 800, 1850),                 # H-0708 浴室
    F("window_vert", [W, -3336.67], [W, -2730], 405, 1000, 1850, spec="型板"),  # T-0410 洗面
    F("window_vert", [bow[1][0], bow[1][1]], [0, -910], 300, 1000, 2000),    # 弓形出窓 小窓(上)
    F("window_vert", [bow[-2][0], bow[-2][1]], [0, -3640], 300, 1000, 2000, hinge=-1),  # 弓形出窓 小窓(下)
    F("window_slide", [W, -5005], [W, -6825], 1620, 1400, 1850),             # H-1614 和室
    F("window_slide", [7280, D], [9100, D], 1620, 1800, 1850),               # HK-1618 和室
    F("window_bay", [910, D], [2730, D], 1620, 1400, 1850, depth=400),       # BAY-1614 居間
    F("combo_fix", [0, -6795], [0, -5713.75], 881.25, 1370, 2000,            # 居間 連窓 FIX + 縦滑り出し
      combo=dict(p1=[0, -5035], p2=[0, -6795], top=2000, width=1760)),
    F("combo_vert", [0, -5035], [0, -5713.75], 478.75, 1370, 2000,
      combo=dict(p1=[0, -5035], p2=[0, -6795], top=2000, width=1760)),
    F("door_side", [5915, -7128], [4550, -7128], 1203, 2330, 2330, spec="玄関ﾄﾞｱ"),  # GE 1223
    # 室内
    F("opening_frame", [2730, -1668.33], [2730, -758.33], 820, 2000, 2000),  # 0820 台所 / 居間
    F("door_in", [3640, -4095], [3640, -5005], 690, 2000, 2000),             # 0820G ホール / 居間
    F("fusuma", [6370, -5915], [6370, -4095], 1600, 2000, 2000),             # 1618 ホール / 和室
    F("fusuma", [8190, -4095], [6370, -4095], 1600, 2000, 2000),             # ｵﾄ-1618 押入
    F("sliding_in", [8190, -2730], [6370, -2730], 1600, 2000, 2000),         # ｵﾚ-1620F 物入 (折戸の代わり)
    F("sliding_in", [4550, -5005], [4550, -6825], 1620, 2000, 2000),         # AL-1621K 下足入 (扉の代わり)
    F("door_in", [6370, -1820], [5460, -1820], 690, 2000, 2000, hinge=-1),   # ﾄﾞ-0720FK 勝手口
    F("door_in", [8190, -1820], [7280, -1820], 600, 2000, 2000, hinge=-1),   # ﾍﾞﾄﾞ-0620FK 便所
    F("door_in", [8190, -1820], [9100, -1820], 690, 2000, 2000),             # ﾖ-0718 浴室
    F("door_in", [8190, -1820], [8190, -2730], 690, 2000, 2000),             # ﾄﾞ-0720FK 洗面
    F("door_in", [5460, -2275], [5460, -3185], 690, 2000, 2000),             # ﾓ-0720F 収納
]

def chain(cuts, edge, off1=1365, off2=1820):
    out = []
    cuts = sorted(cuts)
    segs = list(zip(cuts, cuts[1:])) + [(cuts[0], cuts[-1])]
    for i, (a, b) in enumerate(segs):
        off = off2 if i == len(segs) - 1 else off1
        if edge == "bottom":
            out.append(dict(floor=1, side=-1, p1=[b, D], p2=[a, D], p3=[a, D - off]))
        elif edge == "top":
            out.append(dict(floor=1, side=1, p1=[b, 0], p2=[a, 0], p3=[a, off]))
        elif edge == "right":
            out.append(dict(floor=1, side=-1, p1=[W, b], p2=[W, a], p3=[W + off, a]))
        else:
            out.append(dict(floor=1, side=1, p1=[0, b], p2=[0, a], p3=[-off, a]))
    return out

dims = (chain([0, 3640, 6370, W], "bottom") + chain([0, 2730, 6370, 8190, W], "top")
        + chain([D, -6825, -4095, -2275, 0], "left") + chain([D, -4095, -3640, -1820, 0], "right"))

# 家具・住宅設備(図面の位置から)。center は部品の中心、dir は部品の幅の向き(奥行きは dir の右側)。
furniture = [
    dict(symbol="浴室・洗面関連\\ﾎﾟﾘﾊﾞｽ1100.sym", corner=[9930, -780], dir=[-1, 0]),        # 浴槽
    dict(symbol="家電\\冷蔵庫1.sym", corner=[3488.33, -2195], dir=[-1, 0]),                   # 冷蔵庫
    dict(symbol="基本形状\\ﾎﾞｯｸｽ.sym", corner=[5380, -2195], dir=[-1, 0], size=[1740, 455, 850]),  # バックカウンター
    dict(symbol="ｻﾎﾟｰﾄｻｲﾄ\\家電\\洗濯機1652.sym", center=[6774, -1368], dir=[0, 1]),          # 洗濯機(勝手口、左の壁に背を付けて右向き)
    dict(symbol="家具関連\\Dﾃｰﾌﾞﾙ1423.sym", center=[1365, -2170], dir=[0, -1]),               # ダイニングテーブル
    dict(symbol="家具関連\\Dﾁｪｱ1.sym", center=[910, -1860], dir=[0, 1]),
    dict(symbol="家具関連\\Dﾁｪｱ1.sym", center=[910, -2480], dir=[0, 1]),
    dict(symbol="家具関連\\Dﾁｪｱ1.sym", center=[1820, -1860], dir=[0, -1]),
    dict(symbol="家具関連\\Dﾁｪｱ1.sym", center=[1820, -2480], dir=[0, -1]),
    dict(symbol="ｵﾌｨｽﾌｧﾆﾁｬｰ\\応接ｲｽA3.sym", center=[1362, -7280], dir=[-1, 0]),             # ソファ(下の壁沿い)
    dict(symbol="ｵﾌｨｽﾌｧﾆﾁｬｰ\\応接ｲｽA3.sym", center=[3160, -6195], dir=[0, -1]),             # ソファ(右側)
    dict(symbol="家具関連\\Lﾃｰﾌﾞﾙ1804.sym", center=[1566, -6054], dir=[1, 0]),               # リビングテーブル
    # 合う部品が無いものは四角形(基本形状\ﾎﾞｯｸｽ)で代用。size は [幅, 奥行き, 高さ]
    dict(symbol="基本形状\\ﾎﾞｯｸｽ.sym", center=[2890, -3350], dir=[0, -1], size=[1500, 600, 1250]),   # ピアノ
    dict(symbol="基本形状\\ﾎﾞｯｸｽ.sym", center=[3375, -3375], dir=[0, 1], size=[1350, 350, 850]),    # サイドボード(ピアノ横)
    dict(symbol="基本形状\\ﾎﾞｯｸｽ.sym", center=[280, -4075], dir=[0, 1], size=[750, 400, 850]),      # サイドボード(左の壁沿い)
    dict(symbol="基本形状\\ﾎﾞｯｸｽ.sym", center=[700, -5330], dir=[0.7071, 0.7071], size=[1200, 450, 500]),  # テレビ台(斜め置き)
    dict(symbol="基本形状\\ﾎﾞｯｸｽ.sym", center=[3945, -6050], dir=[0, -1], size=[1900, 450, 2000]),  # 下駄箱(下足入)
    dict(symbol="基本形状\\ﾎﾞｯｸｽ.sym", center=[3570, -1985], dir=[0, 1], size=[400, 120, 900]),    # 米ロッカー(台所)
]
for o in furniture:
    o["floor"] = 1
equipment = [
    dict(floor=1, type="kitchen", corner=[2810, -80], dir=[1, 0], width=2550),     # システムキッチン(上の壁沿い)
    dict(floor=1, type="vanity", corner=[9930, -3560], dir=[-1, 0], width=1660),   # 洗面化粧台(2ボウル)
]

plan = dict(
    furniture=furniture, equipment=equipment,
    name="1階平面図", rooms=rooms, walls=walls, fittings=fittings, dims=dims,
    outlines=[dict(floor=1, points=outline), dict(floor=2, points=rect(2730, -3185, 5460, -4095))],  # 2階側は階段の吹抜
    tatami=[dict(floor=1, points=rect(6370, -4095, W, D))],
    bay_windows=[dict(floor=1, top=2000, height=1000, depth=455, p1=[2730, 0], p2=[910, 0])],
    agari=[dict(floor=1, p1=[4550, -5915], p2=[6370, -5915]), dict(floor=1, p1=[6370, -455], p2=[7280, -455])],
    stairs=[dict(floor=1, steps=11, points=[[5460, -4095], [5460, -3185], [2730, -3185], [2730, -4095]])],
    stair_cuts=[dict(floor=1, p1=[4095, -3185], p2=[4095, -4095])],
    porches=[
        dict(floor=1, type=1, points=[[3336.67, -9100], [6673.33, -9100], [6673.33, D], [6370, D],
                                      [6370, -7128], [3640, -7128], [3640, D], [3336.67, D]]),   # 玄関ポーチ
        dict(floor=1, type=2, points=rect(-80, -5005, -680, -6825)),        # 居間 掃出し前
        dict(floor=1, type=2, points=rect(7280, -7815, 9100, -8415)),       # 和室 前
        dict(floor=1, type=2, points=rect(6325, 0, 7325, 1000)),            # 勝手口 前
    ],
    floor_parts=[dict(floor=1, level=-200, points=rect(6370, 0, 7280, -455))],
)
json.dump(plan, open("plan.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(rooms), "rooms", len(walls), "walls", len(fittings), "fittings", len(dims), "dims")
