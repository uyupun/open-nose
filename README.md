# OpenNose

鼻栓の民主化プロジェクト。快適さとスタイリッシュさを両立する鼻栓フレームを、
簡略化した鼻モデルと多目的最適化(遺伝的アルゴリズム)で探索する実験。

## Scripts

```bash
# 依存パッケージをインストール
$ uv sync

# 鼻モデルを生成して output/nose.obj に出力
$ uv run python scripts/nose_model.py

# 生成した鼻モデルをインタラクティブビューアで確認
$ uv run python scripts/view_nose.py
```
