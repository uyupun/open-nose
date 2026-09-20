"""NSGA-II(pymoo)による拡張ブリッジ型フレーム形状の多目的最適化スクリプト。

evaluate_frame/constraint_values(scripts/dilator/evaluation.py)をpymooの
Problemでラップし、FrameParamsの6設計変数を探索してパレートフロントを
求める。可視化・結果表示はcommons/report.py側の責務とし、このファイルは
実行(FrameProblemの定義とminimize()の呼び出し)だけを持つ
(earrings/spiral.optimize.pyと同じ構成)。

## 目的関数の符号

pymooは最小化のみを扱う。extension_force・inconspicuousnessは最大化
したい目的なので、OBJ_SIGN([-1, 1, -1])を使い、pain以外の符号を反転する。

## 探索範囲(_SEARCH_SPACEの根拠)

FrameParams.__post_init__が要求する下限(いずれも正の値であること)は
そのまま使う。上限は物理的な基準が明示されていない変数が多く、以下の
考え方で仮置きした(GAを実際に動かしながら見直す前提の暫定値。
scripts/dilator/frame_model.pyのモジュールdocstring参照):

- natural_radius: 既定のNoseParamsでの装着後の実際の曲率半径
  (bridge_curvature、実測約6.7mm)に対し、curvature_margin
  (_MIN_CURVATURE_RATIO=1.2倍)を満たす下限(約8.1mm)の少し外側を下限
  (15.0mm)にした。上限100.0mmは、これ以上平らにしてもdeflection
  (1/actual_radius - 1/natural_radius)の増分が小さくなり
  (1/natural_radiusが0に近づくため)、実質的な効果が頭打ちになる水準の
  暫定値
- bridge_width: 実際のブリーズライトの幅の水準に近づけた範囲(下限4.2mm、
  上限5.0mm)。下限は、嵌め込みのスロット(首+頭+はめあい+周りに残す肉=
  1.2+1.7+0.15+0.8=3.85mm)が帯の幅に収まる必要(tab_fit_margin)から
  決めている(タブを大きくするたびに引き上げており、3.0→3.5→4.2mm)。ユーザー指摘(「縦が長すぎる、鼻にフィットする感じに」)を
  受けて、以前の上限(7.0mm、鼻翼の隆起commons.nose_model._ALAE_BUMP_SPAN
  ≈7mmに合わせた値)から縮めた。なお、bridge_widthはextension_force
  (∝width)とpain(∝thickness^3/length^3、widthはforce/areaの計算で
  相殺されるため現れない)・inconspicuousness(thicknessのみに依存)の
  いずれにも本質的なトレードオフがなく、GAは常にこの上限へ寄せる
  (実際のパレートフロントでも全個体がbridge_width≈上限値だった)。
  この上限自体が実質的な既定の見た目を決める値になるため、値そのものを
  ユーザーの見た目の指摘に合わせて調整する方針にした
- bridge_thickness: 平らな板ばね(実際のブリーズライトのテープ厚)の
  水準。帯の厚みはそのまま嵌め込みのタブの厚み、そしてタブの首の中を通る
  棒の太さの上限にもなるため、下限は印刷・嵌め込みに耐える最小値
  (frame_model._MIN_TAB_THICKNESS=_MIN_ROD_DIAMETER=1.8mm、ユーザー指摘
  「連結部分も同様に太さ調整して」「まだ太くして欲しい」)に合わせた
  (1.0→1.8mm)。上限は2.8mm(厚いほど拡張力は上がるが、そのぶん目立つ=
  inconspicuousnessが下がる本質的なトレードオフになる)
- leg_thickness: 当初はearrings.optimize.pyのring_thicknessと同じ範囲
  (0.8〜2.5mm)にしていたが、実際に3Dプリントしたところ「サポートを
  つけても強度がなく崩れてしまう」という指摘を受け、下限を1.2mmへ
  引き上げ、その後さらに実際に印刷したユーザーの「棒をもう少し太く(印刷
  できない)」「まだ太くして欲しい」という指摘を受けて1.2→1.6→2.2mmへ
  上げた(上限も1.9→2.6→3.2mm)。棒の
  太さ(鼻の側面に沿う区間の最大)・タブの首の幅に使われる。レンズ(筒)自体の壁の肉厚には使われない(以前はleg_thicknessを
  そのまま流用していたが、左右のレンズが重なってブーリアン結合が破綻する
  原因になったため、frame_model._COLLAR_WALL_THICKNESSという固定値に
  切り離した。同定数のコメント参照)。上限は1.9mmにとどめた:
  leg_clearance_margin(棒が鼻の側面に沿う区間の、線径に比例しためり込み
  許容量)が太い個体ほど厳しくなるため(この制約自体は鼻表面への不自然な
  沈み込みを防ぐためのもので、印刷強度の指摘とは無関係。緩めていない)。
  なお棒は、レンズへ溶け込む手前と、帯(ブリッジ)のタブへ入る手前では、
  レンズ・帯の厚みに収まる太さまでなめらかに細くなる(frame_model.
  _rod_radii参照)ため、この値は「棒の最も太いところ」の意味になる。
  最も細いところ(レンズへ溶け込む区間)はrod_thickness_marginが印刷可能な
  太さ(_MIN_ROD_DIAMETER=1.8mm)を下回らないか監視する。
  leg_thicknessも目的(extension_force・pain・inconspicuousness)の
  いずれにも現れないため、bridge_widthと同様、GAは制約が許す限りこの
  上限へ寄せる
- collar_length: レンズ(鼻栓を差し込む筒)の厚み。レンズは鼻栓の露出部分
  (鼻の外、commons.plug_model.plug_outer_endからcommons.nose_model.
  tip_cap_min_yまでの間、実測で約2.25mm)に収める設計のため、これを
  超えると鼻本体メッシュにめり込む(collar_clearance_marginが弾く)。
  ユーザー指摘「まだ太くして欲しい」を受けてframe_model._COLLAR_PLUG_INSETを
  0.3→0.15mmに詰め、そのぶん上限を1.9→2.1mmへ伸ばした(実測で2.2mmから
  違反し始める)。下限1.95mmは、棒がレンズへ溶け込む区間の太さがこの厚みで
  決まる(_rod_radii。レンズの上下の面からはみ出さない=直径≦collar_length)
  ため、要求する太さ(rod_thickness_margin、直径1.8mm以上)をわずかな余裕を
  持って満たす水準から決めた。つまりこの変数は、レンズの厚みと棒の太さを
  同時に決める一番効くつまみになっている
- tab_head_oversize: 嵌め込み(ジョイントマット状のタブとスロット)の
  矢じりの張り出し量(片側、mm)。ユーザーのスケッチに沿って、帯の下縁の
  スロットへ平らなタブを押し込む構造にしたときの「返し」(抜け止めの
  引っかかり)の大きさ。実際に引っかかる量は、スロットをタブより太らせる
  はめあい公差(frame_model._TAB_CLEARANCE=0.15mm)を引いた残りなので、
  細かい印刷でも確実に嵌まるようはめあいを0.1→0.15mmへ広げ、さらに返しの
  最小値も0.2→0.3mm(_MIN_TAB_RETENTION、ユーザー要望「まだ太くして
  欲しい」)へ上げたぶん、下限0.45mm(引っかかり0.30mm)・上限0.75mm
  (引っかかり0.60mm)にした。
  引っかかりが足りない組み合わせはtab_retention_marginが弾く。
  tab_head_oversizeは目的(extension_force・pain・inconspicuousness)の
  いずれにも現れないため、GAは範囲内のどの値も等しく良いとみなす。ただし
  大きいほどスロットも大きくなり、帯に収まらなくなる(tab_fit_marginが
  弾く)ので、bridge_width・leg_thicknessとの組み合わせでは制約を受ける
"""

import argparse
import sys
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/dilator/xxx.py`で
# 実行するとsys.path[0]はscripts/dilator/になり、commons/dilatorパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from pymoo.algorithms.moo.nsga2 import NSGA2  # noqa: E402
from pymoo.core.problem import Problem  # noqa: E402
from pymoo.optimize import minimize  # noqa: E402

from commons.nose_model import NoseParams  # noqa: E402
from commons.plug_model import PlugParams  # noqa: E402
from commons.report import SortKeys, plot_evolution, print_summary  # noqa: E402
from dilator.evaluation import constraint_values, evaluate_frame  # noqa: E402
from dilator.export_model import OUTPUT_DIR  # noqa: E402
from dilator.frame_model import (  # noqa: E402
    FrameParams,
    validate_collar_no_overlap,
    validate_target_reach,
)

# 探索変数(名前, 下限, 上限)。FrameParamsのフィールド順と揃える(この順で
# FrameProblem._evaluateがFrameParamsを組み立てる)。根拠はモジュール
# docstring参照
_SEARCH_SPACE: list[tuple[str, float, float]] = [
    ("natural_radius", 15.0, 100.0),
    ("bridge_width", 4.2, 5.0),
    ("bridge_thickness", 2.4, 3.4),
    ("leg_thickness", 2.8, 3.8),
    ("collar_length", 2.00, 2.10),
    ("tab_head_oversize", 0.45, 0.75),
]
_VAR_NAMES = [name for name, _, _ in _SEARCH_SPACE]
_XL = np.array([lo for _, lo, _ in _SEARCH_SPACE])
_XU = np.array([hi for _, _, hi in _SEARCH_SPACE])

# 目的(extension_force, pain, inconspicuousness)の符号。pymooは最小化のみ
# 扱うため、最大化したいextension_force・inconspicuousnessだけ反転する
# (モジュールdocstring参照)
OBJ_SIGN = np.array([-1.0, 1.0, -1.0])

# 目的の表示名(グラフの軸ラベル)。extension_force, pain, inconspicuousness
# の順で固定(FrameProblem._evaluateが組み立てる順序と同じ)
_OBJ_LABELS = [
    "extension_force (拡張力, 基準の帯の剛性=1, 最大化)",
    "pain (圧力 = 拡張力/接触面積, 最小化)",
    "inconspicuousness (目立たなさ = -正面投影面積 mm^2, 最大化)",
]
# print_summaryの並べ替え指定: 目的の名前 → (列番号, 大きい順か)。
# OBJ_SIGN・_OBJ_LABELSと同じ順序・向き
_SORT_KEYS: SortKeys = {
    "extension_force": (0, True),
    "pain": (1, False),
    "inconspicuousness": (2, True),
}
# パレートフロントの表の(見出し, 表示幅)。_SEARCH_SPACEの変数順・目的順
_X_COLUMNS = [
    ("nat_r", 8),
    ("bridge_w", 9),
    ("bridge_t", 9),
    ("leg_t", 7),
    ("collar_l", 9),
    ("tab_ovsz", 9),
]
_F_COLUMNS = [("force", 8), ("pain", 8), ("inconspic.", 11)]


class FrameProblem(Problem):
    """FrameParamsの6変数を探索するpymoo Problem。plug/noseは固定。"""

    def __init__(self, plug: PlugParams, nose: NoseParams):
        # frameに依存しない検証(問題設定そのものの誤り)は、GAを回す前に
        # 一度だけ確認しておく(earrings/spiral.optimize.pyと同じ理由)
        validate_target_reach(plug, nose)
        validate_collar_no_overlap(plug, nose)

        super().__init__(n_var=6, n_obj=3, n_ieq_constr=10, xl=_XL, xu=_XU)
        self.plug = plug
        self.nose = nose

    def _evaluate(self, x: np.ndarray, out: dict, *args, **kwargs) -> None:
        objectives = np.empty((len(x), self.n_obj))
        constraints = np.empty((len(x), self.n_ieq_constr))
        for i, row in enumerate(x):
            frame = FrameParams(**dict(zip(_VAR_NAMES, row)))
            score = evaluate_frame(frame, self.plug, self.nose)
            objectives[i] = OBJ_SIGN * [
                score.extension_force,
                score.pain,
                score.inconspicuousness,
            ]
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
        default="extension_force",
        help="パレートフロントの表をどの目的が良い順に並べるか(既定: extension_force)",
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
