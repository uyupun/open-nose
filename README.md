# OpenNose

- 鼻栓の民主化プロジェクト
- 快適さとスタイリッシュさ(機能美)を両立した鼻栓フレーム
- 簡略化した鼻モデルと遺伝的アルゴリズムによるパレート最適を目指す

## Scripts

```bash
# 依存パッケージをインストール
$ uv sync

# 鼻モデルを生成して output/nose.obj に出力
$ uv run python scripts/nose_model.py

# 生成した鼻モデルをインタラクティブビューアで確認
$ uv run python scripts/view_nose.py
```
