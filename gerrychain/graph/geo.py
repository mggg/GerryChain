from collections import Counter
from shapely.validation import explain_validity
from gerrychain.vendor.utm import from_latlon


def utm_of_point(point):
    return from_latlon(point.y, point.x)[2]


def identify_utm_zone(df):
    wgs_df = df.to_crs("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
    utm_counts = Counter(utm_of_point(point) for point in wgs_df["geometry"].centroid)
    # most_common returns a list of tuples, and we want the 0,0th entry
    most_common = utm_counts.most_common(1)[0][0]
    return most_common


def invalid_geometries(df):
    """Given a GeoDataFrame, returns a list of row indices
    with invalid geometries.

    :param df: :class:`geopandas.GeoDataFrame`
    :rtype: list of int
    """
    invalid = []
    for idx, row in df.iterrows():
        validity = explain_validity(row.geometry)
        if validity != "Valid Geometry":
            invalid.append(idx)
    return invalid


def reprojected(df):
    """Returns a copy of `df`, projected into the coordinate reference system of a suitable
        `Universal Transverse Mercator`_ zone.
    :param df: :class:`geopandas.GeoDataFrame`
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
