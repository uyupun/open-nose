"""optimize.pyの実行結果を可視化・表示する。

pymooのResult/Problemオブジェクトには依存せず、表示用に変換済みの
プレーンなnumpy配列だけを受け取る(目的の順序はretention, pain, fit_gap
で固定、符号はすでに表示用=大きいほど良いとは限らないそのままの物理量に
戻してある前提。optimize.pyのOBJ_SIGNによる変換を参照)。可視化・表示
ロジックをGAの実行から切り離すことで、pymoo固有の内部構造(Result.history
の中身など)を知る必要があるのはこのファイルだけに閉じ込めている。
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

# 目的の表示名(グラフの軸ラベル)。retention, pain, fit_gapの順で固定
# (optimize.pyのFrameProblem._evaluateが組み立てる順序と同じ)
_OBJ_LABELS = ["retention (mm^2, 最大化)", "pain (mm, 最小化)", "fit_gap (mm, 最小化)"]

# 世代ごとの分布推移(plot_evolution)で重ね描きする世代数。多いほど密集して
# 判別できなくなるため、最初・最後を含む一部の世代だけ抽出する
_EVOLUTION_SNAPSHOTS = 6


def _sample_cmap(name: str, n: int) -> list[tuple[float, float, float]]:
    """matplotlibのカラーマップからn色を均等に抽出する(戻り値はRGBタプル)。"""
    cmap = plt.get_cmap(name)
    return [cmap(i / max(n - 1, 1))[:3] for i in range(n)]


def plot_evolution(generations: list[np.ndarray], out_path: Path) -> None:
    """世代ごとの集団の目的空間での分布推移を1枚の3D散布図に重ねて描く。

    generationsは世代ごとの目的値配列(表示用、retention/pain/fit_gapの
    順)のリスト。全世代を重ねると密集して判別できなくなるため、最初・
    最後を含む_EVOLUTION_SNAPSHOTS世代だけを等間隔に抽出し、世代が進む
    ほど紫→黄に変化するカラーマップ(viridis)で色分けする。可視化は
    pymoo.visualization.scatter.Scatter(pymoo組み込みの散布図
    ユーティリティ)を使う。
    """
    n_gen = len(generations)
    n_snapshots = min(_EVOLUTION_SNAPSHOTS, n_gen)
    indices = sorted(set(np.linspace(0, n_gen - 1, n_snapshots, dtype=int)))
    cmap = _sample_cmap("viridis", len(indices))

    plot = Scatter(
        title="世代ごとの集団の分布推移(目的空間)",
        labels=_OBJ_LABELS,
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


def print_summary(x: np.ndarray, f: np.ndarray, n_feasible: int, n_total: int) -> None:
    """最終世代の実行可能数と、パレートフロント全個体を表として表示する。

    xはパレートフロントの決定変数(FrameParamsの12変数の順)、fは対応する
    目的値(表示用、retention/pain/fit_gapの順)。
    """
    print(f"\n最終世代: 実行可能 {n_feasible}/{n_total} 個体")
    print(f"パレートフロント: {len(f)} 個体\n")

    # (見出し, 表示幅)。ヘッダーと各行のフォーマットを同じ定義から組み立て、
    # 幅がずれて表が崩れることを防ぐ。列数が増えた(issue #3)ため、各列の
    # 幅はclip_angle/arm_length時代より詰めている
    x_columns = [
        ("anchor_y", 8),
        ("heading", 8),
        ("len_1", 7),
        ("turn_2", 7),
        ("len_2", 7),
        ("turn_3", 7),
        ("len_3", 7),
        ("turn_4", 7),
        ("len_4", 7),
        ("thick", 7),
        ("hold_off", 9),
        ("grip_d", 7),
    ]
    f_columns = [("retention", 11), ("pain", 8), ("fit_gap", 9)]

    header = "".join(f"{label:>{w}}" for label, w in x_columns)
    header += " |" + "".join(f"{label:>{w}}" for label, w in f_columns)
    print(header)
    print("-" * len(header))

    for i in np.argsort(-f[:, 0]):
        row = "".join(f"{v:>{w}.2f}" for v, (_, w) in zip(x[i], x_columns))
        row += " |" + "".join(f"{v:>{w}.3f}" for v, (_, w) in zip(f[i], f_columns))
        print(row)
