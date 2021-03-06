from typing import Iterator, Union, Iterable, Optional
from math import asin, atan2, cos, sin
import math
import geopy.distance as geod
import numpy as np

from .types import Coordinates, CoordinatesTuple


# lambert = Proj("epsg:2154")
PointLike = Union[CoordinatesTuple, "Point"]


class Point(object):
    """Represents a point as (lon, lat)"""

    def __init__(self, lon: float, lat: float) -> None:
        self.lon: float = lon
        self.lat: float = lat

    def __getitem__(self, item: int) -> float:
        if item == 0:
            return self.lon
        if item == 1:
            return self.lat
        raise KeyError(f"Invalid key '{item}' (should be 0 or 1)")

    def __iter__(self) -> Iterator[float]:
        return iter((self.lon, self.lat))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.lon}, {self.lat})"

    def __hash__(self) -> int:
        return hash(tuple(self))

    def to_JSON(self) -> Coordinates:
        return dict(lon=self.lon, lat=self.lat)

    @classmethod
    def from_latlon(cls, lat: float, lon: float) -> "Point":
        return cls(lon, lat)

    @property
    def url(self) -> str:
        return f"https://www.google.com/maps/@{self.lat:.7f},{self.lon:.7f},18z"

    def as_deg(self) -> CoordinatesTuple:
        return (self.lon, self.lat)

    def as_rad(self) -> CoordinatesTuple:
        return math.radians(self.lon), math.radians(self.lat)

    @property
    def lonlat(self) -> CoordinatesTuple:
        return (self.lon, self.lat)

    @property
    def latlon(self) -> CoordinatesTuple:
        return self.lat, self.lon

    def round(self, prec: int = 4) -> "Point":
        return Point(round(self.lon, prec), round(self.lat, prec))


def vectorized_distance(
    ref: PointLike, points: list[CoordinatesTuple]
) -> Iterable[CoordinatesTuple]:
    # phi = lat, lam = lon
    lons, lats = np.deg2rad(points).transpose()
    lon, lat = to_rad(ref)
    a = (
        np.sin((lats - lat) / 2) ** 2
        + np.cos(lat) * np.cos(lats) * np.sin((lons - lon) / 2) ** 2
    )
    return 6371 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def move(start: PointLike, theta: float, distance: float) -> CoordinatesTuple:
    lam, phi = to_rad(start)
    delta = distance / 6371.0

    phi2 = asin(sin(phi) * cos(delta) + cos(phi) * sin(delta) * cos(theta))
    lam2 = lam + atan2(
        sin(delta) * sin(theta) * cos(phi), cos(delta) - sin(phi) * sin(phi2)
    )

    lon2, lat2 = to_deg((lam2, phi2))
    return lon2, lat2


def vectorized_circle(
    center: PointLike, dist: float, n_points: Optional[int] = None
) -> list[CoordinatesTuple]:
    if n_points is None:
        full_length = 2 * math.pi * dist
        # Number of points per kilometer
        every = 1.0
        n_points = math.floor(full_length / every)

    thetas = 2 * math.pi * np.arange(0, n_points) / n_points
    lam, phi = to_rad(center)
    delta = dist / 6371.0

    phi2 = np.arcsin(sin(phi) * cos(delta) + cos(phi) * sin(delta) * np.cos(thetas))
    lam2 = lam + np.arctan2(
        sin(delta) * np.sin(thetas) * cos(phi), cos(delta) - sin(phi) * np.sin(phi2)
    )

    points = [(lon, lat) for lon, lat in zip(np.rad2deg(lam2), np.rad2deg(phi2))]
    return points


def to_deg(p: PointLike) -> CoordinatesTuple:
    lam, phi = p
    return math.degrees(lam), math.degrees(phi)


def to_rad(p: PointLike) -> CoordinatesTuple:
    lon, lat = p
    return math.radians(lon), math.radians(lat)


def round_point(point: PointLike, prec: int = 4) -> CoordinatesTuple:
    # def round(z): return math.floor(z * 10**prec) / 10**prec
    x, y = point
    return round(x, prec), round(y, prec)


def convert_points(points: Iterable[PointLike]) -> list[CoordinatesTuple]:
    return [round_point(point) for point in points]
    # return [lambert(x, y, inverse=True) for x, y in points]


def angle(start: PointLike, point: PointLike) -> float:
    lam1, phi1 = to_rad(start)
    lam2, phi2 = to_rad(point)
    y = math.sin(lam2 - lam1) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(
        lam2 - lam1
    )
    theta = math.atan2(y, x)
    return normalize_angle(theta)  # (theta + 2*math.pi) % (2*math.pi)


def normalize_angle(a: float) -> float:
    return a % (2 * math.pi)


def distance(pointA: PointLike, pointB: PointLike) -> float:
    p1 = geod.lonlat(*pointA)
    p2 = geod.lonlat(*pointB)
    return geod.distance(p1, p2).km


def move_given_angle(
    theta: float, start: PointLike, distance: float, verbose: bool = False
) -> CoordinatesTuple:
    lam, phi = to_rad(start)
    delta = distance / 6371.0

    phi2 = asin(sin(phi) * cos(delta) + cos(phi) * sin(delta) * cos(theta))
    lam2 = lam + atan2(
        sin(delta) * sin(theta) * cos(phi), cos(delta) - sin(phi) * sin(phi2)
    )

    lon2, lat2 = to_deg((lam2, phi2))

    if verbose:
        print("angle:", theta, f"(ie {math.degrees(theta):.0f}°)")
        print("start:", *start)
        print("end:  ", lon2, lat2)
        print("")
    return lon2, lat2


def get_curr_angle(point: PointLike, ref: PointLike, center: PointLike) -> float:
    normal_angle = normalize_angle(angle(center, ref) + math.pi / 2)
    return normalize_angle(angle(ref, point) - normal_angle)
