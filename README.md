# OpenNose

- 鼻栓の民主化プロジェクト
- 快適さとスタイリッシュさ(機能美)を両立した鼻栓フレーム
- 簡略化した鼻モデルと遺伝的アルゴリズムによるパレート最適を目指す

## Scripts

```bash
# 依存パッケージをインストール
$ uv sync

# 鼻本体・鼻栓・フレームの既定構成一式を生成して output/base.glb に出力
$ uv run python scripts/export_model.py

# 生成した鼻モデルをインタラクティブビューアで確認
$ uv run python scripts/view_nose.py

# NSGA-IIでフレーム形状を最適化し、output/evolution.png に出力(パレートフロントは標準出力の表で確認)
$ uv run python scripts/optimize.py

# 上の表から選んだ候補(clip_angle等の5変数)をglTF(.glb)に出力(base.glbは上書きしない。ファイル名は実行時刻から自動生成、--output-nameで指定も可)
$ uv run python scripts/export_frame.py --clip-angle 5.74 --arm-length 10.25 --arm-thickness 2.13 --holder-offset 8.59 --grip-depth 0.63

# 出力した候補(export_frame.pyの出力等、任意のOBJ/glTFファイル)をインタラクティブビューアで確認
$ uv run python scripts/view_nose.py output/candidate_balanced.glb
```
