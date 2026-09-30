# OpenNose

- 鼻栓の民主化プロジェクト
- 鼻に詰めたティッシュ(鼻栓)を、「隠すもの」から「装うもの」へ。鼻栓を、身近なものにする
- 簡略化した鼻モデルと遺伝的アルゴリズム(NSGA-II)で、形のトレードオフ(パレート最適)を探る
- 現在の主案は[水引型](#水引型現在の主案)(`scripts/mizuhiki/`)。鼻ピアス型・ゼンマイ型・拡張ブリッジ型・元の設計は、これまでに試した方向

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
    frame_model.py       # 形状(FrameParamsの8変数): 鼻の前面と側面に沿って横断する平らな薄いブリッジ(両端は巻き込まずまっすぐ伸ばし、両面テープの貼り代にする。印刷するときは同じアーチを少し開いた自然な形) + 左右の棒(アーチと同じ板の断面で、アーチの面からリングの面へねじれる平たいブレード。鼻翼の輪郭に沿って鼻孔まで約31mm) + 左右のリング(鼻中隔側を開いたC字の筒)(印刷・装着しやすいよう3部品に分け、脚の上端の小さなC字が帯の上下の縁を抱いて連結する)
    evaluation.py        # 評価関数(3目的: 拡張力・鼻栓の保持剛性・目立たなさ + 制約16個)
    scene.py             # 鼻本体・鼻栓・フレームを1つのSceneにまとめる
    optimize.py / export_model.py / export_frame.py / view_nose.py
  mizuhiki/    # 水引型: 丸めたティッシュ(鼻栓)に着け、3本の紐の帯がティッシュを1周する輪から小鼻の外側へ上がって、あわじ結び(三つ輪)になる器具。結びを小鼻の前寄り(鼻の側面)に置き、正面からも横顔からも水引と読める。濃い色で刷ると、結びが鼻の穴の両脇を縁取り、小鼻の輪郭にも見える
    frame_model.py       # 形状(MizuhikiParamsの5変数: 結びの大きさ・高さ・小鼻の上の位置、紐の太さ、端の長さ)。紐の肌の側をつなぐ板と、輪の底を平らに削る補強でFDMで刷れる
    evaluation.py        # 評価関数(3目的: 横顔での存在感・正面での読みやすさ・ティッシュをつかむ面積 + 制約13個)
    scene.py             # 鼻本体・鼻栓・器具を1つのSceneにまとめる
    optimize.py / export_model.py / export_frame.py / view_nose.py
  models/      # 元の設計: 鼻中隔付近のアーム + 鼻栓へ向かうコネクタ(両鼻を同時に挟む)
    frame_model.py / scene.py
  evaluation.py / optimize.py / optimize_report.py
  export_model.py / export_frame.py / view_nose.py   # 元の設計のスクリプト
output/
  models/    # 元の設計の出力(base.glb, evolution.png, candidate_*.glb)
  earrings/  # 鼻ピアス型の出力(base.glb, evolution.png, candidate_*.glb, 印刷用 *_frame_{left,right}.stl)
  spiral/    # ゼンマイ型の出力(base.glb, evolution.png, candidate_*.glb, 印刷用 *_frame_{left,right}.stl)
  mizuhiki/  # 水引型の出力(base.glb, evolution.png, pareto.csv, candidate_*.glb, 印刷用 *_{left,right}_print.stl)
  dilator/   # 拡張ブリッジ型の出力(base.glb, evolution.png, candidate_*.glb, 印刷用 *_frame_bridge.stl / *_frame_leg_left.stl / *_frame_leg_right.stl)
```

新しい設計を足すときは、`earrings/`と同じ構成(frame_model・evaluation・scene・各スクリプト)のフォルダを`scripts/`直下に作り、鼻本体・鼻栓・ビューア・レポートは`commons/`のものを使う。

## 水引型(現在の主案)

丸めたティッシュ(鼻栓)に着ける小さな器具。3本の紐を平らに並べた帯がティッシュのまわりを1周して輪になり(輪にティッシュを通して留める)、小鼻の外側を上がって、あわじ結び(三つ輪)になる。結びの下からは端が垂れる。

水引は、ご祝儀袋やお見舞いの包みで誰もが目にする結びで、性別を問わず使われる。鼻栓に水引を添えることで、見られたくないものを、見覚えのある贈り物の飾りに変える。ティッシュを通す輪だけの形(鼻の下のキャップ)は人の目に留まらず、見え方を変えられなかったので、結びを小鼻の上に出して見せている。

- **結びの位置**: 小鼻の横ではなく、正面を斜めに向いた鼻の側面に置く。最初の試作を着けてみると、小鼻の横の結びは正面から真横に見えて、三つ輪がつぶれて読めなかった。人に見られるのはほとんど正面からなので、正面から水引と分かる位置に出した。結びの内側の端は、正面から見て鼻の穴の中心の線までに収め、鼻頭には乗せない
- **色**: 濃い色(焦げ茶・濃紺など)で刷ると、結びが鼻の穴の両脇を縁取り、小鼻の輪郭にも見える(見立て)。黒は水引では弔事(黒白)の色なので、描画では焦げ茶にしている
- **大きさ**: 結びの大きさは評価関数では決めず、見た目の塩梅で決める。どの目的も「大きいほど見える」ので、探索させると上限に張り付くため。いまは最初に刷った形の1.1倍(`optimize.py --knot-scale`で変えられる)

### 評価関数(`scripts/mizuhiki/evaluation.py`)

目的は3つで、いずれも大きいほど良い。

| 目的 | 測るもの |
|---|---|
| 横顔での存在感 | 真横から見える、輪より上(渡り・結び・端)の面積 |
| 正面での読みやすさ | 正面から見える、結びと端の面積 |
| ティッシュをつかむ面積 | 輪の内側の面積(紐が太いほど輪が高く、よくつかむ) |

見える面積は、鼻の陰に隠れる部分を除いて測る。結びの位置が小鼻の横に寄るほど横顔で、鼻の側面に寄るほど正面で見え、この向きが1つ目と2つ目のトレードオフになる。

制約は13個で、すべて満たす形だけを候補にする。

- 結びが読める: 三つ輪の穴が、横顔からも正面からも抜けて見える(紐を太く・結びを小さくすると穴が潰れる)
- 鼻頭に乗らない: 正面から見て、結びの内側の端が鼻の穴の中心の線を越えない
- 肌・顔との関係: 紐が肌に近づきすぎない、結びが肌から浮かず小鼻の面に乗る、頬に当たらない、小鼻の上端を越えない、鼻の下へ垂れない、左右の器具が当たらない
- FDM(0.4mmノズル)で刷れる: 紐の直径0.8mm以上、紐のつなぎ目の厚み0.6mm以上、輪の底がベッドに着く面積

閾値はいずれも暫定値で、刷って着けながら見直していく。

### いまのおすすめ

`candidate_frontal`(結びの大きさ1.74・高さ2.30・位置1.30・紐の半径0.455mm)。最初に刷った形(小鼻の横に結び)と比べて、正面での読みやすさが約2.4倍(27.8→67.2mm^2)になり、横顔での存在感はほぼ保っている(85.2→80.5mm^2)。結びの内側の端は、鼻の穴の中心の線の0.65mm手前。

`output/mizuhiki/base.glb`(既定値の形)は、最初に手で決めた形のまま。いまの評価では、結びの後ろの輪が頬に当たり、正面から三つ輪が読めない。

### 刷り方(Bambu Studio・FDM 0.4mmノズル)

試作はPLAで刷っている。器具は左右とも約15×16×14mm、片側約0.2g。

- **STL**: `candidate_frontal_left_print.stl`・`candidate_frontal_right_print.stl`。輪の底面をベッドに置き、着けたときの上を上にした向きで書き出してある(6方向を比べて、サポートの要る面が最も少ない向き)。読み込んだ向きのまま使い、自動配置はしない
- **品質**: 層の高さ0.12mm前後、壁生成はArachne(0.6mm前後の紐のつなぎ目を1本の線に丸めずに出す)
- **ブリム**: 外側のみ、幅3〜5mm。ベッドに着くのは輪の底の細い環だけなので
- **冷却**: 左右を離して並べ、冷却のため速度を落とす設定をオンにする(小さい部品は1層がすぐ終わり、冷えきらずにだれる)
- **サポート**: タイプを「ツリー(手動)」にし、サポートペイント(L)で、次の3か所の紐の下側だけを強制で塗る(左右それぞれ)。どれも真下はベッドまで空いているので、「ビルドプレートのみ」はオンでよい
  - 結びから垂れる端の先(高さ約1.7mm)
  - 結びの下の輪のいちばん下(高さ約3.3mm)
  - 結びの上の輪の張り出し(高さ約8.6〜9.0mm)

  自動にすると、三つ輪の中の1mm前後の橋渡し(支えなしで刷れる)にまで枝が入り込み、外しにくく紐を折りやすい。塗る場所は、一度スライスしてプレビューの層スライダーを上の高さに合わせると、宙に浮いて始まる紐として見つかる
- **サポートの外し方**: 完全に冷めてから、ベッド側の太い幹を先にニッパーで切り、紐に付いた先端は、その紐のすぐ横を押さえて小さく揺らして外す。器具は太い輪の部分を持ち、結びは持たない

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

# 上の表から選んだ行の8変数(nat_r tab_pos bridge_y bridge_w bridge_t leg_t collar_l detent。detentは--cuff-detent)をglTF(.glb)に出力
# (base.glbは上書きしない。ファイル名は実行時刻から自動生成、--output-nameで指定も可)
$ uv run python scripts/dilator/export_frame.py --natural-radius 25.96 --tab-side-ratio 1.20 --bridge-y 14.99 --bridge-width 4.06 --bridge-thickness 1.40 --leg-thickness 3.32 --collar-length 2.08 --cuff-detent 0.12 --output-name candidate_balanced.glb

# --stl を付けると、フレームを3Dプリント用STLとしても書き出す。印刷しやすい
# ように、ブリッジ(鼻筋のアーチ状の帯)・左の脚(棒とリング)・右の脚(棒と
# リング)の3つの別々のファイルになる(output/dilator/<出力名>_frame_bridge.stl・
# _frame_leg_left.stl・_frame_leg_right.stl、単位mm)。ブリッジのSTLは、装着
# した形そのものではなく、同じアーチの曲がりを弱めた(少し開いた)自然な形で、
# 鼻の上で曲げて両端を医療用両面テープで貼ると、曲げ戻ろうとする力がブリーズ
# ライトのように小鼻を引き上げる。帯は鼻の前面の丸みと側面に沿うアーチで、両端は
# 鼻の角に沿って巻き込まず、側面の向きのまままっすぐ伸びる(長さ約27mm)。脚は
# それぞれ別々にプリントし、帯を抱くCで組み立てる: 脚の上端は棒と同じ幅の小さな
# C字で、帯の上下の縁に掘ったV溝に爪を入れて帯を抱く。帯の端から滑り込ませ、端寄りの
# 浅い段をカチッと越えると止まる(テープを貼った後でも付け外しできる。爪は帯の厚みの
# 内側で止まり、肌と帯の間には入らない)。
# 棒は鼻の側面を小鼻の外側の輪郭(鼻翼)に沿って降り、鼻中隔側を開いたC字のリングに
# つながる。この設計では鼻栓は鼻の下端から約6.5mm
# 飛び出している想定で、リングはその露出端を掴む
$ uv run python scripts/dilator/export_frame.py --natural-radius 25.96 --tab-side-ratio 1.20 --bridge-y 14.99 --bridge-width 4.06 --bridge-thickness 1.40 --leg-thickness 3.32 --collar-length 2.08 --cuff-detent 0.12 --output-name candidate_balanced.glb --stl

# 出力した候補(glb)や、部品単体のSTLをインタラクティブビューアで確認
$ uv run python scripts/dilator/view_nose.py output/dilator/candidate_balanced.glb
$ uv run python scripts/dilator/view_nose.py output/dilator/candidate_balanced_frame_bridge.stl
```

### 水引型(mizuhiki)

```bash
# 鼻本体・鼻栓・器具の既定構成一式(最初に手で決めた水引の形)を生成して output/mizuhiki/base.glb に出力
$ uv run python scripts/mizuhiki/export_model.py

# 生成した鼻モデルをインタラクティブビューアで確認(引数なしで既定形状)
$ uv run python scripts/mizuhiki/view_nose.py

# NSGA-IIで結びの高さ・小鼻の上の位置・紐の太さを最適化する(40個体×40世代で約7分)。結びの大きさは
# 探索せず --knot-scale で与える(既定1.74)。目的は横顔での存在感・正面での読みやすさ・ティッシュを
# つかむ面積の3つ、制約は13個(scripts/mizuhiki/evaluation.py)。output/mizuhiki/ に次を出力する:
#   evolution.png(世代ごとの分布推移)、pareto.csv(パレートフロントの全個体の変数・目的・制約)、
#   candidate_presence.glb(横顔での存在感が最大)・candidate_frontal.glb(正面で最も読みやすい)・
#   candidate_balanced.glb(3つの目的をパレートフロントの中で0〜1にそろえ、理想点に最も近いもの。
#   目的の差が小さいと、わずかな差に引っ張られるので、表やpareto.csvと見比べて選ぶ)
# パレートフロントの表は標準出力にも出る。--sort-by {profile_presence,frontal_legibility,tissue_grip} で並び順を変えられる
$ uv run python scripts/mizuhiki/optimize.py
$ uv run python scripts/mizuhiki/optimize.py --knot-scale 1.6

# 設計変数を指定してglTF(.glb)に出力し、評価関数の結果(目的3つと制約13個の合否)を表示する。
# 引数を省略した変数は既定値。上の表やpareto.csvから選んだ行の値を渡す(base.glbは上書きしない。
# ファイル名は実行時刻から自動生成、--output-nameで指定も可)
$ uv run python scripts/mizuhiki/export_frame.py
$ uv run python scripts/mizuhiki/export_frame.py --knot-scale 1.74 --knot-y 2.3006 --knot-f 1.2960 --cord-radius 0.4553 --output-name candidate_frontal

# --print を付けると、器具(左右)をそのまま刷れる向き(輪の底面をベッドに置き、着けたときの上を上にする)の
# STLとしても書き出す(<出力名>_left_print.stl / _right_print.stl、単位mm)。FDM(0.4mmノズル)向けに、並べた
# 紐の肌の側を板でつなぎ(つなぎ目の厚み0.6mm以上)、輪の底を0.2mm平らに削ってある。刷るときはツリー
# サポート(手動で3か所を塗る。上の「刷り方」参照)とブリムを使う。--stl で鼻に着けた向きのSTLも書き出せる
$ uv run python scripts/mizuhiki/export_frame.py --knot-scale 1.74 --knot-y 2.3006 --knot-f 1.2960 --cord-radius 0.4553 --output-name candidate_frontal --print

# 出力した候補(glb)や、器具単体のSTLをインタラクティブビューアで確認
$ uv run python scripts/mizuhiki/view_nose.py output/mizuhiki/candidate_frontal.glb
$ uv run python scripts/mizuhiki/view_nose.py output/mizuhiki/candidate_frontal_right_print.stl
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
