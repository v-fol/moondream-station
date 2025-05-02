import urllib.request


def parse_version(version: str) -> tuple[int, ...]:
    """
    Strip any leading 'v', split on '.', and convert each component to int.
    E.g. 'v0.0.10' → (0, 0, 10)
    """
    if version and (version[0] in ("v", "V")):
        version = version[1:]
    return tuple(int(part) for part in version.split("."))


def parse_revision(revision: str) -> tuple[int, ...]:
    """
    Convert each component of a revision str to int.
    E.g. '2025-04-14' → (2025, 4, 14)
    """
    return tuple(int(part) for part in revision.split("-"))


def download_file(url, out_path, logger):
    logger.info(f"Downloading {url} -> {out_path}")
    urllib.request.urlretrieve(url, out_path)
    logger.info("Download complete.")
