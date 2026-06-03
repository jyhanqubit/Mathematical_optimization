# -*- coding: utf-8 -*-
"""polygeom.py
순수 파이썬 다각형 기하. shapely 없이 임의 단순다각형(오목 포함)의
'교차 면적'과 '차집합 면적'을 정확히 계산한다.
방법: ear-clipping 삼각분할 -> 삼각형 쌍마다 Sutherland-Hodgman 볼록 클리핑 면적 합.
"""
from __future__ import annotations

EPS = 1e-12


def signed_area(poly):
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def area(poly):
    return abs(signed_area(poly))


def _ccw(poly):
    return poly if signed_area(poly) >= 0 else poly[::-1]


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _pt_in_tri(p, a, b, c):
    """삼각형 내부(경계 제외, 약간의 tol)면 True."""
    d1 = _cross(a, b, p); d2 = _cross(b, c, p); d3 = _cross(c, a, p)
    has_neg = (d1 < -EPS) or (d2 < -EPS) or (d3 < -EPS)
    has_pos = (d1 > EPS) or (d2 > EPS) or (d3 > EPS)
    return not (has_neg and has_pos)


def triangulate(poly):
    """단순다각형 -> 삼각형 리스트 [(p0,p1,p2), ...]. 오목 다각형 지원(ear clipping)."""
    pts = [(float(x), float(y)) for x, y in poly]
    # 연속 중복 제거
    clean = []
    for p in pts:
        if not clean or (abs(p[0] - clean[-1][0]) > EPS or abs(p[1] - clean[-1][1]) > EPS):
            clean.append(p)
    if len(clean) >= 2 and abs(clean[0][0] - clean[-1][0]) < EPS and abs(clean[0][1] - clean[-1][1]) < EPS:
        clean.pop()
    n = len(clean)
    if n < 3:
        return []
    poly2 = _ccw(clean)
    idx = list(range(len(poly2)))
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        m = len(idx)
        ear = False
        for i in range(m):
            i0, i1, i2 = idx[(i - 1) % m], idx[i], idx[(i + 1) % m]
            a, b, c = poly2[i0], poly2[i1], poly2[i2]
            if _cross(a, b, c) <= EPS:        # reflex/collinear -> not an ear
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                if _pt_in_tri(poly2[j], a, b, c):
                    ok = False; break
            if ok:
                tris.append((a, b, c))
                del idx[i]
                ear = True
                break
        if not ear:
            break                              # 안전장치(단순다각형이면 도달 안 함)
    if len(idx) == 3:
        tris.append((poly2[idx[0]], poly2[idx[1]], poly2[idx[2]]))
    return [t for t in tris if area(t) > EPS]


def _inside(p, a, b):
    """볼록 클립 변 a->b 기준 내부(왼쪽, CCW)면 True."""
    return _cross(a, b, p) >= -EPS


def _seg_intersect(s, e, a, b):
    """선분 s-e 와 직선 a-b 의 교점."""
    x1, y1 = s; x2, y2 = e; x3, y3 = a; x4, y4 = b
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-15:
        return e
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def clip_convex(subject, clip):
    """subject(임의 다각형 정점)를 볼록 clip(CCW)로 잘라낸 다각형 정점 반환."""
    out = list(subject)
    cn = len(clip)
    for i in range(cn):
        A = clip[i]; B = clip[(i + 1) % cn]
        inp = out; out = []
        if not inp:
            break
        S = inp[-1]
        for E in inp:
            if _inside(E, A, B):
                if not _inside(S, A, B):
                    out.append(_seg_intersect(S, E, A, B))
                out.append(E)
            elif _inside(S, A, B):
                out.append(_seg_intersect(S, E, A, B))
            S = E
    return out


def _bbox(poly):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def intersection_area(polyA, polyB):
    """두 단순다각형의 교차 면적(정확)."""
    a0, b0, a1, b1 = _bbox(polyA); c0, d0, c1, d1 = _bbox(polyB)
    if a1 < c0 or c1 < a0 or b1 < d0 or d1 < b0:
        return 0.0
    trisA = triangulate(polyA)
    trisB = triangulate(polyB)
    total = 0.0
    for ta in trisA:
        ta_bb = _bbox(ta)
        for tb in trisB:
            tb_bb = _bbox(tb)
            if ta_bb[2] < tb_bb[0] or tb_bb[2] < ta_bb[0] or ta_bb[3] < tb_bb[1] or tb_bb[3] < ta_bb[1]:
                continue
            clipped = clip_convex(list(ta), _ccw(list(tb)))
            if len(clipped) >= 3:
                total += area(clipped)
    return total


def difference_area(polyA, polyB):
    """polyA - polyB 면적 = area(A) - 교차면적 (단순다각형 가정)."""
    return max(0.0, area(polyA) - intersection_area(polyA, polyB))


def point_in_poly(p, poly):
    """ray casting (Monte Carlo 검증용)."""
    x, y = p; n = len(poly); inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi):
            inside = not inside
        j = i
    return inside
