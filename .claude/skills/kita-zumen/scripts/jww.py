#!/usr/bin/env python3
"""Jw_cad JWW ファイル(Ver.7.00 系)の図形部分を読み書きする。

ヘッダ(用紙・レイヤ設定など)と、図形リストの後ろ(ブロック定義・画像)はバイト列のまま保持し、
図形リスト(線・円弧・点・文字・ソリッド)だけを解析・追加する。
"""
import re
import struct

KIND_FIELDS = {
    "CDataSen": "4d",          # 始点 x,y  終点 x,y
    "CDataEnko": "7dI",        # 中心 x,y 半径 開始角 円弧角 傾き 扁平率 全円フラグ
    "CDataSolid": "8d",        # 点1 x,y  点4 x,y  点2 x,y  点3 x,y (+色 DWORD: 線色 10 のとき)
}
BIG = 0x7FFF


def _cstr(d, i):
    n = d[i]
    i += 1
    if n == 0xFF:
        n = struct.unpack_from("<H", d, i)[0]
        i += 2
        if n == 0xFFFF:
            n = struct.unpack_from("<I", d, i)[0]
            i += 4
    return d[i:i + n].decode("cp932", "replace"), i + n


def _wcstr(s):
    b = s.encode("cp932")
    n = len(b)
    if n < 0xFF:
        return bytes([n]) + b
    if n < 0xFFFF:
        return b"\xff" + struct.pack("<H", n) + b
    return b"\xff\xff\xff" + struct.pack("<I", n) + b


class Ent:
    __slots__ = ("cls", "group", "style", "color", "width", "layer", "glayer", "flag", "v", "extra")

    def __init__(self, cls, layer=0, glayer=0, color=1, style=1, width=0, group=0, flag=0, v=(), extra=None):
        self.cls, self.layer, self.glayer, self.color, self.style = cls, layer, glayer, color, style
        self.width, self.group, self.flag, self.v, self.extra = width, group, flag, list(v), extra or {}


class Jww:
    def __init__(self, path):
        d = open(path, "rb").read()
        self.data = d
        m = re.search(rb"\xff\xff..[\x08-\x0a]\x00CData", d, re.S)
        start = m.start()
        # 件数: WORD か 0xFFFF + DWORD
        if d[start - 6:start - 4] == b"\xff\xff":
            self.count_pos, n = start - 6, struct.unpack_from("<I", d, start - 4)[0]
        else:
            self.count_pos, n = start - 2, struct.unpack_from("<H", d, start - 2)[0]
        self.head = d[:self.count_pos]
        self.classes = {}       # class name -> map index
        self.schema = {}
        self.ents = []
        idx = 1                 # MFC CArchive のマップ番号(クラスとオブジェクトで共通)
        names = {}
        i = start
        for _ in range(n):
            tag = struct.unpack_from("<H", d, i)[0]
            i += 2
            if tag == 0xFFFF:
                sch, ln = struct.unpack_from("<HH", d, i)
                i += 4
                name = d[i:i + ln].decode()
                i += ln
                self.classes[name] = idx
                self.schema[name] = sch
                names[idx] = name
                idx += 1
            elif tag == BIG:
                big = struct.unpack_from("<I", d, i)[0]
                i += 4
                name = names[big & 0x7FFFFFFF]
            else:
                name = names[tag & 0x7FFF]
            e, i = self._read(name, d, i)
            self.ents.append(e)
            idx += 1
        self.next_index = idx
        self.tail = d[i:]

    def _read(self, name, d, i):
        group, style, color, width, layer, glayer, flag = struct.unpack_from("<IBHHHHH", d, i)
        i += 15
        e = Ent(name, layer, glayer, color, style, width, group, flag)
        if name in KIND_FIELDS:
            fmt = "<" + KIND_FIELDS[name]
            e.v = list(struct.unpack_from(fmt, d, i))
            i += struct.calcsize(fmt)
            if name == "CDataSolid" and color == 10:
                e.extra["rgb"] = struct.unpack_from("<I", d, i)[0]
                i += 4
        elif name == "CDataTen":
            x, y, kari = struct.unpack_from("<ddI", d, i)
            i += 20
            e.v = [x, y, kari]
            if style == 100:
                e.extra["code"], e.extra["angle"], e.extra["scale"] = struct.unpack_from("<Idd", d, i)
                i += 20
        elif name == "CDataMoji":
            vals = struct.unpack_from("<4dI4d", d, i)
            i += struct.calcsize("<4dI4d")
            font, i = _cstr(d, i)
            text, i = _cstr(d, i)
            e.v = list(vals)
            e.extra["font"], e.extra["text"] = font, text
        else:
            raise ValueError(name)
        return e, i

    def _write(self, e):
        b = struct.pack("<IBHHHHH", e.group, e.style, e.color, e.width, e.layer, e.glayer, e.flag)
        if e.cls in KIND_FIELDS:
            b += struct.pack("<" + KIND_FIELDS[e.cls], *e.v)
            if e.cls == "CDataSolid" and e.color == 10:
                b += struct.pack("<I", e.extra.get("rgb", 0))
        elif e.cls == "CDataTen":
            b += struct.pack("<ddI", *e.v)
            if e.style == 100:
                b += struct.pack("<Idd", e.extra["code"], e.extra["angle"], e.extra["scale"])
        elif e.cls == "CDataMoji":
            b += struct.pack("<4dI4d", *e.v) + _wcstr(e.extra["font"]) + _wcstr(e.extra["text"])
        return b

    def save(self, path):
        out = [self.head]
        n = len(self.ents)
        out.append(struct.pack("<H", n) if n < 0xFFFF else b"\xff\xff" + struct.pack("<I", n))
        seen = {}
        idx = 1
        for e in self.ents:
            if e.cls not in seen:
                sch = self.schema.get(e.cls, 700)
                out.append(struct.pack("<HHH", 0xFFFF, sch, len(e.cls)) + e.cls.encode())
                seen[e.cls] = idx
                idx += 1
            else:
                ci = seen[e.cls]
                out.append(struct.pack("<H", 0x8000 | ci) if ci < BIG else
                           struct.pack("<HI", BIG, 0x80000000 | ci))
            out.append(self._write(e))
            idx += 1
        out.append(self.tail)
        open(path, "wb").write(b"".join(out))

    # 便利関数 ---------------------------------------------------------
    def line(self, x1, y1, x2, y2, **kw):
        self.ents.append(Ent("CDataSen", v=(x1, y1, x2, y2), **kw))

    def solid(self, p1, p2, p3, p4, rgb=None, **kw):
        """四角形(三角形なら p4=p3)を塗る。p1→p2→p3→p4 の順に周回。"""
        if rgb is not None:
            kw["color"] = 10
        e = Ent("CDataSolid", v=(p1[0], p1[1], p4[0], p4[1], p2[0], p2[1], p3[0], p3[1]), **kw)
        if rgb is not None:
            e.extra["rgb"] = rgb
        self.ents.append(e)

    def arc(self, cx, cy, r, start=0.0, sweep=6.283185307179586, **kw):
        full = 1 if abs(sweep - 6.283185307179586) < 1e-9 else 0
        self.ents.append(Ent("CDataEnko", v=(cx, cy, r, start, sweep, 0.0, 1.0, full), **kw))

    def text(self, x, y, s, size=3.5, angle=0.0, kind=1, font="ＭＳ ゴシック", spacing=0.0, **kw):
        """size は図寸(mm)。文字列の幅は概算。"""
        w = size * sum(1 if ord(c) > 0xFF else 0.5 for c in s)
        self.ents.append(Ent("CDataMoji", v=(x, y, x + w, y, kind, size, size, spacing, angle),
                             extra={"font": font, "text": s}, **kw))
