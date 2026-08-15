"""
Abstract Base Acquisition Adapter and Transport Interface (RA-013).

Defines the isolated HTTP transport interface and abstract base class for
structured public source acquisition adapters (NHTSA vPIC and EPA FuelEconomy.gov).
"""

import json
import ssl
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple

from reference.ingestion.contracts import SourceAssertionSet


class AcquisitionError(Exception):
    """Base exception for external source acquisition errors."""
    pass


class TransportError(AcquisitionError):
    """Raised when an HTTP transport or network failure occurs."""
    pass


class SourceParseError(AcquisitionError):
    """Raised when a source response is malformed or unexpected."""
    pass


# Transport callable signature: (url, headers, timeout_seconds) -> (status_code, body_bytes, headers_dict)
TransportCallable = Callable[[str, Dict[str, str], int], Tuple[int, bytes, Dict[str, str]]]


def default_http_transport(url: str, headers: Dict[str, str], timeout_seconds: int = 10) -> Tuple[int, bytes, Dict[str, str]]:
    """
    Default HTTP transport using Python standard library urllib.request.
    Enforces a finite timeout, explicit User-Agent header, and strict TLS certificate verification.
    """
    req = urllib.request.Request(url, headers=headers, method="GET")
    ssl_context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds, context=ssl_context) as response:
            status_code = response.status
            body = response.read()
            resp_headers = dict(response.headers)
            return status_code, body, resp_headers
    except urllib.error.HTTPError as e:
        body = e.read() if e.fp else b""
        return e.code, body, dict(e.headers)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise TransportError(f"HTTP request failed to '{url}': {str(e)}") from e




class BaseSourceAdapter(ABC):
    """
    Abstract base class for external source acquisition adapters.
    Isolates network transport from source-native payload parsing and
    Tier 1 SourceAssertionSet construction.
    """

    DEFAULT_USER_AGENT = "RigArchive-Ingestion/0.1.0 (RigArchive Technical Archive Project; +https://github.com/rigarchive)"

    def __init__(
        self,
        transport: Optional[TransportCallable] = None,
        timeout_seconds: int = 10,
        user_agent: Optional[str] = None,
    ):
        self.transport = transport or default_http_transport
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT

    @property
    @abstractmethod
    def source_id(self) -> str:
        """RigArchive-local stable source identifier (e.g. 'nhtsa_vpic', 'epa_fueleconomy')."""
        pass

    def _fetch_json(self, url: str, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute HTTP GET request and parse JSON response payload."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        status_code, body_bytes, resp_headers = self.transport(url, headers, self.timeout_seconds)

        if status_code != 200:
            raise TransportError(f"Source '{self.source_id}' returned HTTP {status_code} for URL '{url}'. Body excerpt: {body_bytes[:200]!r}")

        if not body_bytes:
            raise SourceParseError(f"Source '{self.source_id}' returned empty response body for URL '{url}'.")

        try:
            return json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise SourceParseError(f"Source '{self.source_id}' returned invalid JSON from '{url}': {str(e)}") from e
