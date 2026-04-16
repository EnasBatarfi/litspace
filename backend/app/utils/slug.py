# This is a modified version of the Django slugify function, which is licensed under the BSD License.
# It has been adapted to treat underscores as separators rather than characters to delete, and to collapse any run of non-alphanumeric characters into a single hyphen.
import re
import unicodedata


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()

    # Treat underscores like separators, not characters to delete
    value = value.replace("_", " ")

    # Collapse any run of non-alphanumeric characters into a single hyphen
    value = re.sub(r"[^a-z0-9]+", "-", value)

    return value.strip("-")