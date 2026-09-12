"""NSGA-II(optimize.py)の実行結果を可視化・表示する、設計に依らない補助。

pymooのResult/Problemオブジェクトには依存せず、表示用に変換済みの
プレーンなnumpy配列だけを受け取る(目的の符号はすでに表示用=そのままの
物理量に戻してある前提。各設計のoptimize.pyのOBJ_SIGNによる変換を参照)。
目的の名前・設計変数の列名は設計ごとに違うため、引数で受け取る。
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from pymoo.visualization.scatter import Scatter

# matplotlibの既定フォント(DejaVu Serif)は日本語グリフを持たず、グラフの
# タイトル・凡例が豆腐(文字化け)になる。pymoo.core.plot.Plotがコンストラクタ
# 内でfont.family="serif"を強制上書きするため、font.familyではなくfont.serif
# (family="serif"時の実フォント解決先)にmacOS標準搭載のCJK対応フォントを
# 設定する必要がある
matplotlib.rcParams["font.serif"] = ["Hiragino Mincho ProN"]

# 世代ごとの分布推移(plot_evolution)で重ね描きする世代数。多いほど密集して
# 判別できなくなるため、最初・最後を含む一部の世代だけ抽出する
_EVOLUTION_SNAPSHOTS = 6

# print_summaryの並べ替え指定(sort_keys引数)の型: 目的の名前 → (fの列番号,
# 大きい順に並べるか=最大化目的か)。「ある目的に極振りした候補」を表の
# 先頭から拾えるようにするためのもの。パレートフロントは目的ごとの極端を
# 全て含んでいるので、極振りのために別途GAを回し直す必要はない。目的の
# 名前・向きは設計ごとに違うため、各設計のoptimize.pyが定義して渡す
SortKeys = dict[str, tuple[int, bool]]


def _sample_cmap(name: str, n: int) -> list[tuple[float, float, float]]:
    """matplotlibのカラーマップからn色を均等に抽出する(戻り値はRGBタプル)。"""
    cmap = plt.get_cmap(name)
    return [cmap(i / max(n - 1, 1))[:3] for i in range(n)]


def plot_evolution(
    generations: list[np.ndarray], out_path: Path, labels: list[str]
) -> None:
    """世代ごとの集団の目的空間での分布推移を1枚の3D散布図に重ねて描く。

    generationsは世代ごとの目的値配列(表示用)のリスト、labelsは目的の
    表示名(軸ラベル、目的の順)。全世代を重ねると密集して判別できなく
    なるため、最初・最後を含む_EVOLUTION_SNAPSHOTS世代だけを等間隔に
    抽出し、世代が進むほど紫→黄に変化するカラーマップ(viridis)で
    色分けする。可視化はpymoo.visualization.scatter.Scatter(pymoo組み込み
    の散布図ユーティリティ)を使う。
    """
    n_gen = len(generations)
    n_snapshots = min(_EVOLUTION_SNAPSHOTS, n_gen)
    indices = sorted(set(np.linspace(0, n_gen - 1, n_snapshots, dtype=int)))
    cmap = _sample_cmap("viridis", len(indices))

    plot = Scatter(
        title="世代ごとの集団の分布推移(目的空間)",
        labels=labels,
        figsize=(9, 8),
        legend=True,
    )
    for color, gen_idx in zip(cmap, indices):
        plot.add(
            generations[gen_idx],
            color=color,
            label=f"gen {gen_idx + 1}",
            s=20,
            alpha=0.7,
        )
    plot.save(str(out_path))


def print_summary(
    x: np.ndarray,
    f: np.ndarray,
    n_feasible: int,
    n_total: int,
    x_columns: list[tuple[str, int]],
    f_columns: list[tuple[str, int]],
    sort_keys: SortKeys,
    sort_by: str,
) -> None:
    """最終世代の実行可能数と、パレートフロント全個体を表として表示する。

    xはパレートフロントの決定変数、fは対応する目的値(表示用)。x_columns/
    f_columnsは(見出し, 表示幅)のリストで、ヘッダーと各行のフォーマットを
    同じ定義から組み立てることで幅がずれて表が崩れることを防ぐ。sort_by
    で指定した目的(sort_keys参照)が良い順に並べる。
    """
    print(f"\n最終世代: 実行可能 {n_feasible}/{n_total} 個体")
    print(f"パレートフロント: {len(f)} 個体\n")

    header = "".join(f"{label:>{w}}" for label, w in x_columns)
    header += " |" + "".join(f"{label:>{w}}" for label, w in f_columns)
    print(header)
    print("-" * len(header))

    column, descending = sort_keys[sort_by]
    order = np.argsort(-f[:, column] if descending else f[:, column])
    for i in order:
        row = "".join(f"{v:>{w}.2f}" for v, (_, w) in zip(x[i], x_columns))
        row += " |" + "".join(f"{v:>{w}.3f}" for v, (_, w) in zip(f[i], f_columns))
        print(row)
