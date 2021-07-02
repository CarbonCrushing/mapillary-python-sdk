"""
mapillary.utils.client

This module contains aims to serve as a generalization for all API
requests within the mapillary python SDK.

# Notes:
- To enter DEBUG mode, set a DEBUG environment variable = 1

## Over Authentication

1. All requests against https://graph.mapillary.com
must be authorized. They require a client or user
access tokens. Tokens can be sent in two ways
    1. Using ?access_token=XXX query parameters. This
    is a preferred method for interacting with vector
    tiles. Using this method is STRONGLY discouraged
    for sending user access tokens
    2. using a header such as Authorization: OAuth XXX,
    where XXX is the token obtained either through the
    OAuth flow that your application implements or a
    client token from https://mapillary.com/dashboard/developers
    This method works for the Entity API

# References:
- https://www.mapillary.com/developer/api-documentation/
- https://github.com/michaeldbianchi/Python-API-Client-Boilerplate
"""

import requests
import logging
import sys
import os
from math import floor


# Root endpoint for vector tiles
TILES_URL = "https://tiles.mapillary.com"

# Root endpoint for metadata
GRAPH_URL = "https://graph.mapillary.com"

# Basic logger setup
logger = logging.getLogger("mapillary.utils.client")

# stdout logger setup
hdlr = logging.StreamHandler(sys.stdout)
logger.addHandler(hdlr)

# Setting log_level to INFO
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

# Check if in DEBUG mode to show debugging output
if os.environ.get("DEBUG") == "1":
    log_level = "DEBUG"
try:
    logger.setLevel(log_level)
except ValueError:
    logger.setLevel(logging.INFO)
    logger.warn("LOG_LEVEL: unvalid variable - Defaulting to: INFO")


class Client:
    """
    Client setup for API communication. All requests for the Mapillary API v4 should go through this class

    Usage::
        >>> client = Client(access_token=MLY||XXX)
        >>> # for entities endpoints
        >>> client.get(endpoint='endpoint specific path', graph=True, params={
            'fields': ['id', 'value']
        })
        >>> # for tiles endpoint
        >>> client.get(endpoint='endpoint specific path', graph=False)
    """

    def __init__(self, access_token=None) -> None:

        self.url = GRAPH_URL  # Default to metadata endpoint

        # Session object setup to be referenced across future API calls.
        self.session = requests.Session()

        # User Access token will be set once and used throughout all requests within the same session
        self.access_token = access_token

    def __initiate_request(self, url, method, params={}):
        """
        Private method - For internal use only.
        This method is responsible for making tailored API requests to the mapillary API v4.
        It generalizes the requests and ties them to the same session.

        :param url: the request endpoint - required
        :param method: HTTP method to be used - required
        :param params: query parameters to be attached to the requeset - optional
        """

        request = requests.Request(method, url, params=params)

        # create a prepared request with the request and the session info merged
        prepped_req = self.session.prepare_request(request)

        # Log the prepped request before sending it.
        self.__pprint_request(prepped_req)

        # Sending the request
        res = self.session.send(prepped_req)

        # Log the responses
        self.__pprint_response(res)

        # Handling the response status codes
        if res.status_code == requests.codes.ok:
            try:
                logger.debug(f"Response: {res.json()}")
            except ValueError:
                return res

        elif res.status_code >= 400:
            logger.error(f"Srever responded with a {str(res.status_code)} error!")
            try:
                logger.debug(f"Error details: {str(res.json())}")

            except ValueError:
                ...
            res.raise_for_status()

        return res

    def get(self, graph=True, endpoint=None, params={}):
        """
        Make GET requests to both mapillary main endpoints
        :param graph: A boolean to dinamically switch between the entities and tiles endpoints
        :param enpoint: The specific path of the request enpoint
        :param params: Query paramaters to be attached to the URL (Dict)
        """
        # Check if an enpoint is specified.
        if endpoint is None:
            logger.error("You need to specify an endpoint!")
            return

        # Dynamically set authorization mechanism based on the target endpoint
        if not graph:
            self.url = TILES_URL
            params["access_token"] = params.get("access_token", self.access_token)
        else:
            self.session.headers.update({"Authorization": f"OAuth {self.access_token}"})

        url = self.url + endpoint
        return self.__initiate_request(url=url, method="GET", params=params)

    def __pprint_request(self, prepped_req):
        """
        method endpoint HTTP/version
        Host: host
        header_key: header_value
        body
        :param prepped_req: The prepped request object
        ref: https://github.com/michaeldbianchi/Python-API-Client-Boilerplate/blob/fd1c82be9e98e24730c4631ffc30068272386669/exampleClient.py#L202
        """
        method = prepped_req.method
        url = prepped_req.path_url

        headers = "\n".join(f"{k}: {v}" for k, v in prepped_req.headers.items())
        # Print body if present or empty string if not
        body = prepped_req.body or ""

        logger.info(f"Requesting {method} to {url}")

        logger.debug(
            "{}\n{} {} HTTP/1.1\n{}\n\n{}".format(
                "-----------REQUEST-----------", method, url, headers, body
            )
        )

    def __pprint_response(self, res):
        """
        HTTP/version status_code status_text
        header_key: header_value
        body
        :param res: Response object returned from the API request
        ref: https://github.com/michaeldbianchi/Python-API-Client-Boilerplate/blob/fd1c82be9e98e24730c4631ffc30068272386669/exampleClient.py#L230
        """
        httpv0, httpv1 = list(str(res.raw.version))
        httpv = f"HTTP/{httpv0}.{httpv1}"
        status_code = res.status_code
        status_text = res.reason
        headers = "\n".join(f"{k}: {v}" for k, v in res.headers.items())
        body = res.text or ""

        # Convert timedelta to milliseconds
        elapsed = floor(res.elapsed.total_seconds() * 1000)

        logger.info(f"Response {status_code} {status_text} received in {elapsed}ms")

        logger.debug(
            "{}\n{} {} {}\n{}\n\n{}".format(
                "-----------RESPONSE-----------",
                httpv,
                status_code,
                status_text,
                headers,
                body,
            )
        )
