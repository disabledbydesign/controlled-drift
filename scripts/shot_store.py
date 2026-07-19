#!/usr/bin/env python3
"""Binary store for friction snapshots — the PNGs that ride along with a Log entry.

CAPTURE ONLY, exactly like signal_log: the image is stored verbatim and never inspected,
resized, or classified. The signal record in signal_log.jsonl holds only the FILENAME; the
bytes live here, out of the JSONL so the log stays greppable and diffable.

⚠ These images are June's real screen — task names, medical and financial detail, the same
content that keeps scripts/data/ out of git. The directory is gitignored. Nothing here ever
leaves the machine.
"""
import sys, os, re, base64, datetime as dt, secrets
sys.path.insert(0, os.path.dirname(__file__))
import cd_paths

# A phone screenshot is well under a megabyte; 8MB is a generous ceiling that still refuses a
# runaway or hostile body outright rather than writing it to disk and finding out later.
MAX_BYTES = 8 * 1024 * 1024

_PREFIX = "data:image/png;base64,"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Exactly the shape save_png() generates: an ISO-ish timestamp, a hex suffix, .png. Anything
# else is refused, which is what makes read_png's path containment total.
_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-[0-9a-f]{12}\.png$")


def shots_dir():
    return cd_paths.data_file("shots")


def save_png(data_url):
    """Write one base64 PNG data URL to the shots dir; return its bare filename.

    Raises ValueError on anything that is not a PNG, or is over MAX_BYTES. We check the magic
    number rather than trusting the data-URL's own claim about its type: the prefix is written
    by the client and a mislabelled body would otherwise be stored as a .png that is not one.
    """
    if not isinstance(data_url, str) or not data_url.startswith(_PREFIX):
        raise ValueError("a snapshot must be a data:image/png;base64 URL")
    try:
        raw = base64.b64decode(data_url[len(_PREFIX):], validate=True)
    except Exception as e:
        raise ValueError("that snapshot was not valid base64: %s" % e)
    if len(raw) > MAX_BYTES:
        raise ValueError("that snapshot is larger than the %d byte limit" % MAX_BYTES)
    if not raw.startswith(_PNG_MAGIC):
        raise ValueError("that snapshot's bytes are not a PNG")

    name = "%s-%s.png" % (dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S"), secrets.token_hex(6))
    d = shots_dir()
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f:
        f.write(raw)
    return name


def read_png(name):
    """Bytes of one stored snapshot. Raises ValueError on a name this module did not generate."""
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ValueError("not a snapshot name")
    with open(os.path.join(shots_dir(), name), "rb") as f:
        return f.read()
