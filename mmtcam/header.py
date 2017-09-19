"""
Utilities for querying MMT systems to get information to include in image headers
"""

import json
from urllib.parse import urlencode
import urllib3
urllib3.disable_warnings()

API_HOST = "https://api.mmto.arizona.edu/APIv1"

def get_redis_keys(http=urllib3.PoolManager()):
    """
    Get list of redis keys via the MMTO web api
    """
    url = API_HOST + "/keys"
    r = http.request('GET', url)
    data = json.loads(r.data.decode('utf-8'))
    return sorted(data)

def get_redis(keys=[], http=urllib3.PoolManager()):
    """
    Given list of keys, return a dict containing the redis values for each keys
    """
    url = API_HOST + "/vals"
    r = http.request(
        'POST',
        url,
        fields={'keys': ",".join(keys)}
    )
    data = json.loads(r.data.decode('utf-8'))
    return data
