"""NSGA-II(pymoo)によるゼンマイ型フレーム形状の多目的最適化スクリプト。

evaluate_frame/constraint_values(scripts/spiral/evaluation.py)をpymooの
Problemでラップし、FrameParamsの6設計変数を探索してパレートフロントを
求める。可視化・結果表示はcommons/report.py側の責務とし、このファイルは
実行(FrameProblemの定義とminimize()の呼び出し)だけを持つ
(earrings/optimize.pyと同じ構成)。

## 目的関数の符号

pymooは最小化のみを扱う。visibility・turnsは最大化したい目的なので、
OBJ_SIGN([-1, 1, -1])を使い、weight以外の符号を反転する。

## 探索範囲(_SEARCH_SPACEの根拠)

FrameParams.__post_init__が要求する下限(いずれも正の値であること)は
そのまま使う。上限は物理的な基準が明示されていない変数が多く、以下の
考え方で仮置きした(GAを実際に動かしながら見直す前提の暫定値。
scripts/spiral/frame_model.pyのモジュールdocstring「幾何」参照):

- turns: 最初は下限1.0・上限3.5(turns・start_radius・coil_thicknessが
  大きいほど経路長(=weight)が増えるため、あまり大きくすると重さが
  支配的になり実用に耐えないという考え方だった)、ユーザー指摘「元の
  添付画像くらい1周半くらいで」を受けて1.2〜1.8に狭め、続いて「もっと
  渦巻き少なくていいや。半周くらいで」との指摘で0.4〜0.7に、さらに
  「0.75周にできる?」との指摘で0.6〜0.9に調整した(0.75を範囲の中央に
  し、GAに多少の探索の余地は残す)
- start_radius: 下限3.0mm(渦の外径が小さすぎると見た目の主張が弱い)。
  上限8.0mmは、earrings.optimize.pyのring_radius上限と同じ理由
  (実物の鼻ピアスに近いサイズ感)
- end_radius: 下限0.5mm(渦の中心が尖りすぎない最小限)。上限3.0mmは
  start_radius(上限8.0)に対してradius_order_margin
  (_MIN_RADIUS_DROP=1.0mm差)を満たす余地を残すための暫定値
- coil_thickness: stem_thicknessと独立の変数に分けた(以前は共通の
  wire_thickness、frame_model.pyのモジュールdocstring参照)。下限を
  earrings.optimize.pyのring_thicknessと同じ0.8mmにしたところ、weight
  (体積、最小化)しか太さに効く目的がないため、GAが下限付近(0.8〜0.9mm
  程度)に張り付いてしまい、ユーザー指摘「評価後が細すぎる」の通りに
  なった(earringsのring_thicknessはretention∝線径^4という「太いほど
  有利」な目的があったため下限に張り付かなかった、という違い)。
  visibility/turnsに太さは効かないため、この設計では下限を実際に見た目が
  太いと感じられる水準まで引き上げるしかない。1.4mm(旧wire_thicknessの
  既定値、earringsのring_thicknessの既定値でもある)を下限にしたが、
  GAが常に下限付近に張り付く(=coil_thicknessに関して探索する意味が
  ほぼない)ことは変わらないため、ユーザー指摘「もう少し太くできる?」を
  受けて下限をさらに1.8mmへ引き上げた。上限2.5mmは変更なし
  (earrings.optimize.pyのring_thicknessの上限=実際の鼻ピアスの線材の
  太さの目安と同じ)
- stem_thickness: earrings.optimize.pyのstem_thicknessと同じ根拠・同じ
  範囲(下限0.5mm、上限2.0mmはcoil_thicknessの上限引き下げに合わせた
  値で、thickness_order_marginと矛盾しない)
- stem_length: earrings.optimize.pyのstem_lengthと同じ根拠(下限6.0mmは
  鼻栓の下部から刺さる分の余裕を見た最低限の長さ、上限16.0mmは鼻栓の
  奥の端を突き抜ける境界の少し外側)
"""

import argparse
import sys
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/spiral/xxx.py`で
# 実行するとsys.path[0]はscripts/spiral/になり、commons/spiralパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from pymoo.algorithms.moo.nsga2 import NSGA2  # noqa: E402
from pymoo.core.problem import Problem  # noqa: E402
from pymoo.optimize import minimize  # noqa: E402

from commons.nose_model import NoseParams, build_nose_body  # noqa: E402
from commons.plug_model import PlugParams  # noqa: E402
from commons.report import SortKeys, plot_evolution, print_summary  # noqa: E402
from spiral.evaluation import constraint_values, evaluate_frame  # noqa: E402
from spiral.export_model import OUTPUT_DIR  # noqa: E402
from spiral.frame_model import (  # noqa: E402
    FrameParams,
    validate_follow_height,
    validate_target_reach,
)

# 探索変数(名前, 下限, 上限)。FrameParamsのフィールド順と揃える(この順で
# FrameProblem._evaluateがFrameParamsを組み立てる)。根拠はモジュール
# docstring参照
_SEARCH_SPACE: list[tuple[str, float, float]] = [
    ("turns", 0.6, 0.9),
    ("start_radius", 3.0, 8.0),
    ("end_radius", 0.5, 3.0),
    ("coil_thickness", 1.8, 2.5),
    ("stem_thickness", 0.5, 2.0),
    ("stem_length", 6.0, 16.0),
]
_VAR_NAMES = [name for name, _, _ in _SEARCH_SPACE]
_XL = np.array([lo for _, lo, _ in _SEARCH_SPACE])
_XU = np.array([hi for _, _, hi in _SEARCH_SPACE])

# 目的(visibility, weight, turns)の符号。pymooは最小化のみ扱うため、
# 最大化したいvisibility・turnsだけ反転する(モジュールdocstring参照)
OBJ_SIGN = np.array([-1.0, 1.0, -1.0])

# 目的の表示名(グラフの軸ラベル)。visibility, weight, turnsの順で固定
# (FrameProblem._evaluateが組み立てる順序と同じ)
_OBJ_LABELS = [
    "visibility (コイルの突き出し mm, 最大化)",
    "weight (コイル+ステムの体積 mm^3, 最小化)",
    "turns (渦の巻き数, 最大化)",
]
# print_summaryの並べ替え指定: 目的の名前 → (列番号, 大きい順か)。
# OBJ_SIGN・_OBJ_LABELSと同じ順序・向き
_SORT_KEYS: SortKeys = {
    "visibility": (0, True),
    "weight": (1, False),
    "turns": (2, True),
}
# パレートフロントの表の(見出し, 表示幅)。_SEARCH_SPACEの変数順・目的順
_X_COLUMNS = [
    ("turns", 7),
    ("start_r", 8),
    ("end_r", 7),
    ("coil_t", 7),
    ("stem_t", 7),
    ("stem_len", 9),
]
_F_COLUMNS = [("visibility", 11), ("weight", 9), ("turns", 7)]


class FrameProblem(Problem):
    """FrameParamsの6変数を探索するpymoo Problem。plug/noseは固定。"""

    def __init__(self, plug: PlugParams, nose: NoseParams):
        # frameに依存しない検証(問題設定そのものの誤り)は、GAを回す前に
        # 一度だけ確認しておく(earrings/optimize.pyと同じ理由)
        validate_target_reach(plug, nose)
        validate_follow_height(nose, build_nose_body(nose))

        super().__init__(n_var=6, n_obj=3, n_ieq_constr=6, xl=_XL, xu=_XU)
        self.plug = plug
        self.nose = nose

    def _evaluate(self, x: np.ndarray, out: dict, *args, **kwargs) -> None:
        objectives = np.empty((len(x), self.n_obj))
        constraints = np.empty((len(x), self.n_ieq_constr))
        for i, row in enumerate(x):
            frame = FrameParams(**dict(zip(_VAR_NAMES, row)))
            score = evaluate_frame(frame, self.plug, self.nose)
            objectives[i] = OBJ_SIGN * [score.visibility, score.weight, score.turns]
            constraints[i] = constraint_values(score)
        out["F"] = objectives
        out["G"] = constraints


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pop-size", type=int, default=50)
    parser.add_argument("--n-gen", type=int, default=60)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--sort-by",
        choices=sorted(_SORT_KEYS),
        default="visibility",
        help="パレートフロントの表をどの目的が良い順に並べるか(既定: visibility)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    problem = FrameProblem(PlugParams(), NoseParams())
    algorithm = NSGA2(pop_size=args.pop_size)
    res = minimize(
        problem,
        algorithm,
        ("n_gen", args.n_gen),
        seed=args.seed,
        save_history=True,
        verbose=True,
    )

    generations = [OBJ_SIGN * h.pop.get("F") for h in res.history]
    pareto_f = OBJ_SIGN * res.F
    n_feasible = int(res.algorithm.pop.get("feasible").sum())
    n_total = len(res.algorithm.pop)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    evolution_path = args.output_dir / "evolution.png"
    plot_evolution(generations, evolution_path, _OBJ_LABELS)
    print_summary(
        res.X, pareto_f, n_feasible, n_total, _X_COLUMNS, _F_COLUMNS, _SORT_KEYS, args.sort_by
    )
    print(f"\n画像を出力: {evolution_path}")


if __name__ == "__main__":
    main()
