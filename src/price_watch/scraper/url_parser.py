"""Extract MercadoLibre item IDs from product URLs."""

from __future__ import annotations

import re
from urllib.parse import urlparse

# MercadoLibre item IDs: M + 2 uppercase country letters + digits
# e.g. MLA15485496 (Argentina), MLM3000123456 (Mexico), MCO1234567890 (Colombia)
_ML_ID = r"M[A-Z]{2}\d+"

# Pattern for /p/MLA15485496 (catalog product page)
RE_CATALOG = re.compile(r"/p/({})".format(_ML_ID))

# Pattern for /iphone-15-MLM3000123456 (direct listing)
RE_DIRECT = re.compile(r"-({})(?:\?|$|#)".format(_ML_ID))

# Pattern for raw item ID input
RE_RAW_ID = re.compile(r"^({})$".format(_ML_ID))


def extract_item_id(url: str) -> str | None:
    """Extract the MercadoLibre item ID from a URL or raw ID string.

    Supports:
    - https://www.mercadolibre.com.ar/p/MLA15485496  (catalog)
    - https://www.mercadolibre.com/iphone-15-MLM3000123456  (direct listing)
    - MLA15485496  (raw ID)
    """
    url = url.strip()

    # Raw ID
    if m := RE_RAW_ID.search(url):
        return m.group(1)

    # Parse as URL
    parsed = urlparse(url)
    path = parsed.path

    # Catalog pattern
    if m := RE_CATALOG.search(path):
        return m.group(1)

    # Direct listing — search whole URL in case ID is in query
    if m := RE_DIRECT.search(url):
        return m.group(1)

    return None
