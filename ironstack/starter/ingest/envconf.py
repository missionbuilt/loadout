#!/usr/bin/env python3
"""One reading of the Elasticsearch environment, shared by every script here.

Three scripts used to read ES_ENDPOINT and ES_API_KEY three different ways:
setup_indices stripped a trailing "/" off *both* values, index_workouts stripped
whitespace off both, and verify_index did neither. The first is a data-corruption
bug rather than a tidy-up: "/" is in the base64 alphabet, so an API key that ends
in one was silently truncated and the cluster answered 401 with nothing in the
repo to explain it. The last means a trailing newline picked up from `source .env`
failed verification while indexing succeeded.

So: a URL is stripped and has its trailing slashes removed; a secret is stripped
and nothing else is ever done to it.
"""

from __future__ import annotations

import os
import sys


def env_url(name: str) -> str:
    """A URL from the environment: whitespace-stripped, no trailing slash."""
    value = os.environ.get(name, "").strip().rstrip("/")
    if not value:
        sys.exit(f"error: {name} is not set")
    return value


def env_secret(name: str) -> str:
    """A secret from the environment: whitespace-stripped, and nothing else.

    Never rstrip("/") this. Base64 keys legitimately end in "/" and "=".
    """
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"error: {name} is not set")
    return value
