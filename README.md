# OpenNose

- 鼻栓の民主化プロジェクト
- 快適さとスタイリッシュさ(機能美)を両立した鼻栓フレーム
- 簡略化した鼻モデルと遺伝的アルゴリズムによるパレート最適を目指す

## 構成

```
scripts/
  commons/     # 設計に依らず共通で使うもの
    nose_model.py        # 簡略化した鼻本体モデル(NoseParams)
    plug_model.py        # 鼻栓(ティッシュ等)のプレースホルダー(PlugParams)
    rounded_triangle.py  # 鼻の断面(角丸三角形)の2D幾何プリミティブ
    viewer.py            # ビューア補助(半透明の描画順・カメラ調整)
    report.py            # NSGA-IIの結果表示(世代推移の図・パレートフロントの表)
  earrings/    # 鼻ピアス型(「b」字)フレーム: 片方の鼻ごとに独立したクリップ
    frame_model.py       # 形状(FrameParamsの6変数): 鼻翼を挟むリング + 鼻栓に刺すステム
    evaluation.py        # 評価関数(3目的 + 制約)
    scene.py             # 鼻本体・鼻栓・フレームを1つのSceneにまとめる
    optimize.py / export_model.py / export_frame.py / view_nose.py
  spiral/      # ゼンマイ(渦巻き)型フレーム: 鼻翼の外側にぶら下がるコイル + 鼻栓に刺すステム
    frame_model.py       # 形状(FrameParamsの6変数): 渦巻きのコイル + ステム
    evaluation.py        # 評価関数(3目的 + 制約)
    scene.py             # 鼻本体・鼻栓・フレームを1つのSceneにまとめる
    optimize.py / export_model.py / export_frame.py / view_nose.py
  dilator/     # 拡張ブリッジ型フレーム: 鼻腔拡張テープ(ブリーズライト等)のように鼻を押し開く平らなブリッジ + 鼻栓を受け入れる筒
    frame_model.py       # 形状(FrameParamsの8変数): 鼻を一定の曲率の円弧で横断する平らな薄いブリッジ(両端は両面テープの貼り代。印刷するときは平らに近い自然な形) + 左右の棒(アーチと同じ板の断面で、アーチの面からリングの面へねじれる平たいブレード。鼻翼の輪郭に沿って鼻孔まで約31mm) + 左右のリング(鼻中隔側を開いたC字の筒)(印刷・装着しやすいよう、帯の下縁をエッジクリップで挟む3部品構成)
    evaluation.py        # 評価関数(3目的: 拡張力・鼻栓の保持剛性・目立たなさ + 制約16個)
    scene.py             # 鼻本体・鼻栓・フレームを1つのSceneにまとめる
    optimize.py / export_model.py / export_frame.py / view_nose.py
  models/      # 元の設計: 鼻中隔付近のアーム + 鼻栓へ向かうコネクタ(両鼻を同時に挟む)
    frame_model.py / scene.py
  evaluation.py / optimize.py / optimize_report.py
  export_model.py / export_frame.py / view_nose.py   # 元の設計のスクリプト
output/
  models/    # 元の設計の出力(base.glb, evolution.png, candidate_*.glb)
  earrings/  # 鼻ピアス型の出力(base.glb, evolution.png, candidate_*.glb, 印刷用 *_frame_{left,right}.stl)
  spiral/    # ゼンマイ型の出力(base.glb, evolution.png, candidate_*.glb, 印刷用 *_frame_{left,right}.stl)
  dilator/   # 拡張ブリッジ型の出力(base.glb, evolution.png, candidate_*.glb, 印刷用 *_frame_bridge.stl / *_frame_leg_left.stl / *_frame_leg_right.stl)
```

新しい設計を足すときは、`earrings/`と同じ構成(frame_model・evaluation・scene・各スクリプト)のフォルダを`scripts/`直下に作り、鼻本体・鼻栓・ビューア・レポートは`commons/`のものを使う。

## Scripts

### 共通

```bash
# 依存パッケージをインストール
$ uv sync
```

### 鼻ピアス型(earrings)

```bash
# 鼻本体・鼻栓・フレームの既定構成一式を生成して output/earrings/base.glb に出力
$ uv run python scripts/earrings/export_model.py

# 生成した鼻モデルをインタラクティブビューアで確認(引数なしで既定形状)
$ uv run python scripts/earrings/view_nose.py

# NSGA-IIでフレーム形状を最適化し、output/earrings/evolution.png に出力(パレートフロントは標準出力の表で確認)
# --sort-by {retention,pain,visibility} で表の並び順を変えられる(ある目的に極振りした候補を先頭から拾う用)
$ uv run python scripts/earrings/optimize.py
$ uv run python scripts/earrings/optimize.py --sort-by visibility

# 上の表から選んだ行の6変数(ring_r ring_gap ring_t ring_d stem_len stem_t)をglTF(.glb)に出力
# (base.glbは上書きしない。ファイル名は実行時刻から自動生成、--output-nameで指定も可)
$ uv run python scripts/earrings/export_frame.py --ring-radius 3.04 --ring-gap-deg 92.13 --ring-thickness 2.47 --ring-depth 0.85 --stem-length 3.84 --stem-thickness 1.09 --output-name candidate_balanced.glb

# --stl を付けると、フレーム(左右)だけを3Dプリント用STLとしても書き出す
# (output/earrings/<出力名>_frame_left.stl / _frame_right.stl、単位mm)
$ uv run python scripts/earrings/export_frame.py --ring-radius 3.04 --ring-gap-deg 92.13 --ring-thickness 2.47 --ring-depth 0.85 --stem-length 3.84 --stem-thickness 1.09 --output-name candidate_balanced.glb --stl

# 出力した候補(glb)や、フレーム単体のSTLをインタラクティブビューアで確認
$ uv run python scripts/earrings/view_nose.py output/earrings/candidate_balanced.glb
$ uv run python scripts/earrings/view_nose.py output/earrings/candidate_balanced_frame_left.stl
```

### ゼンマイ型(spiral)

```bash
# 鼻本体・鼻栓・フレームの既定構成一式を生成して output/spiral/base.glb に出力
$ uv run python scripts/spiral/export_model.py

# 生成した鼻モデルをインタラクティブビューアで確認(引数なしで既定形状)
$ uv run python scripts/spiral/view_nose.py

# NSGA-IIでフレーム形状を最適化し、output/spiral/evolution.png に出力(パレートフロントは標準出力の表で確認)
# --sort-by {visibility,weight,turns} で表の並び順を変えられる(ある目的に極振りした候補を先頭から拾う用)
$ uv run python scripts/spiral/optimize.py
$ uv run python scripts/spiral/optimize.py --sort-by weight

# 上の表から選んだ行の6変数(turns start_r end_r coil_t stem_t stem_len)をglTF(.glb)に出力
# (base.glbは上書きしない。ファイル名は実行時刻から自動生成、--output-nameで指定も可)
$ uv run python scripts/spiral/export_frame.py --turns 0.73 --start-radius 7.42 --end-radius 2.95 --coil-thickness 1.80 --stem-thickness 0.58 --stem-length 8.06 --output-name candidate_balanced.glb

# --stl を付けると、フレーム(左右)だけを3Dプリント用STLとしても書き出す
# (output/spiral/<出力名>_frame_left.stl / _frame_right.stl、単位mm)
$ uv run python scripts/spiral/export_frame.py --turns 0.73 --start-radius 7.42 --end-radius 2.95 --coil-thickness 1.80 --stem-thickness 0.58 --stem-length 8.06 --output-name candidate_balanced.glb --stl

# 出力した候補(glb)や、フレーム単体のSTLをインタラクティブビューアで確認
$ uv run python scripts/spiral/view_nose.py output/spiral/candidate_balanced.glb
$ uv run python scripts/spiral/view_nose.py output/spiral/candidate_balanced_frame_left.stl
```

### 拡張ブリッジ型(dilator)

```bash
# 鼻本体・鼻栓・フレームの既定構成一式を生成して output/dilator/base.glb に出力
$ uv run python scripts/dilator/export_model.py

# 生成した鼻モデルをインタラクティブビューアで確認(引数なしで既定形状)
$ uv run python scripts/dilator/view_nose.py

# NSGA-IIでフレーム形状を最適化し、output/dilator/evolution.png に出力(パレートフロントは標準出力の表で確認)
# --sort-by {extension_force,plug_hold,inconspicuousness} で表の並び順を変えられる(ある目的に極振りした候補を先頭から拾う用)
$ uv run python scripts/dilator/optimize.py
$ uv run python scripts/dilator/optimize.py --sort-by plug_hold

# 上の表から選んだ行の8変数(nat_r tab_pos bridge_y bridge_w bridge_t leg_t collar_l detent)をglTF(.glb)に出力
# (base.glbは上書きしない。ファイル名は実行時刻から自動生成、--output-nameで指定も可)
$ uv run python scripts/dilator/export_frame.py --natural-radius 76.59 --tab-side-ratio 1.27 --bridge-y 13.45 --bridge-width 4.54 --bridge-thickness 1.22 --leg-thickness 3.48 --collar-length 2.16 --clip-detent 0.37 --output-name candidate_balanced.glb

# --stl を付けると、フレームを3Dプリント用STLとしても書き出す。印刷しやすい
# ように、ブリッジ(鼻筋のアーチ状の帯)・左の脚(棒とリング)・右の脚(棒と
# リング)の3つの別々のファイルになる(output/dilator/<出力名>_frame_bridge.stl・
# _frame_leg_left.stl・_frame_leg_right.stl、単位mm)。ブリッジのSTLは、装着
# した形ではなく平らに近い自然な形(曲率半径natural_radiusの円弧)で、鼻の上で
# 曲げて両端を医療用両面テープで貼ると、曲げ戻ろうとする力がブリーズライトの
# ように小鼻を引き上げる。帯は鼻の上で一定の曲率の円弧になり、鼻の角に沿って
# 丸まらない(鼻の形が違っても両端さえ肌に届けば貼れる)。両端は鼻の側面の
# 背面寄りまで届く(長さ約31mm)。脚はそれぞれ別々に
# プリントし、先端のC字のクリップを帯の下縁に押し込んで組み立てる(差し口は
# 面取りしてあり、外側の顎の突起が帯の小さな丸穴に落ちて位置が決まる。外す
# ときは引き抜くだけ)。棒は鼻の側面を小鼻の外側の輪郭(鼻翼)に沿って降り、
# 鼻中隔側を開いたC字のリングにつながる。この設計では鼻栓は鼻の下端から約6.5mm
# 飛び出している想定で、リングはその露出端を掴む
$ uv run python scripts/dilator/export_frame.py --natural-radius 76.59 --tab-side-ratio 1.27 --bridge-y 13.45 --bridge-width 4.54 --bridge-thickness 1.22 --leg-thickness 3.48 --collar-length 2.16 --clip-detent 0.37 --output-name candidate_balanced.glb --stl

# 出力した候補(glb)や、部品単体のSTLをインタラクティブビューアで確認
$ uv run python scripts/dilator/view_nose.py output/dilator/candidate_balanced.glb
$ uv run python scripts/dilator/view_nose.py output/dilator/candidate_balanced_frame_bridge.stl
```

### 元の設計(アーム + コネクタ)

```bash
# 鼻本体・鼻栓・フレームの既定構成一式を生成して output/models/base.glb に出力
$ uv run python scripts/export_model.py

# 生成した鼻モデルをインタラクティブビューアで確認
$ uv run python scripts/view_nose.py

# NSGA-IIでフレーム形状を最適化し、output/models/evolution.png に出力(パレートフロントは標準出力の表で確認)
$ uv run python scripts/optimize.py

# 上の表から選んだ候補(11変数)をglTF(.glb)に出力(base.glbは上書きしない)
$ uv run python scripts/export_frame.py --connector-heading 24 --connector-length-1 5.5 --arm-thickness 2.0 --holder-offset 12 --grip-depth 0.5

# 出力した候補をインタラクティブビューアで確認
$ uv run python scripts/view_nose.py output/models/candidate_balanced.glb
```
