# 同じ 1 階データを、Walk in home が出力した CSV (NSIFDATV.110) の書式で出力する。
# 書式は塩﨑邸サンプル CSV から推定したもの。分かっている範囲だけを書き、他のブロックは件数 0。
#   XA 部屋: 階, 種類コード, 1, 0, 床高, 天井高, 名称, 点数, 点列
#   XD 建具: 階, 始点X, 始点Y, 終点X, 終点Y, 種別(1=窓 2=戸 3=開口), 上端高, 開口高, 0
#   XL 外周: 階, 0, 点数, 点列
#   YI 寸法線: 階, 向き(1=横 2=縦), 始点X, 始点Y, 終点X, 終点Y, 引出しX, 引出しY, 寸法値
# 座標は CSV に合わせて Y を下向き(上端が 0、下へマイナス)にする。

import make_cedxm as m

D, W = m.D, m.W


def c(x, y):
    return f"{x:.2f},{y - D:.2f}"


# 部屋の種類コード(サンプルより: 2=居室 3=玄関・土間 4=トイレ 5=浴室 6=廊下 9=収納)
ROOM_CODE = {"玄関": 3, "下足入": 3, "便所": 4, "浴室": 5, "廊下": 6, "階段": 6,
             "収納": 9, "物入": 9}
DOMA = {"玄関", "下足入"}

# 寸法線(図面の寸法に合わせた区切り)
DIM_BOTTOM = [0, m.p(4), m.p(7), W]                  # 下側
DIM_TOP = [0, m.p(3), m.p(7), m.p(9), W]             # 上側
DIM_LEFT = [0, 910, 3640, 5460, D]                    # 左側(図面: 910 / 2730 / 1820 / 2275)
DIM_RIGHT = [0, 3640, 4550, 5915, D]                  # 右側

dims = []


def chain(xs, axis, pos, off):
    """xs の区切りごとの寸法と全体寸法を追加。axis=1 横, 2 縦。"""
    for a, b in zip(xs, xs[1:]):
        dims.append((axis, a, b, pos, off))
    dims.append((axis, xs[0], xs[-1], pos, off * 1.5))


chain(DIM_BOTTOM, 1, 0, -900)
chain(DIM_TOP, 1, D, 900)
chain(DIM_LEFT, 2, 0, -900)
chain(DIM_RIGHT, 2, W, 900)

rows = ['"WV",1', '"NSIFDATV.110"', '"WA",1']
rows.append(f'"Walk in home","26-10-03 12:00","1階平面図",910.00,1,1,0.00,{-D - 455:.2f},'
            f'12.51,{W / 2:.2f},{-D / 2:.2f},625.00,3,0,2896,5636,8436')
rows += ['"WB",0', '"WC",0']

rows.append(f'"XA",{len(m.rooms)}')
for name, poly in m.rooms:
    fl, ce = (-144, 2580) if name in DOMA else (36, 2400)
    pts = ",".join(c(x, y) for x, y in poly)
    rows.append(f'1,{ROOM_CODE.get(name, 2)},1,0,{fl},{ce},"{name}",{len(poly)},{pts}')
rows += ['"XB",0', '"XC",0']

rows.append(f'"XD",{len(m.openings)}')
for _, kind, _, a, b, _, oh, top in m.openings:
    rows.append(f"1,{c(*a)},{c(*b)},{kind},{top},{oh},0")
rows += ['"XE",0', '"XF",0', '"XG",0', '"XH",0', '"XI",0', '"XJ",0', '"XK",0']

outer = [(W, 0), (W, D), (0, D), (0, 0)]
rows.append('"XL",1')
rows.append(f'1,0,{len(outer)},' + ",".join(c(x, y) for x, y in outer))
rows += ['"YA",0', '"YB",0', '"YC",0', '"YD",0', '"YE",0', '"YF",0', '"YG",0', '"YH",0']

rows.append(f'"YI",{len(dims)}')
for axis, a, b, pos, off in dims:
    if axis == 1:   # 横寸法: 右→左(サンプルと同じ向き)
        rows.append(f"1,1,{c(b, pos + off)},{c(a, pos + off)},0.00,{(400 if off > 0 else -400):.2f},{b - a:.2f}")
    else:           # 縦寸法: 上→下
        rows.append(f"1,2,{c(pos + off, b)},{c(pos + off, a)},{(400 if off > 0 else -400):.2f},0.00,{b - a:.2f}")
rows.append('"YJ",0')

with open("1F.csv", "w", encoding="cp932", newline="\r\n") as fp:
    fp.write("\n".join(rows) + "\n")
