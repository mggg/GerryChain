"""
This module contains functions for working with GeoDataFrames and Shapely
geometries. Specifically, it contains functions for handling and reprojecting
the Universal Transverse Mercator projection, and for identifying bad geometries
within a given GeoDataFrame.
"""

from collections import Counter
from gerrychain.vendor.utm import from_latlon

# from shapely.geometry.base import BaseGeometry
from geopandas import GeoDataFrame


def utm_of_point(point):
    """
    Given a point, return the Universal Transverse Mercator zone number
    for that point.
    """
    return from_latlon(point.y, point.x)[2]


def identify_utm_zone(df: GeoDataFrame) -> int:
    """
    Given a GeoDataFrame, identify the Universal Transverse Mercator zone
    number for the centroid of the geometries in the dataframe.
    """
    wgs_df = df.to_crs("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
    utm_counts = Counter(utm_of_point(point) for point in wgs_df["geometry"].centroid)
    # most_common returns a list of tuples, and we want the 0,0th entry
    most_common = utm_counts.most_common(1)[0][0]
    return most_common


# Explicit type hint intentionally omitted here because of import issues.
def explain_validity(geo) -> str:
    """
    Given a geometry that is shapely interpretable, explain the validity.
    Light wrapper around shapely's explain_validity.

    :param geo: Shapely geometry object
    :type geo: shapely.geometry.BaseGeometry

    :returns: Explanation for the validity of the geometry
    :rtype: str
    """
    import shapely.validation

    return shapely.validation.explain_validity(geo)


def invalid_geometries(df):
    """
    Given a GeoDataFrame, returns a list of row indices
    with invalid geometries.

    :param df: The GeoDataFrame to examine
    :type df: :class:`geopandas.GeoDataFrame`

    :returns: List of row indices with invalid geometries
    :rtype: list of int
    """
    invalid = []
    for idx, row in df.iterrows():
        validity = explain_validity(row.geometry)
        if validity != "Valid Geometry":
            invalid.append(idx)
    return invalid


def reprojected(df):
    """
    Returns a copy of `df`, projected into the coordinate reference system of a suitable
        `Universal Transverse Mercator`_ zone.

    :param df: The GeoDataFrame to reproject
    :type df: :class:`geopandas.GeoDataFrame`

    :returns: A copy of `df`, projected into the coordinate reference system of a suitable
        UTM zone.
    :rtype: :class:`geopandas.GeoDataFrame`

    .. _`Universal Transverse Mercator`: https://en.wikipedia.org/wiki/UTM_coordinate_system
    """
    utm = identify_utm_zone(df)
    return df.to_crs(
        "+proj=utm +zone={utm} +ellps=WGS84 +datum=WGS84 +units=m +no_defs".format(
            utm=utm
        )
    )


class GeometryError(Exception):
    """
    Wrapper error class for projection failures.
    Changing a map's projection may create invalid geometries, which may
    or may not be repairable using the `.buffer(0)`_ trick.

    .. _`.buffer(0)`: https://shapely.readthedocs.io/en/stable/manual.html#constructive-methods
    """
