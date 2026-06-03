"""candidates.py
후보 placement 생성. 연속 좌표를 직접 변수화하지 않고
가능한 (orientation, x, y) 정수 후보를 추려서 알고리즘이 그 중 하나를 고르게 한다.
(기획안 7.2: 좌하단(0,0), 기배치 block의 AABB 접점, skyline candidate point, grid)
"""
from __future__ import annotations
import math
from geometry import base_polygons, poly_aabb


def origin_range(base_polys, W, H):
    """containment을 만족하는 정수 reference 좌표 (x,y) 범위.
       block-local AABB가 (minx,miny,maxx,maxy)일 때
       0 <= x+minx, x+maxx <= W  ->  x in [ceil(-minx), floor(W-maxx)]."""
    minx, miny, maxx, maxy = poly_aabb(base_polys)
    xlo, xhi = math.ceil(-minx), math.floor(W - maxx)
    ylo, yhi = math.ceil(-miny), math.floor(H - maxy)
    return xlo, xhi, ylo, yhi


def fits(block, W, H):
    """이 bay에 들어갈 수 있는 첫 orientation 의 (o, x, y)를 반환, 없으면 None."""
    for o, polys in base_polygons(block).items():
        xlo, xhi, ylo, yhi = origin_range(polys, W, H)
        if xlo <= xhi and ylo <= yhi:
            return o, xlo, ylo
    return None


def skyline_points(occupied_aabbs, W, H):
    """이미 놓인 block들의 AABB에서 파생한 접점 후보 (좌하단 포함)."""
    pts = {(0, 0)}
    for (x0, y0, x1, y1) in occupied_aabbs:
        pts.add((x1, 0)); pts.add((x1, y0))     # 오른쪽 접점
        pts.add((0, y1)); pts.add((x0, y1))     # 위쪽 접점
    return [(px, py) for (px, py) in pts if 0 <= px <= W and 0 <= py <= H]


def generate(block, W, H, occupied_aabbs=(), grid=None, max_cands=400):
    """후보 (orient, x, y) 리스트. 좌하단 우선 정렬."""
    cands = []
    cps = skyline_points(occupied_aabbs, W, H)
    for o, polys in base_polygons(block).items():
        xlo, xhi, ylo, yhi = origin_range(polys, W, H)
        if xlo > xhi or ylo > yhi:
            continue                              # 이 orient로는 안 들어감
        cands.append((o, xlo, ylo))               # 코너
        for (cx, cy) in cps:                      # 접점
            if xlo <= cx <= xhi and ylo <= cy <= yhi:
                cands.append((o, int(cx), int(cy)))
        if grid:                                  # 선택적 거친 grid
            for gx in range(xlo, xhi + 1, grid):
                for gy in range(ylo, yhi + 1, grid):
                    cands.append((o, gx, gy))
    # 중복 제거 + 좌하단 우선
    cands = sorted(set(cands), key=lambda c: (c[2], c[1], c[0]))
    return cands[:max_cands]
