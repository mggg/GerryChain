from typing import Any

import numpy as mathlib
import numpy.typing as npt

from .error import OutOfRangeError

Coordinate = float | npt.NDArray[Any]

__all__ = ["to_latlon", "from_latlon"]

K0 = 0.9996

E = 0.00669438
E2 = E * E
E3 = E2 * E
E_P2 = E / (1.0 - E)

SQRT_E = mathlib.sqrt(1 - E)
_E = (1 - SQRT_E) / (1 + SQRT_E)
_E2 = _E * _E
_E3 = _E2 * _E
_E4 = _E3 * _E
_E5 = _E4 * _E

M1 = 1 - E / 4 - 3 * E2 / 64 - 5 * E3 / 256
M2 = 3 * E / 8 + 3 * E2 / 32 + 45 * E3 / 1024
M3 = 15 * E2 / 256 + 45 * E3 / 1024
M4 = 35 * E3 / 3072

P2 = 3.0 / 2 * _E - 27.0 / 32 * _E3 + 269.0 / 512 * _E5
P3 = 21.0 / 16 * _E2 - 55.0 / 32 * _E4
P4 = 151.0 / 96 * _E3 - 417.0 / 128 * _E5
P5 = 1097.0 / 512 * _E4

R = 6378137

ZONE_LETTERS = "CDEFGHJKLMNPQRSTUVWXX"


def in_bounds(x: Coordinate, lower: float, upper: float, upper_strict: bool = False) -> bool:
    if upper_strict:
        return bool(lower <= mathlib.min(x)) and bool(mathlib.max(x) < upper)
    return bool(lower <= mathlib.min(x)) and bool(mathlib.max(x) <= upper)


def check_valid_zone(zone_number: int, zone_letter: str | None) -> None:
    if not 1 <= zone_number <= 60:
        raise OutOfRangeError("zone number out of range (must be between 1 and 60)")

    if zone_letter:
        zone_letter = zone_letter.upper()

        if not "C" <= zone_letter <= "X" or zone_letter in ["I", "O"]:
            raise OutOfRangeError("zone letter out of range (must be between C and X)")


def mixed_signs(x: Coordinate) -> bool:
    return bool(mathlib.min(x) < 0) and bool(mathlib.max(x) >= 0)


def negative(x: Coordinate) -> bool:
    return bool(mathlib.max(x) < 0)


def to_latlon(
    easting: Coordinate,
    northing: Coordinate,
    zone_number: int,
    zone_letter: str | None = None,
    northern: bool | None = None,
    strict: bool = True,
) -> tuple[Coordinate, Coordinate]:
    """Convert a UTM coordinate to latitude and longitude.

    Args:
        easting (Coordinate): Easting value of the UTM coordinate.
        northing (Coordinate): Northing value of the UTM coordinate.
        zone_number (int): UTM zone number from 1 through 60.
        zone_letter (str | None, optional): UTM zone letter. Defaults to ``None``.
        northern (bool | None, optional): Whether the coordinate is in the northern hemisphere.
            Defaults to ``None``.
        strict (bool, optional): Whether to validate coordinate bounds. Defaults to ``True``.

    Returns:
        tuple[Coordinate, Coordinate]: Latitude and longitude.

    Raises:
        ValueError: If neither or both hemisphere indicators are provided.
        OutOfRangeError: If a coordinate or zone is outside its valid range.
    """
    if not zone_letter and northern is None:
        raise ValueError("either zone_letter or northern needs to be set")

    elif zone_letter and northern is not None:
        raise ValueError("set either zone_letter or northern, but not both")

    if strict:
        if not in_bounds(easting, 100000, 1000000, upper_strict=True):
            raise OutOfRangeError("easting out of range (must be between 100.000 m and 999.999 m)")
        if not in_bounds(northing, 0, 10000000):
            raise OutOfRangeError("northing out of range (must be between 0 m and 10.000.000 m)")

    check_valid_zone(zone_number, zone_letter)

    if zone_letter:
        zone_letter = zone_letter.upper()
        northern = zone_letter >= "N"

    x = easting - 500000
    y = northing

    if not northern:
        y -= 10000000

    m = y / K0
    mu = m / (R * M1)

    p_rad = (
        mu
        + P2 * mathlib.sin(2 * mu)
        + P3 * mathlib.sin(4 * mu)
        + P4 * mathlib.sin(6 * mu)
        + P5 * mathlib.sin(8 * mu)
    )

    p_sin = mathlib.sin(p_rad)
    p_sin2 = p_sin * p_sin

    p_cos = mathlib.cos(p_rad)

    p_tan = p_sin / p_cos
    p_tan2 = p_tan * p_tan
    p_tan4 = p_tan2 * p_tan2

    ep_sin = 1 - E * p_sin2
    ep_sin_sqrt = mathlib.sqrt(1 - E * p_sin2)

    n = R / ep_sin_sqrt
    r = (1 - E) / ep_sin

    c = _E * p_cos**2
    c2 = c * c

    d = x / (n * K0)
    d2 = d * d
    d3 = d2 * d
    d4 = d3 * d
    d5 = d4 * d
    d6 = d5 * d

    latitude = (
        p_rad
        - (p_tan / r) * (d2 / 2 - d4 / 24 * (5 + 3 * p_tan2 + 10 * c - 4 * c2 - 9 * E_P2))
        + d6 / 720 * (61 + 90 * p_tan2 + 298 * c + 45 * p_tan4 - 252 * E_P2 - 3 * c2)
    )

    longitude = (
        d
        - d3 / 6 * (1 + 2 * p_tan2 + c)
        + d5 / 120 * (5 - 2 * c + 28 * p_tan2 - 3 * c2 + 8 * E_P2 + 24 * p_tan4)
    ) / p_cos

    return (
        mathlib.degrees(latitude),
        mathlib.degrees(longitude) + zone_number_to_central_longitude(zone_number),
    )


def from_latlon(
    latitude: Coordinate,
    longitude: Coordinate,
    force_zone_number: int | None = None,
    force_zone_letter: str | None = None,
) -> tuple[Coordinate, Coordinate, int, str | None]:
    """Convert latitude and longitude to a UTM coordinate.

    Args:
        latitude (Coordinate): Latitude between 80 degrees south and 84 degrees north.
        longitude (Coordinate): Longitude between 180 degrees west and 180 degrees east.
        force_zone_number (int | None, optional): UTM zone number to use. Defaults to ``None``.
        force_zone_letter (str | None, optional): UTM zone letter to use. Defaults to ``None``.

    Returns:
        tuple[Coordinate, Coordinate, int, str | None]: Easting, northing, zone number, and zone
            letter.

    Raises:
        OutOfRangeError: If a coordinate or forced zone is outside its valid range.
    """
    if not in_bounds(latitude, -80.0, 84.0):
        raise OutOfRangeError("latitude out of range (must be between 80 deg S and 84 deg N)")
    if not in_bounds(longitude, -180.0, 180.0):
        raise OutOfRangeError("longitude out of range (must be between 180 deg W and 180 deg E)")
    if force_zone_number is not None:
        check_valid_zone(force_zone_number, force_zone_letter)

    lat_rad = mathlib.radians(latitude)
    lat_sin = mathlib.sin(lat_rad)
    lat_cos = mathlib.cos(lat_rad)

    lat_tan = lat_sin / lat_cos
    lat_tan2 = lat_tan * lat_tan
    lat_tan4 = lat_tan2 * lat_tan2

    if force_zone_number is None:
        zone_number = latlon_to_zone_number(latitude, longitude)
    else:
        zone_number = force_zone_number

    if force_zone_letter is None:
        zone_letter = latitude_to_zone_letter(latitude)
    else:
        zone_letter = force_zone_letter

    lon_rad = mathlib.radians(longitude)
    central_lon = zone_number_to_central_longitude(zone_number)
    central_lon_rad = mathlib.radians(central_lon)

    n = R / mathlib.sqrt(1 - E * lat_sin**2)
    c = E_P2 * lat_cos**2

    a = lat_cos * (lon_rad - central_lon_rad)
    a2 = a * a
    a3 = a2 * a
    a4 = a3 * a
    a5 = a4 * a
    a6 = a5 * a

    m = R * (
        M1 * lat_rad
        - M2 * mathlib.sin(2 * lat_rad)
        + M3 * mathlib.sin(4 * lat_rad)
        - M4 * mathlib.sin(6 * lat_rad)
    )

    easting = (
        K0
        * n
        * (
            a
            + a3 / 6 * (1 - lat_tan2 + c)
            + a5 / 120 * (5 - 18 * lat_tan2 + lat_tan4 + 72 * c - 58 * E_P2)
        )
        + 500000
    )

    northing = K0 * (
        m
        + n
        * lat_tan
        * (
            a2 / 2
            + a4 / 24 * (5 - lat_tan2 + 9 * c + 4 * c**2)
            + a6 / 720 * (61 - 58 * lat_tan2 + lat_tan4 + 600 * c - 330 * E_P2)
        )
    )

    if mixed_signs(latitude):
        raise ValueError("latitudes must all have the same sign")
    elif negative(latitude):
        northing += 10000000

    return easting, northing, zone_number, zone_letter


def latitude_to_zone_letter(latitude: Coordinate) -> str | None:
    # If the input is a numpy array, just use the first element
    # User responsibility to make sure that all points are in one zone
    if isinstance(latitude, mathlib.ndarray):
        latitude = float(latitude.flat[0])

    if -80 <= latitude <= 84:
        return ZONE_LETTERS[int(latitude + 80) >> 3]
    else:
        return None


def latlon_to_zone_number(latitude: Coordinate, longitude: Coordinate) -> int:
    # If the input is a numpy array, just use the first element
    # User responsibility to make sure that all points are in one zone
    if isinstance(latitude, mathlib.ndarray):
        latitude = float(latitude.flat[0])
    if isinstance(longitude, mathlib.ndarray):
        longitude = float(longitude.flat[0])

    if 56 <= latitude < 64 and 3 <= longitude < 12:
        return 32

    if 72 <= latitude <= 84 and longitude >= 0:
        if longitude < 9:
            return 31
        elif longitude < 21:
            return 33
        elif longitude < 33:
            return 35
        elif longitude < 42:
            return 37

    return int((longitude + 180) / 6) + 1


def zone_number_to_central_longitude(zone_number: int) -> int:
    return (zone_number - 1) * 6 - 180 + 3
