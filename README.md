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
  models/      # 元の設計: 鼻中隔付近のアーム + 鼻栓へ向かうコネクタ(両鼻を同時に挟む)
    frame_model.py / scene.py
  evaluation.py / optimize.py / optimize_report.py
  export_model.py / export_frame.py / view_nose.py   # 元の設計のスクリプト
output/
  models/    # 元の設計の出力(base.glb, evolution.png, candidate_*.glb)
  earrings/  # 鼻ピアス型の出力(base.glb, evolution.png, candidate_*.glb, 印刷用 *_frame_{left,right}.stl)
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
# --sort-by {retention,pain,fit_gap} で表の並び順を変えられる(ある目的に極振りした候補を先頭から拾う用)
$ uv run python scripts/earrings/optimize.py
$ uv run python scripts/earrings/optimize.py --sort-by fit_gap

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
