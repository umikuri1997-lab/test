---
name: cedxm-pset-param
description: IFC ファイルの木質系部材に CEDXM 連携用プロパティセット 'Cedxm_Pset_param'（mokuzai, syurui, jyusyu, toukyuu, kesyou, 端部加工形状, 断面, 芯ずれ）を付ける・読む・検証するときに使う。IFCPROPERTYSET / IFCPROPERTYSINGLEVALUE / IFCRELDEFINESBYPROPERTIES の行の生成、既存 IFC の値チェック、BIM→プレカット CAD 連携の属性設計が対象。
---

# Cedxm_Pset_param（シーデクセマ評議会 仕様書 2026-03-06 版に基づく）

IFC 内の各要素が木質系か、柱・横架材・羽柄材のどれかなどを、BIM アプリが違っても自動判定できるようにするための独自プロパティセット。
CEDXM の XML ファイル本体の仕様ではなく、**IFC に付ける属性の仕様**である。

## IFC での書き方

```
#500=IFCRELDEFINESBYPROPERTIES('<GUID>',$,'Cedxm_Pset_param',$,(#3000,#3010),#501);
#501=IFCPROPERTYSET('<GUID>',$,'Cedxm_Pset_param',$,(#2930,#7678,...));
#2930=IFCPROPERTYSINGLEVALUE('mokuzai',$,IFCBOOLEAN(.T.),$);
```

- IFCRELDEFINESBYPROPERTIES：GUID, オーナーヒストリー, セット名, 説明, 適用先要素のリスト, IFCPROPERTYSET への参照
- IFCPROPERTYSET：GUID, オーナーヒストリー, セット名 `'Cedxm_Pset_param'`, 説明, プロパティのリスト
- プロパティはすべて IFCPROPERTYSINGLEVALUE。第2・第4引数は未使用（`$`）
- 指定のない値は出力されないか、空のまま出力されることがある（読み込み側は欠落を許容する）

## プロパティ一覧

| 名前 | 型 | 内容 | 値 |
|---|---|---|---|
| mokuzai | IFCBOOLEAN | 木質系か | `.T.` 木質系（編集対象として読む）／`.F.` 木質系以外（干渉チェック用。樹種名に '木材以外' を入れて連携） |
| syurui | IFCLABEL | 部材の種類 | 下の「syurui の値」 |
| jyusyu | IFCTEXT | 樹種（自由文字列） | 例 `'hinoki'`。取込時は各アプリの変換マスターで変換 |
| toukyuu | IFCTEXT | 等級（自由文字列） | 例 `'tokuiti'`。取込時は各アプリの変換マスターで変換 |
| kesyou | IFCBOOLEAN | 化粧材か | `.T.` 化粧材／`.F.` 化粧材以外 |
| siten_keijyou | IFCLABEL | 横架材の始端加工形状 | 下の「横架材端部の値」 |
| syuuten_keijyou | IFCLABEL | 横架材の終端加工形状 | 同上 |
| joutan_keijyou | IFCLABEL | 柱の上端加工形状 | 下の「柱端部の値」 |
| katan_keijyou | IFCLABEL | 柱の下端加工形状 | 同上 |
| w | IFCTEXT | 断面の幅 | 半角数字 例 `'105'`。長方形以外は外接する最小長方形の幅 |
| h | IFCTEXT | 断面の高さ | 半角数字 例 `'240'`。長方形以外は外接する最小長方形の高さ |
| hasira_w1 | IFCTEXT | 柱断面 w1（回転前の CAD 画面 X 方向） | 半角数字 例 `'240'` |
| hasira_w2 | IFCTEXT | 柱断面 w2（回転前の CAD 画面 Y 方向） | 半角数字 例 `'120'` |
| sinzure | IFCTEXT | 横架材の芯ずれ量 | 例 `'-7.5'`。水平材：上＋／下−。垂直材・斜め材：右＋／左− |
| hasira_sinzure_x | IFCTEXT | 柱の X 方向芯ずれ量 | 例 `'-7.5'`。右＋／左− |
| hasira_sinzure_y | IFCTEXT | 柱の Y 方向芯ずれ量 | 例 `'7.5'`。上＋／下− |

### 始端・終端の決め方（横架材）
- 始終端の X 座標が同じ（Y 方向の材）：始端＝Y が小さい側、終端＝Y が大きい側
- それ以外：始端＝X が小さい側、終端＝X が大きい側

### syurui の値
- 柱類：`kuda` 管柱, `tooshi` 通し柱, `han` 半柱, `kaidan` 階段柱, `porch` ポーチ柱, `turizuka` 吊束, `jizuka` 地束, `yukazuka` 床束, `koyazuka` 小屋束
- 横架材類：`dodai` 土台, `oobiki` 大引き, `hiuchi` 火打ち, `hari` 梁, `moya` 母屋, `munagi` 棟木, `sumiki` 隅木, `taniki` 谷木, `nobori` 登梁
- 羽柄類：`mabasira` 間柱, `sujikai` 筋違, `madodai` 窓台, `madomagusa` まぐさ, `neda` 根太, `taruki` 垂木, `hafu` 破風, `hanakakushi` 鼻隠し, `hirokomai` 広小舞, `noboriyodo` 登り淀

### 横架材端部の値（siten_keijyou / syuuten_keijyou）
`ari` 蟻♂, `gyakuari` 逆蟻♂, `yoseari` 寄せ蟻♂, `ooire` 大入れ♂, `oobiki` 大引き♂,
`ketasasi` 桁差し♂, `dousasi` 胴差♂, `makurasasi` 枕♂,
`aritugiosu` 蟻継手♂, `aritugimesu` 蟻継手♀, `kamatugiosu` 鎌継♂, `kamatugimesu` 鎌継♀,
`okkakeosu` 追っかけ♂, `okkakemesu` 追っかけ♀, `daimotiosu` 台持ち♂, `daimotimesu` 台持ち♀,
`katto` カット

### 柱端部の値（joutan_keijyou / katan_keijyou）
`hirahozo` 平ほぞ, `yosehozo` 寄せほぞ, `kakuhozo` 角ほぞ（仕様書の表記は「各ほぞ」）, `katto` カット

## 仕様書の誤記と思われる箇所（扱い方）
- 本文中の `'sitan_keijyou'`・`'jyoutan_keijyou'` は、見出しのプロパティ名 `siten_keijyou`・`joutan_keijyou` の誤記とみなす。出力は見出しの名前を使う。
- joutan_keijyou / katan_keijyou の表記例が `IFCLABEL('tokuiti')` になっているが、値は上の柱端部リストから選ぶ。
- 表記例の行番号 `#9005` が複数のプロパティで重複しているのは例示上のもの。実際の IFC では行番号を重複させない。
- 今後プロパティが追加される可能性がある。未知のプロパティ名は警告に留め、エラーにしない。

## スクリプト

`scripts/cedxm_pset.py`（Python 3 標準ライブラリのみ）

- 生成：`python3 scripts/cedxm_pset.py gen input.json --start 9000 --targets 3000,3010`
  - input.json はプロパティ名→値の辞書。BOOLEAN は true/false、他は文字列か数値
  - 値をこの仕様で検証してから、IFCPROPERTYSINGLEVALUE / IFCPROPERTYSET / IFCRELDEFINESBYPROPERTIES の行を出力する
- 検証：`python3 scripts/cedxm_pset.py check model.ifc`
  - IFC 内の Cedxm_Pset_param に含まれるプロパティの型と値を検証し、問題を一覧にする

## 作業手順
1. 対象部材の種類（柱／横架材／羽柄材／木質系以外）を決める
2. 柱なら joutan/katan・hasira_w1/w2・hasira_sinzure_x/y、横架材なら siten/syuuten・w/h・sinzure を使う
3. スクリプトで生成または検証し、エラーがあれば値を直す
