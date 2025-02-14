"""
Utilities for querying MMT systems to get information to include in image headers
"""

import json
import urllib3

import redis

import astropy.units as u
from astropy.units import cds
from astropy.io import fits

urllib3.disable_warnings()
API_HOST = "http://api.mmto.arizona.edu/APIv1"
REDIS_HOST = "ops2.mmto.arizona.edu"

HEADER_MAP = {
    "mount_mini_ra": {
        "fitskey": "RA",
        "comment": "Object RA",
        "units": u.hourangle,
    },
    "mount_mini_declination": {
        "fitskey": "DEC",
        "comment": "Object Dec",
        "units": u.deg,
    },
    "mount_mini_epoch": {
        "fitskey": "EPOCH",
        "comment": "Coordinate Epoch",
        "units": u.year,
    },
    "mount_mini_cat_id": {
        "fitskey": "CATID",
        "comment": "Catalog Source Name",
        "units": None,
    },
    "mount_mini_cat_ra2000": {
        "fitskey": "CATRA2K",
        "comment": "Catalog RA (J2000)",
        "units": u.hourangle,
    },
    "mount_mini_cat_dec2000": {
        "fitskey": "CATDEC2K",
        "comment": "Catalog Dec (J2000)",
        "units": u.deg,
    },
    "mount_mini_cat_ra": {
        "fitskey": "CATRA",
        "comment": "Catalog RA",
        "units": u.hourangle,
    },
    "mount_mini_cat_dec": {
        "fitskey": "CATDEC",
        "comment": "Catalog Dec",
        "units": u.deg,
    },
    "mount_mini_cat_epoch": {
        "fitskey": "CATEPOCH",
        "comment": "Catalog Epoch",
        "units": u.year,
    },
    "mount_mini_cat_rapm": {
        "fitskey": "CATRAPM",
        "comment": "Catalog RA proper motion",
        "units": (u.hourangle / 3600.0) / (100.0 * u.year),
    },
    "mount_mini_cat_decpm": {
        "fitskey": "CATDECPM",
        "comment": "Catalog Dec proper motion",
        "units": u.arcsec / (100.0 * u.year),
    },
    "mount_mini_alt": {
        "fitskey": "EL",
        "comment": "Object Elevation at time of observation",
        "units": u.deg,
    },
    "mount_mini_az": {
        "fitskey": "AZ",
        "comment": "Object Azimuth at time of observation",
        "units": u.deg,
    },
    "mount_mini_rot": {
        "fitskey": "ROT",
        "comment": "Instrument Rotator Angle",
        "units": u.deg,
    },
    "mount_mini_pa": {
        "fitskey": "PA",
        "comment": "Parallactic Angle",
        "units": u.deg,
    },
    "mount_mini_posang": {
        "fitskey": "POSANG",
        "comment": "Position Angle",
        "units": u.deg,
    },
    "mount_mini_mjd": {
        "fitskey": "MJD",
        "comment": "Modified Julian Data at time of observation",
        "units": u.day,
    },
    "mount_mini_uttime": {
        "fitskey": "UT",
        "comment": "UT of observation",
        "units": u.hour,
    },
    "mount_mini_lst": {
        "fitskey": "LST",
        "comment": "Sidereal Time of observation",
        "units": u.hour,
    },
    "mount_mini_ha": {
        "fitskey": "HA",
        "comment": "Hour Angle of observation",
        "units": u.hour,
    },
    "mount_mini_airmass": {
        "fitskey": "AIRMASS",
        "comment": "Object Airmass (Secant of Zenith Distance)",
        "units": None,
    },
    "mount_mini_total_off_alt": {
        "fitskey": "ELOFF",
        "comment": "Total elevation offset",
        "units": u.arcsec,
    },
    "mount_mini_total_off_az": {
        "fitskey": "AZOFF",
        "comment": "Total azimuth offset",
        "units": u.arcsec,
    },
    "mount_mini_total_off_ra": {
        "fitskey": "RAOFF",
        "comment": "Total RA offset",
        "units": u.arcsec,
    },
    "mount_mini_total_off_dec": {
        "fitskey": "DECOFF",
        "comment": "Total Dec offset",
        "units": u.arcsec,
    },
    "mount_mini_instoff_az": {
        "fitskey": "IAZOFF",
        "comment": "Instrument Az offset",
        "units": u.arcsec,
    },
    "mount_mini_instoff_alt": {
        "fitskey": "IELOFF",
        "comment": "Instrument El offset",
        "units": u.arcsec,
    },
    "mount_mini_offroti": {
        "fitskey": "IROTOFF",
        "comment": "Instrument Rotator offset",
        "units": u.deg,
    },
    "hexapod_mini_curxyz_z": {
        "fitskey": "TRANSZ",
        "comment": "Hexapod Z Translation, i.e. Focus (um)",
        "units": u.micron,
    },
    "hexapod_mini_curxyz_y": {
        "fitskey": "TRANSY",
        "comment": "Hexapod Y Translation (um)",
        "units": u.micron,
    },
    "hexapod_mini_curxyz_x": {
        "fitskey": "TRANSX",
        "comment": "Hexapod X Translation (um)",
        "units": u.micron,
    },
    "hexapod_mini_curxyz_tx": {
        "fitskey": "TILTX",
        "comment": "Hexapod X Tilt (arcsec)",
        "units": u.arcsec,
    },
    "hexapod_mini_curxyz_ty": {
        "fitskey": "TILTY",
        "comment": "Hexapod Y Tilt (arcsec)",
        "units": u.arcsec,
    },
    "hexapod_mini_curr_temp": {
        "fitskey": "OSSTEMP",
        "comment": "Average OSS Temperature",
        "units": u.Celsius,
    },
    "hexapod_mini_secondary": {
        "fitskey": "SECNDRY",
        "comment": "Mounted secondary mirror",
        "units": None,
    },
    "hexapod_mini_instrument": {
        "fitskey": "INST",
        "comment": "Mounted instrument",
        "units": None,
    },
    "ds_atmospheric_pressure": {
        "fitskey": "PRESSURE",
        "comment": "Barometric Pressure",
        "units": cds.mbar,
    },
    "ds_chamber_dew": {
        "fitskey": "CHAM_DPT",
        "comment": "Chamber Dewpoint",
        "units": u.Celsius,
    },
    "ds_chamber_rh": {
        "fitskey": "CHAM_RH",
        "comment": "Chamber RH",
        "units": u.percent,
    },
    "ds_chamber_temp": {
        "fitskey": "CHAM_T",
        "comment": "Chamber Temperature",
        "units": u.Celsius,
    },
    "ds_outside_dew": {
        "fitskey": "OUT_DPT",
        "comment": "Outside Dewpoint",
        "units": u.Celsius,
    },
    "ds_outside_rh": {
        "fitskey": "OUT_RH",
        "comment": "Outside RH",
        "units": u.percent,
    },
    "ds_outside_temp": {
        "fitskey": "OUT_T",
        "comment": "Outside Temperature",
        "units": u.Celsius,
    },
    "ds_east_wind_speed_mph": {
        "fitskey": "WIND_E",
        "comment": "Wind Speed (east sensor)",
        "units": u.imperial.mile / u.hour,
    },
    "ds_east_wind_direction": {
        "fitskey": "WDIR_E",
        "comment": "Wind Direction (east sensor)",
        "units": u.degree,
    },
    "ds_west_wind_speed_mph": {
        "fitskey": "WIND_W",
        "comment": "Wind Speed (west sensor)",
        "units": u.imperial.mile / u.hour,
    },
    "ds_west_wind_direction": {
        "fitskey": "WDIR_W",
        "comment": "Wind Direction (west sensor)",
        "units": u.degree,
    },
}


def get_redis_keys(r=redis.StrictRedis(host=REDIS_HOST)):
    keys = sorted([k.decode() for k in r.keys()])
    return keys


def get_redis(keys=[], r=redis.StrictRedis(host=REDIS_HOST)):
    if not isinstance(keys, list):
        keys = [keys]
    vals = r.mget(keys)
    return dict(zip(keys, vals))


def get_api_keys(http=urllib3.PoolManager()):
    """
    Get list of redis keys via the MMTO web api
    """
    url = API_HOST + "/keys"
    r = http.request("GET", url)
    data = json.loads(r.data.decode("utf-8"))
    return sorted(data)


def get_api(keys=[], http=urllib3.PoolManager()):
    """
    Given list of keys, return a dict containing the redis values for each keys
    """
    if not isinstance(keys, list):
        keys = [keys]
    url = API_HOST + "/vals"
    r = http.request("POST", url, fields={"keys": ",".join(keys)})
    data = json.loads(r.data.decode("utf-8"))
    return data


def update_header(f=fits.hdu.image.PrimaryHDU()):
    """
    Given a FITS PrimaryHDU object or a list of HDUs, insert data from redis into the primary headers
    and return updates HDU or HDU list
    """
    if isinstance(f, fits.hdu.image.PrimaryHDU):
        header = f.header
    elif isinstance(f, list):
        header = None
        for hdu in f:
            if isinstance(hdu, fits.hdu.image.PrimaryHDU):
                header = hdu.header
        if header is None:
            raise ValueError("No PrimaryHDU found in HDU list.")
    else:
        raise ValueError(
            "Must provide a PrimaryHDU object or an HDU list that contains one."
        )

    keys = list(HEADER_MAP.keys())
    data = get_api(keys)

    for k in keys:
        if k not in header:
            header.append((HEADER_MAP[k]["fitskey"], data[k], HEADER_MAP[k]["comment"]))
        else:
            header.comments[k] = HEADER_MAP[k]["comment"]

    return f
