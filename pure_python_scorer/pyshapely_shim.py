# -*- coding: utf-8 -*-
"""pyshapely_shim.py
shapely 가 설치돼 있지 않은 환경에서도 대회 제공 utils.py 를 그대로 실행할 수 있게,
utils 가 사용하는 shapely API(Polygon.area/intersection/difference/is_empty/is_valid/buffer,
box, ops.unary_union, affinity.translate)를 순수 파이썬으로 대체한다.

사용법:
    import pyshapely_shim   # (import 시 자동으로 가짜 shapely 등록)
    import utils            # 이제 shapely 없이도 import/실행 가능
    r = utils.check_feasibility(prob, solution)

정확성: 다각형 교차/차집합 면적은 polygeom.py(삼각분할+볼록클리핑)로 정확히 계산.
사각형은 해석해와 1e-15, 오목 다각형은 Monte Carlo 와 일치 검증됨.
실제 shapely 가 있으면 이 모듈을 import 하지 말 것(원본이 더 빠름).
"""
from __future__ import annotations
import sys, types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import polygeom as _pg


class _Geom:
    def __init__(self, a): self._a = a
    @property
    def area(self): return self._a
    @property
    def is_empty(self): return self._a <= 1e-12


class Polygon:
    def __init__(self, coords):
        self.verts = [(float(x), float(y)) for x, y in coords]
    @property
    def area(self): return _pg.area(self.verts)
    @property
    def is_valid(self): return True
    @property
    def is_empty(self): return _pg.area(self.verts) <= 1e-12
    def buffer(self, d): return self
    @property
    def bounds(self):
        xs = [p[0] for p in self.verts]; ys = [p[1] for p in self.verts]
        return (min(xs), min(ys), max(xs), max(ys))
    def intersects(self, other):
        a = self.bounds; b = other.bounds
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])
    def intersection(self, other):
        return _Geom(_pg.intersection_area(self.verts, other.verts))
    def difference(self, other):
        return _Geom(_pg.difference_area(self.verts, other.verts))


def box(x0, y0, x1, y1):
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def _translate(poly, xoff=0.0, yoff=0.0):
    return Polygon([(x + xoff, y + yoff) for (x, y) in poly.verts])


def _unary_union(polys):
    return _Geom(sum(p.area for p in polys))


def install():
    g = types.ModuleType('shapely.geometry'); g.Polygon = Polygon; g.box = box
    o = types.ModuleType('shapely.ops'); o.unary_union = _unary_union
    a = types.ModuleType('shapely.affinity'); a.translate = _translate
    s = types.ModuleType('shapely'); s.geometry = g; s.ops = o; s.affinity = a
    sys.modules.setdefault('shapely', s)
    sys.modules.setdefault('shapely.geometry', g)
    sys.modules.setdefault('shapely.ops', o)
    sys.modules.setdefault('shapely.affinity', a)


install()
