from collections import Counter

from gerrychain.utm import from_latlon


def utm_of_point(point):
    return from_latlon(point.y, point.x)[2]


def identify_utm_zone(df):
    wgs_df = df.to_crs("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
    utm_counts = Counter(utm_of_point(point) for point in wgs_df["geometry"].centroid)
    # most_common returns a list of tuples, and we want the 0,0th entry
    most_common = utm_counts.most_common(1)[0][0]
    return most_common


def reprojected(df):
    """Returns a copy of `df`, projected into the coordinate reference system of a suitable
        `Universal Transverse Mercator`_ zone.
    :param df: :class:`geopandas.GeoDataFrame`
    :rtype: :class:`geopandas.GeoDataFrame`

    .. _`Universal Transverse Mercator`: https://en.wikipedia.org/wiki/UTM_coordinate_system
    """
    utm = identify_utm_zone(df)
    return df.to_crs(
        f"+proj=utm +zone={utm} +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    )
