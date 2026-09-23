"""角丸三角形の断面輪郭を作る、鼻を知らない汎用の2D幾何プリミティブ。

背面2頂点・前面1頂点の三角形の角を丸め、背面2角を結ぶ辺だけは直線ではなく
中央が前方へ膨らむカーブ(ブーメラン型)にした輪郭(rounded_triangle_ring)
を組み立てる。個々の頂点・辺長・丸め半径から輪郭点列を導く計算はnose_model
の意味づけ(鼻先・鼻翼など)に依存しないため、こちらに分離している。
"""

import numpy as np

# 断面の多角形の頂点数(角丸三角形なので3)。rounded_triangle_ringが
# 実際に組み立てる頂点(背面2つ・前面1つ)の数と一致させること
_NUM_TRIANGLE_CORNERS = 3
# 角丸三角形の1つの角に使う点数(多いほど滑らかになる)
POINTS_PER_CORNER = 11
# 背面2角を結ぶ辺を、直線ではなく中央が前方へ膨らむカーブに置き換える
# ための点数。実際の鼻の断面は単純な三角形ではなく、背面の中腹(鼻中隔
# のあたり)がへこんだブーメラン型に近いため
_BOOMERANG_POINTS = 11
# 輪郭生成に使う点数の合計。全ての角に均等に配分されるよう、
# NUM_RING_POINTSを独立した値にはせずPOINTS_PER_CORNERから導出する
# (assertではなく構成上ズレが起きないようにするため)。ブーメランのカーブは
# 両端が背面角のフィレット終点と重複するため、重複を除いた分だけ加える
NUM_RING_POINTS = POINTS_PER_CORNER * _NUM_TRIANGLE_CORNERS + (_BOOMERANG_POINTS - 2)
# 角丸三角形の角の丸め半径を、半幅(half_width)に対する比率で指定。
# 0.3→0.15→0.25と動かしている。0.3では背面の2角(内角が浅い扁平な
# 三角形)が大きく削られて断面が指定の半分まで縮み、鼻栓(直径10mm)を
# 左右に並べた筒が鼻の幅に収まらなかった。0.15まで下げると幅は戻るが、
# 今度は前面の角が尖りすぎて(帯の高さで丸めの半径1.9mm・弧長4.0mm)、
# 鼻を横断する帯が稜線のところで「くの字」に折れた(ユーザー指摘
# 「アーチの両端が曲がりすぎている」)。0.25にして前面の弧長を7.1mmへ
# 倍増させ、縮むぶんはNoseParamsのbridge_w/tip_wを1.2倍して打ち消して
# いる(出来上がりの鼻の幅は実測で変わらない)
_CORNER_ROUNDNESS_RATIO = 0.25
# 背面の中腹をへこませる量(カーブの高さ)を、その断面のdepth_backに
# 対する比率で指定
_BOOMERANG_BOW_RATIO = 0.75


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

    単純な円弧(弦の両端と中央の膨らみ量から求めるもの)だと、両端での
    接線が隣接する角丸フィレットの接線(水平)と一致せず、繋ぎ目で傾きが
    不連続になり縁が鋭く見えてしまう。余弦カーブは両端で傾きがちょうど0に
    なるため、フィレットの接線に滑らかに繋がる。
    """
    t = np.linspace(0.0, 1.0, num_points)
    x = x_start + (x_end - x_start) * t
    bow_z = z + bow_depth * 0.5 * (1 - np.cos(2 * np.pi * t))
    return np.stack([x, bow_z], axis=1)


def rounded_triangle_ring(
    half_width: float, depth_back: float, depth_front: float
) -> np.ndarray:
    """角丸三角形の輪郭点を (NUM_RING_POINTS, 2) で返す。

    背面(depth_back)側の2頂点を底辺、前面(depth_front)側の1頂点を頂点とする
    三角形の角を丸める。背面2角を結ぶ辺は直線ではなく、中腹がへこむ
    ブーメラン型のカーブにしている(_boomerang_bow)。
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
            vertices[i], edge_dirs[i], radius, betas[i], POINTS_PER_CORNER
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


def ring_at_y(half_width: float, depth_back: float, depth_front: float, y: float) -> np.ndarray:
    """角丸三角形の輪郭(x, z)にyを結合し、3D頂点列 (NUM_RING_POINTS, 3) にして返す。"""
    ring_2d = rounded_triangle_ring(half_width, depth_back, depth_front)
    y_col = np.full(len(ring_2d), y)
    return np.column_stack([ring_2d[:, 0], y_col, ring_2d[:, 1]])


def z_at_center(region: np.ndarray) -> float:
    """2D点列(region[:,0]がx, region[:,1]がz)のうち、x=0に最も近い点のzを返す。"""
    idx = np.argmin(np.abs(region[:, 0]))
    return float(region[idx, 1])
