# This is a simple slugify function that converts a string into a URL-friendly slug. It normalizes the string, removes non-alphanumeric characters, and replaces spaces with hyphens.
# For example, "Hello World!" would become "hello-world". This is useful for creating clean URLs based on titles or names.

import re
import unicodedata


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"[\s-]+", "-", value)
    return value.strip("-")