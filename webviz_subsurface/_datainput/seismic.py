import math
import numpy as np
import xtgeo
import oneseismic.simple as simple
from oneseismic.simple import aztools

import azure.identity
import azure.storage.blob as azblob

import datetime
from urllib.parse import urlsplit

from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient,
    generate_account_sas,
    generate_container_sas,
)

from webviz_config.common_cache import CACHE


def get_sas(resource, guid):
    credential = azure.identity.AzureCliCredential()
    client = azblob.BlobServiceClient(resource, credential=credential)

    now = datetime.datetime.now(datetime.timezone.utc)
    fivemin = datetime.timedelta(minutes=5)

    user_delegation_key = client.get_user_delegation_key(
        now - datetime.timedelta(minutes=5),
        now + datetime.timedelta(hours=2),
    )

    acc = urlsplit(resource).netloc.split(".")[0]
    return azblob.generate_container_sas(
        account_name=acc,
        container_name=guid,
        user_delegation_key=user_delegation_key,
        permission="r",
        start=now - fivemin,
        expiry=now + fivemin,
    )


def get_client():
    client = simple.simple_client("https://oneseismic.equinor.com")

    return client


def seismic_data():
    seismic = {
        "ashska_JS_21_20": "e4def7548efba2afc4c0d14677bd608eaf03534b",
        "ashska_JS_20": "218761ccaab1badcdee40051dcbe2a2750c5765e",
        "ashska_JS_21_TS_corr": "21974b9f94afdd959a108143bc5a5ac6647e762e",
    }

    return seismic


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_cube_data(cube_path: str) -> xtgeo.Cube:
    return xtgeo.cube_from_file(cube_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_xline(cube: xtgeo.Cube, xline: int) -> np.ndarray:
    idx = np.where(cube.xlines == xline)
    return cube.values[:, idx, :][:, 0, 0].T


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_iline(cube: xtgeo.Cube, iline: int) -> np.ndarray:
    idx = np.where(cube.ilines == iline)
    return cube.values[idx, :, :][0, 0, :].T


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_zslice(cube: xtgeo.Cube, zslice: float) -> np.ndarray:
    idx = np.where(cube.zslices == zslice)
    return cube.values[:, :, idx][:, :, 0, 0].T


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_os_line(sas, name, dim, lineno: int) -> np.ndarray:
    seismic = seismic_data()
    id = seismic.get(name)
    client = get_client()
    req = client.sliceByLineno(id, dim, lineno)(sas=sas)
    line = req.numpy().T
    return line


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_os_iline(sas, name, iline: int) -> np.ndarray:
    return get_os_line(sas, name, 0, iline)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_os_xline(sas, name, xline: int) -> np.ndarray:
    return get_os_line(sas, name, 1, xline)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_os_zslice(sas, name, zslice: int) -> np.ndarray:
    return get_os_line(sas, name, 2, zslice * 1000)


def get_horisontal_distances(xutm, yutm):
    d = 0
    dist = [d]
    for i in range(1, len(xutm)):
        x_dist = xutm[i] - xutm[i - 1]
        y_dist = yutm[i] - yutm[i - 1]
        delta = math.sqrt(x_dist * x_dist + y_dist * y_dist)

        d = d + delta
        dist.append(d)

    return dist


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_os_fence(client, sas, seismic, seismic_name, coords):
    print("get_os_fence")
    print("seismic", seismic)
    print("seismic_name", seismic_name)
    print("coords", coords)
    id = seismic.get(seismic_name)

    meta = client.metadata(id)(sas=sas)
    z = meta["cube"]["linenumbers"][2]
    vmin = float(z[0]) / 1000
    vmax = float(z[-1]) / 1000

    # Calculate horisontal distances
    x_resamp = []
    y_resamp = []
    xy_resamp = []

    for xy in coords:
        x_resamp.append(xy[0])
        y_resamp.append(xy[1])
        xy_resamp.append([xy[0], xy[1]])

    dist = get_horisontal_distances(x_resamp, y_resamp)
    hmin = dist[0]
    hmax = dist[-1]
    print("xy_resamp", xy_resamp)

    req = client.curtainByUTM(id, xy_resamp, attributes=["cdp"])(sas=sas)
    values = req.xarray().T
    print("values", values)
    return hmin, hmax, vmin, vmax, values
