"""簡略化した鼻本体の幾何モデル(PROJECT.md の「モデル・変数・評価関数(暫定仕様 v0)」に対応)。

正確な人体計測データではなく、実験用の簡略近似。
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import trimesh

# 断面の多角形の頂点数(角丸三角形なので3)。_rounded_triangle_ringが
# 実際に組み立てる頂点(背面2つ・前面1つ)の数と一致させること
_NUM_TRIANGLE_CORNERS = 3
# 角丸三角形の1つの角に使う点数(多いほど滑らかになる)
_POINTS_PER_CORNER = 11
# 背面2角を結ぶ辺を、直線ではなく中央が前方へ膨らむカーブに置き換える
# ための点数。実際の鼻の断面は単純な三角形ではなく、背面の中腹(鼻中隔
# のあたり)がへこんだブーメラン型に近いため
_BOOMERANG_POINTS = 11
# 輪郭生成に使う点数の合計。全ての角に均等に配分されるよう、
# _NUM_RING_POINTSを独立した値にはせず_POINTS_PER_CORNERから導出する
# (assertではなく構成上ズレが起きないようにするため)。ブーメランのカーブは
# 両端が背面角のフィレット終点と重複するため、重複を除いた分だけ加える
_NUM_RING_POINTS = _POINTS_PER_CORNER * _NUM_TRIANGLE_CORNERS + (_BOOMERANG_POINTS - 2)
# 角丸三角形の角の丸め半径を、半幅(half_width)に対する比率で指定
_CORNER_ROUNDNESS_RATIO = 0.3
# 背面の中腹をへこませる量(カーブの高さ)を、その断面のdepth_backに
# 対する比率で指定
_BOOMERANG_BOW_RATIO = 0.75
# ボディのロフトに使うリング数(鼻筋〜鼻先の間を何段でつなぐか)
_NUM_LOFT_RINGS = 8
# 幅(x)テーパーの非線形度。1より大きいと鼻筋側は幅を保ち、鼻先側で急に
# 広がる。奥行き(z)は別途、鼻筋から鼻先まで直線的にテーパーさせ、
# 前面が斜め一直線に迫り出す三角形の側面シルエットにする
_TAPER_POWER = 2.2
# 鼻の背面(顔に接する側)の奥行き半径。鼻筋から鼻先まで一定とし、
# 前面だけが迫り出すことで側面が三角形になるようにする
_BACK_DEPTH = 2.2
# 鼻根(鼻筋の付け根、y=nose_len付近。顔との接着面にあたる)で背面を
# 局所的に浅くする、くびれの強さを_BACK_DEPTHに対する比率で指定。
# 背面が鼻筋から鼻先まで一定の平らな板のままだと、実際の鼻のように
# 鼻根でくびれてから顔と分かれる形にならず、厚い板が貼り付いたように
# 見えてしまう
_ROOT_WAIST_RATIO = 0.85
# 鼻根のくびれによる半幅(half_w)の減算量を、bridge_w/2に対する比率で
# 指定。背面だけでなく幅も一緒にくびれさせることで、鼻根まわり全体を
# 細くする
_ROOT_WAIST_WIDTH_RATIO = 0.9
# 鼻根のくびれが効くy方向の範囲(鼻根中心からの距離、mm)。狭すぎると
# 鼻根のごく近傍にしか効かず、通常の見た目では気づきにくい局所的な
# 切り欠きになってしまうため、鼻筋の長さに対してある程度の割合を持たせる
_ROOT_WAIST_SPAN = 25.0
# 鼻先の最終リング(側面が最大幅まで迫り出した断面)から、キャップ面へ
# つなぐ丸め処理に使う追加リングの数
_NUM_TIP_FILLET_RINGS = 4
# 鼻先の丸めに使う半径を、鼻先の半幅(tip_w/2)に対する比率で指定
_TIP_FILLET_RADIUS_RATIO = 0.25
# 鼻尖(鼻先の局所的な隆起)による前面迫り出しへの追加量を、tip_depth_front
# に対する比率で指定。単純な直線的テーパーの終点ではなく、鼻先だけが丸く
# 隆起して見えるようにする
_TIP_BUMP_RATIO = 0.3
# 鼻尖の隆起が効くy方向の範囲(鼻先中心からの距離、mm)
_TIP_BUMP_SPAN = 10.44
# 鼻翼(鼻孔まわりの張り出し)による半幅への追加量を、tip_w/2に対する
# 比率で指定
_ALAE_BUMP_RATIO = 0.1
# 鼻翼の張り出しが効くy方向の範囲(鼻先中心からの距離、mm)
_ALAE_BUMP_SPAN = 6.96
# 鼻孔楕円体のy方向(鼻先から鼻の内部へ向かう、穴としての深さ方向。
# _BACK_DEPTHやbridge/tip_depth_frontが指すz軸方向の「奥行き」とは別の軸
# なので注意)の半径を、短径(nostril_b)の何倍にするか。浅い皿状のくぼみに
# ならないよう、実際の穴らしい深さを持たせる
_NOSTRIL_DEPTH_RATIO = 2.0
# 鼻孔断面(三角形)の奥行き(z)方向における鼻孔の中心位置を、断面のz範囲
# ([-_BACK_DEPTH, tip_depth_front])に対する比率で指定。0は背面、1は前面。
# 前面(1)に寄せすぎると断面が先細りして側面からはみ出し、背面(0)に
# 寄せすぎると背面から突き抜けるため、前後の隙間が均等になる中間に
# 置いている。_BACK_DEPTHやtip_depth_frontを変更しても追従するよう、
# 絶対値ではなく比率で持つ
_NOSTRIL_Z_RATIO = 0.5


@dataclass(frozen=True)
class NoseParams:
    """鼻モデルの寸法パラメータ(単位: mmおよび度。nostril_tilt_degのみ度)。

    構築後の変更を禁止する(frozen)ことで、__post_init__の検証を
    後からのミューテーションで回避できないようにしている。
    """

    bridge_w: float = 23.2
    bridge_depth_front: float = 2.1
    tip_w: float = 34.8
    tip_depth_front: float = 12.0
    nose_len: float = 52.2
    nostril_a: float = 5.6
    nostril_b: float = 3.2
    nostril_gap: float = 8.5
    nostril_tilt_deg: float = 55.0

    def __post_init__(self) -> None:
        # 幅・奥行き・長さが0以下だと、フィレット計算(タンジェント長や
        # 角度)が0除算・NaNを起こしたり、キャップ面が自己交差したりして、
        # 例外を出さずに壊れたメッシュを生成してしまう。ここで早期に弾く
        for name in ("bridge_w", "tip_w", "nose_len", "nostril_a", "nostril_b"):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} は正の値にすること: {value}")
        # 境界ぎりぎり(例: -_BACK_DEPTHに極めて近い値)だと、チェック自体は
        # 通過しても断面が自己交差する場合があるため、余裕を持たせる
        margin = 0.5
        for name in ("bridge_depth_front", "tip_depth_front"):
            value = getattr(self, name)
            if value <= -_BACK_DEPTH + margin:
                raise ValueError(
                    f"{name} は -_BACK_DEPTH + {margin} "
                    f"({-_BACK_DEPTH + margin}) より大きくすること: {value}"
                )


def nostril_depth_z(depth_front: float) -> float:
    """鼻孔断面のz方向における配置位置を返す(_NOSTRIL_Z_RATIOによる内分)。

    depth_frontにはtip_depth_front相当の値を渡す。鼻栓プレースホルダーも
    同じ鼻孔位置に配置するため、models.plug_modelから参照される
    """
    return -_BACK_DEPTH + (depth_front + _BACK_DEPTH) * _NOSTRIL_Z_RATIO


def _unwrap_near(angle: float, reference: float) -> float:
    """angleを、referenceとの差が[-pi, pi]に収まるよう2*piの整数倍だけずらして返す。"""
    diff = angle - reference
    return angle - 2 * np.pi * np.round(diff / (2 * np.pi))


def _corner_edge_directions(
    prev_v: np.ndarray, corner_v: np.ndarray, next_v: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """corner_vから隣接2頂点(prev_v, next_v)への単位方向ベクトルを返す。"""
    u = prev_v - corner_v
    u = u / np.linalg.norm(u)
    v = next_v - corner_v
    v = v / np.linalg.norm(v)
    return u, v


def _angle_between(u: np.ndarray, v: np.ndarray) -> float:
    """単位ベクトルu, vのなす角(0〜pi)を返す。"""
    return np.arccos(np.clip(np.dot(u, v), -1.0, 1.0))


def _fillet_arc_geometry(
    corner_v: np.ndarray,
    edge_dirs: tuple[np.ndarray, np.ndarray],
    radius: float,
    beta: float,
) -> tuple[np.ndarray, float, float]:
    """角(corner_v、内角beta)を半径radiusで丸めたときの円弧の中心と、
    始点・終点の角度を返す。

    edge_dirsとbetaは呼び出し側(_corner_edge_directions + _angle_between)で
    計算済みの値を渡すこと。radiusは、隣接する2つの角のタンジェント長の
    合計が各辺の長さを超えない(フィレット同士が辺上で重ならない)ことを
    呼び出し側が保証していること。
    """
    u, v = edge_dirs
    tangent_len = radius / np.tan(beta / 2)

    bisector = u + v
    bisector /= np.linalg.norm(bisector)
    center = corner_v + bisector * (radius / np.sin(beta / 2))

    p1 = corner_v + u * tangent_len
    p2 = corner_v + v * tangent_len
    angle1 = np.arctan2(p1[1] - center[1], p1[0] - center[0])
    angle2 = np.arctan2(p2[1] - center[1], p2[0] - center[0])

    # p1からp2への弧の中心角は必ず(pi - beta)、すなわち[0, pi]に収まる
    # (betaは内角で(0, pi)の範囲のため)。したがってangle1との差が
    # [-pi, pi]に収まる側が常に正しい(凸な)弧であり、angle_cornerを
    # 使った判定は不要かつ、betaが鈍角のとき逆向きの弧を選ぶ不具合の原因だった
    angle2 = _unwrap_near(angle2, angle1)
    return center, angle1, angle2


def _fillet_corner(
    corner_v: np.ndarray,
    edge_dirs: tuple[np.ndarray, np.ndarray],
    radius: float,
    beta: float,
    num_points: int,
) -> np.ndarray:
    """多角形の1つの角(corner_v、内角beta)を半径radiusで丸めた円弧の点列を返す。"""
    center, angle1, angle2 = _fillet_arc_geometry(corner_v, edge_dirs, radius, beta)
    angles = np.linspace(angle1, angle2, num_points)
    arc_x = center[0] + radius * np.cos(angles)
    arc_z = center[1] + radius * np.sin(angles)
    return np.stack([arc_x, arc_z], axis=1)


def _safe_corner_radius(
    vertices: np.ndarray, betas: list[float], radius: float
) -> float:
    """辺を共有する2つの角のフィレットが辺上で重ならない安全な半径を返す。

    1つの角だけを見て半径を制限しても、辺の反対側の角も同時に大きな
    半径を要求していれば、両側のタンジェント点が辺の途中で交差し
    (自己交差した不正な輪郭になり)、それでもTrimeshはwatertight/
    winding_consistentと判定してしまう。そのため、各辺について両端の
    タンジェント長の合計が辺の長さを超えないよう、三角形全体で半径を
    決める。betasは各頂点の内角(vertices[i]に対応、呼び出し側で計算済み)。
    """
    num_corners = len(vertices)
    margin = 0.95  # ちょうど辺いっぱいだと接点が一致してしまうため少し余裕を持たせる
    for i in range(num_corners):
        j = (i + 1) % num_corners
        edge_len = np.linalg.norm(vertices[j] - vertices[i])
        tangent_len_per_radius = 1 / np.tan(betas[i] / 2) + 1 / np.tan(betas[j] / 2)
        radius = min(radius, edge_len * margin / tangent_len_per_radius)
    return radius


def _boomerang_bow(
    x_start: float, x_end: float, z: float, bow_depth: float, num_points: int
) -> np.ndarray:
    """(x_start, z)から(x_end, z)へ、中央がbow_depthだけ前方(+z方向)に
    膨らむ余弦カーブの点列を返す。

    実際の鼻の断面は背面が平らな三角形ではなく、背面の中腹(鼻中隔の
    あたり)がへこんだブーメラン型に近いため、背面2角を結ぶ直線をこの
    カーブに置き換える。単純な円弧(弦の両端と中央の膨らみ量から求める
    もの)だと、両端での接線が隣接する角丸フィレットの接線(水平)と
    一致せず、繋ぎ目で傾きが不連続になり縁が鋭く見えてしまう。
    _localized_bumpと同じ余弦カーブは両端で傾きがちょうど0になるため、
    フィレットの接線に滑らかに繋がる。
    """
    t = np.linspace(0.0, 1.0, num_points)
    x = x_start + (x_end - x_start) * t
    bow_z = z + bow_depth * 0.5 * (1 - np.cos(2 * np.pi * t))
    return np.stack([x, bow_z], axis=1)


def _rounded_triangle_ring(
    half_width: float, depth_back: float, depth_front: float
) -> np.ndarray:
    """角丸三角形の輪郭点を (_NUM_RING_POINTS, 2) で返す。

    背面(depth_back)側の2頂点を底辺、前面(depth_front)側の1頂点を頂点とする
    三角形の角を丸めることで、鼻の前後非対称な断面(背面は平ら、前面だけ
    尖って迫り出す)を三角柱に近い構造で表現する。ただし背面2角を結ぶ辺は
    直線ではなく、中腹がへこむブーメラン型のカーブにしている(_boomerang_bow)。
    """
    vertices = np.array(
        [[-half_width, -depth_back], [half_width, -depth_back], [0.0, depth_front]]
    )
    num_corners = len(vertices)

    # 各頂点の辺方向ベクトル(edge_dirs)と内角(beta)は_safe_corner_radiusと
    # _fillet_cornerの両方で必要になるが、ここで1度だけ計算して使い回す
    edge_dirs = [
        _corner_edge_directions(
            vertices[i - 1], vertices[i], vertices[(i + 1) % num_corners]
        )
        for i in range(num_corners)
    ]
    betas = [_angle_between(u, v) for u, v in edge_dirs]
    radius = _safe_corner_radius(
        vertices, betas, half_width * _CORNER_ROUNDNESS_RATIO
    )

    arcs = [
        _fillet_corner(
            vertices[i], edge_dirs[i], radius, betas[i], _POINTS_PER_CORNER
        )
        for i in range(num_corners)
    ]

    # arcs[0](背面左角)の終点とarcs[1](背面右角)の始点は、どちらも
    # 元の直線の背面辺の上にある。その間を、へこんだカーブで置き換える。
    # 両端は既存の点と重複するので[1:-1]で除く
    back_left_end = arcs[0][-1]
    back_right_start = arcs[1][0]
    # 背面角のフィレットが辺の大部分を消費する断面(半幅が広く前面の
    # 迫り出しが浅いなど)では、残り幅が狭いのに深さが固定のままだと
    # 幅に対して尖ったスパイク状になってしまう。半弦長に対する比率で
    # 深さの上限を設け、細くなるほどへこみも浅くする
    half_chord = (back_right_start[0] - back_left_end[0]) / 2
    bow_depth = min(depth_back * _BOOMERANG_BOW_RATIO, half_chord * 0.5)
    bow = _boomerang_bow(
        back_left_end[0], back_right_start[0], -depth_back, bow_depth, _BOOMERANG_POINTS
    )[1:-1]

    return np.concatenate([arcs[0], bow, arcs[1], arcs[2]], axis=0)


def _localized_bump(y: float, span: float, reference: float, ratio: float) -> float:
    """鼻先(y=0)からspan以内で、余弦カーブで滑らかに0へ減衰するふくらみ量を返す。

    鼻尖(前面迫り出しへの追加)・鼻翼(半幅への追加)のどちらも、
    「鼻先付近だけ局所的に隆起し、離れるほど滑らかに元の形へ戻る」という
    同じ形の変形なので共通化している。referenceはふくらみの基準量
    (鼻先での最大値)、ratioはそれに対する隆起量の比率。
    """
    dist = abs(y)
    if dist >= span:
        return 0.0
    return reference * ratio * 0.5 * (1 + np.cos(np.pi * dist / span))


def _tip_bump(y: float, tip_depth_front: float) -> float:
    """鼻尖(鼻先の局所的な隆起)による前面迫り出しへの追加量。"""
    return _localized_bump(y, _TIP_BUMP_SPAN, tip_depth_front, _TIP_BUMP_RATIO)


def _alae_bump(y: float, tip_half_w: float) -> float:
    """鼻翼(鼻孔まわりの張り出し)による半幅への追加量。"""
    return _localized_bump(y, _ALAE_BUMP_SPAN, tip_half_w, _ALAE_BUMP_RATIO)


def _root_waist_depth_bump(y: float, nose_len: float) -> float:
    """鼻根(鼻筋の付け根)のくびれによる、背面(depth_back)からの減算量。

    _localized_bumpは鼻先(y=0)を中心に減衰するが、くびれの中心は
    鼻根(y=nose_len)なので、yをnose_len分ずらして中心を合わせている。
    """
    return _localized_bump(y - nose_len, _ROOT_WAIST_SPAN, _BACK_DEPTH, _ROOT_WAIST_RATIO)


def _root_waist_width_bump(y: float, nose_len: float, bridge_half_w: float) -> float:
    """鼻根のくびれによる、半幅(half_w)からの減算量。"""
    return _localized_bump(
        y - nose_len, _ROOT_WAIST_SPAN, bridge_half_w, _ROOT_WAIST_WIDTH_RATIO
    )


def _ring_at_y(half_width: float, depth_back: float, depth_front: float, y: float) -> np.ndarray:
    """角丸三角形の輪郭(x, z)にyを結合し、3D頂点列 (_NUM_RING_POINTS, 3) にして返す。"""
    ring_2d = _rounded_triangle_ring(half_width, depth_back, depth_front)
    y_col = np.full(len(ring_2d), y)
    return np.column_stack([ring_2d[:, 0], y_col, ring_2d[:, 1]])


def surface_profile(params: NoseParams, y: float) -> tuple[float, float, float]:
    """指定したyにおける鼻表面の断面プロファイル(半幅, 背面奥行き, 前面迫り出し)を返す。

    _ring_atが使うテーパー式(鼻尖・鼻翼の隆起、鼻根のくびれを含む)から、
    リング全体ではなくこの3値だけを取り出したもの。models.frame_modelが
    鼻の外側に沿った経路を組むために参照する
    """
    s = 1 - y / params.nose_len  # 0=鼻筋(上), 1=鼻先(下)
    width_taper = s**_TAPER_POWER
    half_w = (params.bridge_w + (params.tip_w - params.bridge_w) * width_taper) / 2
    depth_front = (
        params.bridge_depth_front
        + (params.tip_depth_front - params.bridge_depth_front) * s
    )

    # 鼻尖(前面)・鼻翼(半幅)の局所的な隆起を、直線的なテーパーに上乗せする
    depth_front += _tip_bump(y, params.tip_depth_front)
    half_w += _alae_bump(y, params.tip_w / 2)
    # 鼻根(半幅・背面)のくびれを差し引く
    half_w -= _root_waist_width_bump(y, params.nose_len, params.bridge_w / 2)
    depth_back = _BACK_DEPTH - _root_waist_depth_bump(y, params.nose_len)

    return half_w, depth_back, depth_front


def _z_at_center(region: np.ndarray) -> float:
    """2D点列(region[:,0]がx, region[:,1]がz)のうち、x=0に最も近い点のzを返す。

    back_surface_z_at_center/front_surface_z_at_centerの共通ロジック
    (リングを対象の弧だけに絞り込んだあと、x=0に最も近い点を探す部分)。
    """
    idx = np.argmin(np.abs(region[:, 0]))
    return float(region[idx, 1])


def back_surface_z_at_center(params: NoseParams, y: float) -> float:
    """指定したyにおける、背面境界のx=0(中央)での実際のz座標を返す。

    断面の背面2角を結ぶ辺は直線ではなく、中央(x=0)が+z方向へ膨らむ
    ブーメラン型のカーブ(_boomerang_bow)になっている。そのため単純に
    -depth_backを「背面の位置」として使うと、実際より後方(奥)に安全域を
    見積もってしまう。frame_model.validate_grip_depthが、常にx=0にある
    アーム起点が鼻の背面を突き抜けていないか正しく検証するために使う
    (ブーメラン計算式を再実装せず、実際の断面リング上でx=0に最も近い
    点のzを使うことで、_rounded_triangle_ringの実装から乖離しないようにする)。

    _rounded_triangle_ringが返すリングは[背面左角の弧, ブーメラン, 背面右角の
    弧, 前面角の弧]の順に連結されている(_rounded_triangle_ring参照)。x=0に
    近い点を探す範囲を先頭3ブロック(背面側、末尾の前面角の弧を除く)に
    限定することで、前面角の弧の点を誤って拾わないようにしている。
    """
    half_width, depth_back, depth_front = surface_profile(params, y)
    ring = _rounded_triangle_ring(half_width, depth_back, depth_front)
    return _z_at_center(ring[:-_POINTS_PER_CORNER])


def front_surface_z_at_center(params: NoseParams, y: float) -> float:
    """指定したyにおける、前面境界のx=0(中央)での実際のz座標を返す。

    surface_profileが返すdepth_frontは、角丸処理前の三角形の頂点(鋭角の
    コーナー)のz座標であり、実際のメッシュはこの頂点を半径
    half_width*_CORNER_ROUNDNESS_RATIOでフィレットしているため、実際の
    前面境界(x=0)はdepth_frontより後退している(既定値でy=6mm付近で
    約1.66mm)。frame_model.arm_pointsのアーム起点(grip_depthでめり込ませる
    基準点)は、この後退を無視するとdepth_frontを基準にした分だけ実際には
    鼻表面に届かず、意図した「鼻中隔を挟み込む」挙動が機能しなくなる。

    _rounded_triangle_ringのリングの末尾_POINTS_PER_CORNER点が前面角の
    フィレット弧にあたる(_rounded_triangle_ring参照)。back_surface_z_at_
    centerと同様、リング全体でx=0に近い点を探すと稀に背面のブーメラン
    カーブ側の点を誤って拾うことがあるため、前面角の弧だけに限定する。
    """
    half_width, depth_back, depth_front = surface_profile(params, y)
    ring = _rounded_triangle_ring(half_width, depth_back, depth_front)
    return _z_at_center(ring[-_POINTS_PER_CORNER:])


def _ring_at(params: NoseParams, k: int) -> np.ndarray:
    """k番目のリング(0=鼻筋, _NUM_LOFT_RINGS-1=鼻先)の3D頂点列 (_NUM_RING_POINTS, 3) を返す。"""
    s = k / (_NUM_LOFT_RINGS - 1)  # 0=鼻筋(上), 1=鼻先(下)
    y = params.nose_len * (1 - s)
    half_w, depth_back, depth_front = surface_profile(params, y)
    return _ring_at_y(half_w, depth_back, depth_front, y)


def _loft_side_faces(num_rings: int) -> list[list[int]]:
    """隣接リング間を繋ぐ側面の三角形面を返す。"""
    faces = []
    for k in range(num_rings - 1):
        ring_a = k * _NUM_RING_POINTS
        ring_b = (k + 1) * _NUM_RING_POINTS
        for i in range(_NUM_RING_POINTS):
            j = (i + 1) % _NUM_RING_POINTS
            faces.append([ring_a + i, ring_b + j, ring_b + i])
            faces.append([ring_a + i, ring_a + j, ring_b + j])
    return faces


def _loft_cap_faces(
    bridge_center_idx: int, tip_center_idx: int, num_rings: int
) -> list[list[int]]:
    """鼻筋側・鼻先側の両端を、それぞれの中心点から扇状に閉じる面を返す。"""
    faces = []
    tip_ring_start = (num_rings - 1) * _NUM_RING_POINTS
    for i in range(_NUM_RING_POINTS):
        j = (i + 1) % _NUM_RING_POINTS
        faces.append([bridge_center_idx, j, i])
        faces.append([tip_center_idx, tip_ring_start + i, tip_ring_start + j])
    return faces


def _tip_fillet_radius(half_w: float, depth_front: float) -> float:
    """鼻先の丸め処理(_tip_fillet_rings)に使う半径を返す。

    insetの最大値(半径そのもの)がhalf_wやdepth_frontを超えると、輪郭の
    前面頂点が背面の辺を越えて反転してしまう(winding反転。
    _safe_corner_radiusで対処した不具合と同じクラス)。tip_depth_frontが
    小さいパラメータで実際に再現するため、半幅・前面迫り出しの小さい方を
    超えないよう安全マージンを掛けて制限する
    """
    margin = 0.9
    return min(half_w * _TIP_FILLET_RADIUS_RATIO, min(half_w, depth_front) * margin)


def tip_cap_min_y(params: NoseParams) -> float:
    """鼻先の丸め処理(_tip_fillet_rings)が実際に到達する最小のy座標を返す。

    鼻本体メッシュはy=0からこの値までしか存在しない(丸め処理はy=0を
    中心に四分円状に窄まるため、最も鼻先側の点はy=0-radius)。この値より
    小さいyには鼻本体メッシュが存在しないため、models.frame_modelが
    「鼻の外側」を判定する基準として使う
    """
    radius = _tip_fillet_radius(params.tip_w / 2, params.tip_depth_front)
    return -radius


def tip_cap_depth_front(params: NoseParams, y: float) -> float:
    """鼻先の丸め区間([tip_cap_min_y(params), 0])における前面迫り出しの
    実測値を返す。

    surface_profileの式はこの区間の実際の丸め形状(_tip_fillet_rings)を
    表さない(単純なテーパーを延長するだけで、丸め処理による窄まりを
    無視する)ため、この区間ではこちらを使う。_tip_fillet_ringsのinset
    計算をyから逆算する形で再現している(y=0でsurface_profileの値と
    一致する)。models.frame_modelが鼻先付近で外側判定をする際、
    surface_profileの延長値より正確(かつより小さい、鼻に近い)値を
    得るために使う
    """
    half_w = params.tip_w / 2
    depth_front = params.tip_depth_front
    radius = _tip_fillet_radius(half_w, depth_front)
    angle = np.arcsin(np.clip(-y / radius, -1.0, 1.0))
    inset = radius * (1 - np.cos(angle))
    return depth_front - inset + _tip_bump(y, depth_front)


def _tip_fillet_rings(half_w: float, depth_front: float, y: float) -> list[np.ndarray]:
    """鼻先の最終リング(半幅half_w・前面迫り出しdepth_front・位置y)から
    キャップ面へ、四分円状に断面を窄めながらつなぐ追加リング群を返す。

    これがないと、迫り出しきった側面にいきなり平らなキャップを被せる形に
    なり、側面とキャップの境目が鋭いリムになってしまう(実際の鼻先は
    側面から丸くつながって下面に至る)。_fillet_cornerと同様、円弧
    (半径radius)で丸める考え方を3Dのリング列に適用している。
    """
    radius = _tip_fillet_radius(half_w, depth_front)
    rings = []
    for m in range(1, _NUM_TIP_FILLET_RINGS + 1):
        angle = (m / _NUM_TIP_FILLET_RINGS) * (np.pi / 2)
        inset = radius * (1 - np.cos(angle))
        ring_y = y - radius * np.sin(angle)

        # 鼻尖・鼻翼の隆起は丸め区間にも及ぶため(_ring_atと同じ考え方)、
        # 窄めた後の値に追加する
        ring_depth_front = depth_front - inset + _tip_bump(ring_y, depth_front)
        ring_half_w = half_w - inset + _alae_bump(ring_y, half_w)
        # 丸め区間は鼻先(y=0)付近に限られ鼻根から十分離れているため、
        # 背面は_root_waist_bumpの影響を受けない_BACK_DEPTHのままでよい
        rings.append(_ring_at_y(ring_half_w, _BACK_DEPTH, ring_depth_front, ring_y))
    return rings


def _build_body(params: NoseParams) -> trimesh.Trimesh:
    """鼻筋(y=nose_len)から鼻先(y=0)へテーパーし、鼻先はさらに丸めながら
    キャップへつながるロフト形状(実際の頂点はy=0よりわずかに先まで続く)。

    幅(x)は鼻筋側で保たれ鼻先側で急に広がる非線形テーパー、奥行き(z)の
    前面は鼻筋から鼻先まで直線的に迫り出すテーパーにすることで、
    正面から見ても側面から見ても丸みを帯びた三角形のシルエットになる。
    """
    main_rings = [_ring_at(params, k) for k in range(_NUM_LOFT_RINGS)]
    # 鼻先の最終リング(s=1, y=0)は幅・前面迫り出しともにtip_w/tip_depth_frontの
    # 最大値になっている。これをそのままキャップすると縁が鋭くなるため、
    # キャップ手前を丸める追加リングを繋ぐ
    fillet_rings = _tip_fillet_rings(params.tip_w / 2, params.tip_depth_front, y=0.0)
    ring_vertices = main_rings + fillet_rings
    num_rings = len(ring_vertices)

    bridge_center_idx = num_rings * _NUM_RING_POINTS
    tip_center_idx = bridge_center_idx + 1
    # リング内の全点でyは共通なので、先頭の点から取り出せばよい
    tip_y = ring_vertices[-1][0, 1]
    vertices = np.vstack(
        ring_vertices + [[[0.0, params.nose_len, 0.0]], [[0.0, tip_y, 0.0]]]
    )

    faces = _loft_side_faces(num_rings)
    faces += _loft_cap_faces(bridge_center_idx, tip_center_idx, num_rings)

    return trimesh.Trimesh(vertices=vertices, faces=np.array(faces), process=True)


def _nostril_ellipsoid(params: NoseParams) -> trimesh.Trimesh:
    """鼻孔をくり抜くための楕円体(原点中心、回転・配置前)を返す。"""
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    scale = np.eye(4)
    scale[0, 0] = params.nostril_a
    scale[1, 1] = params.nostril_b * _NOSTRIL_DEPTH_RATIO
    scale[2, 2] = params.nostril_b
    mesh.apply_transform(scale)
    return mesh


def _build_nostril(
    base_ellipsoid: trimesh.Trimesh,
    gap: float,
    tilt_deg: float,
    depth_front: float,
    side: Literal[-1, 1],
) -> trimesh.Trimesh:
    """base_ellipsoidを回転・配置し、鼻先の下側(y=0の断面付近)を向く鼻孔にする。

    形状(nostril_a/nostril_b)はbase_ellipsoidに既に反映済みなので、ここでは
    配置に関わる値(nostril_gap, nostril_tilt_deg, tip_depth_front)だけを
    受け取る。NoseParams全体を渡さないのは、base_ellipsoid構築後にparamsが
    変わっても形状に反映されない、という食い違いを起こさないため。
    """
    mesh = base_ellipsoid.copy()

    # y軸まわりに回転させる(x-z平面内で傾く)ことで、底面から見たときに
    # 左右の鼻孔が「ハ」の字に開くようにする
    tilt = np.radians(tilt_deg) * side
    rotate = trimesh.transformations.rotation_matrix(tilt, [0, 1, 0])
    mesh.apply_transform(rotate)

    x_pos = side * gap / 2
    # y=0(鼻先の丸め処理に入る直前の断面)上に中心を置く。楕円体の半分弱が
    # y<0側にはみ出す形になり、ブーリアン減算後に鼻先の下側を向いた
    # 自然な深さの開口部になる
    y_pos = 0.0
    z_pos = nostril_depth_z(depth_front)
    mesh.apply_translation([x_pos, y_pos, z_pos])

    return mesh


def build_nose_body(params: NoseParams) -> trimesh.Trimesh:
    """鼻本体メッシュを構築する(左右の鼻孔をくり抜き、着色済み)。"""
    body = _build_body(params)
    base_ellipsoid = _nostril_ellipsoid(params)
    left, right = (
        _build_nostril(
            base_ellipsoid,
            gap=params.nostril_gap,
            tilt_deg=params.nostril_tilt_deg,
            depth_front=params.tip_depth_front,
            side=side,
        )
        for side in (-1, 1)
    )

    # 鼻孔同士が重なると1つの穴に融合してしまい、ブーリアン減算自体は
    # 成功する(watertightなメッシュが返る)ため、事前に重なりを検出する
    if len(left.intersection(right).faces) > 0:
        raise ValueError(
            "左右の鼻孔が重なっている。nostril_a/nostril_gapを見直すこと"
        )

    body = body.difference([left, right])
    if len(body.faces) == 0:
        raise ValueError(
            "鼻孔のブーリアン減算でボディが消失した。"
            "nostril_a/nostril_b/nostril_gapが大きすぎる可能性がある"
        )
    # 鼻孔の窪みが側面や背面まで突き抜けると、くぼみ(トポロジー的には
    # 球のまま)ではなくトンネル(貫通穴)になり、閉曲面のオイラー数が
    # 2からずれる。tip_wを鼻孔サイズに対して狭めすぎたときに実際に
    # 再現したため検出する
    if body.euler_number != 2:
        raise ValueError(
            "鼻孔が側面や背面まで突き抜けている可能性がある"
            "(euler_number != 2)。tip_wやnostril_a/b/gapを見直すこと"
        )
    body.visual.face_colors = [255, 220, 200, 255]
    return body
