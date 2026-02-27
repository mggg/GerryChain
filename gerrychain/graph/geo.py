"""
This module contains functions for working with GeoDataFrames and Shapely
geometries. Specifically, it contains functions for handling and reprojecting
the Universal Transverse Mercator projection, and for identifying bad geometries
within a given GeoDataFrame.
"""

from collections import Counter

from geopandas import GeoDataFrame
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from gerrychain.vendor.utm import from_latlon


def utm_of_point(point: Point) -> int:
    """Given a point, return the Universal Transverse Mercator zone number for that point.

    Args:
        point (shapely.geometry.Point): A Shapely Point geometry object representing a geographic
            location.

    Returns:
        int: The Universal Transverse Mercator zone number for the given point.
    """
    return from_latlon(point.y, point.x)[2]


def identify_utm_zone(df: GeoDataFrame) -> int:
    """Given a GeoDataFrame, identify the UTM zone number for that GeoDataFrame.

    Note:
        This function uses the centroid of the geometries in the GeoDataFrame to determine the UTM
        zone.

    """
    wgs_df = df.to_crs("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
    utm_counts = Counter(utm_of_point(point) for point in wgs_df["geometry"].centroid)
    # most_common returns a list of tuples, and we want the 0,0th entry
    most_common = utm_counts.most_common(1)[0][0]
    return most_common


# Explicit type hint intentionally omitted here because of import issues.
def explain_validity(geo: BaseGeometry) -> str:
    """Given a geometry that is shapely interpretable, call Shapely's explain_validity function.

    Args:
        geo (shapely.geometry.BaseGeometry): Shapely geometry object

    Returns:
        str: Explanation for the validity of the geometry
    """
    import shapely.validation

    return shapely.validation.explain_validity(geo)


def invalid_geometries(df: GeoDataFrame) -> list[int]:
    """Given a GeoDataFrame, returns a list of row indices with invalid geometries.

    Args:
        df (GeoDataFrame): The GeoDataFrame to examine

    Returns:
        list of int: List of row indices with invalid geometries
    """
    invalid = []
    for idx, row in df.iterrows():
        validity = explain_validity(row.geometry)
        if validity != "Valid Geometry":
            invalid.append(idx)
    return invalid


def reprojected(df: GeoDataFrame) -> GeoDataFrame:
    """Returns a copy of `df`, projected into the CRS of a suitable UTM zone.

    Args:
        df (GeoDataFrame): The GeoDataFrame to reproject

    Returns:
        GeoDataFrame: A copy of `df`, projected into the coordinate reference
            system of a suitable UTM zone.
    .. _`Universal Transverse Mercator`: https://en.wikipedia.org/wiki/UTM_coordinate_system
    """
    utm = identify_utm_zone(df)
    return df.to_crs(f"+proj=utm +zone={utm} +ellps=WGS84 +datum=WGS84 +units=m +no_defs")


class GeometryError(Exception):
    """
    Wrapper error class for projection failures.
    Changing a map's projection may create invalid geometries, which may
    or may not be repairable using the `.buffer(0)`_ trick.

    .. _`.buffer(0)`: https://shapely.readthedocs.io/en/stable/manual.html#constructive-methods
    """
