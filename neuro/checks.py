"""Some checks to run on files"""

import os
import tomllib as toml
from itertools import chain
from pathlib import Path
from string import ascii_letters, digits

from loguru import logger
from tqdm import tqdm

from neuro import LOG_DIR, ROOT_DIR
from neuro.polars_utils import load_db
from neuro.utils import format_logger, get_sha256


def check_ascii() -> None:
    """Checks if the artists and songs are properly sanitized regarding
    characters by displaying them in the console."""
    ALPHANUM = set(ascii_letters + digits)

    songs = load_db()
    no_ascii = songs.get_column("Song").to_list() + songs.get_column("Artist").to_list()
    ascii = songs.get_column("Song_ASCII").to_list() + songs.get_column("Artist_ASCII").to_list()

    no_ascii_ok = set(chain.from_iterable(no_ascii)) - ALPHANUM
    ascii_ok = set(chain.from_iterable(ascii)) - ALPHANUM

    def pp(s: set) -> str:
        return ", ".join(map(repr, sorted(s, key=ord)))

    logger.info(f"No ASCII only: {pp(no_ascii_ok - ascii_ok)}")
    logger.info(f"   ASCII only: {pp(ascii_ok)}")


def check_hash() -> None:
    """Checks if the hash from files match the hash in the database (long)."""
    songs = load_db()
    logger.debug("Checking files' hashes")
    for song in tqdm(songs.iter_rows(named=True), total=len(songs)):
        file = ROOT_DIR / Path(song["File_IN"])
        assert file.exists()
        hash = song["Hash_IN"]
        assert get_sha256(file) == hash, f"{file}"


# Test if there are case inconsitancies at all
def check_case(field: str) -> None:
    """Checks for any inconsistency in the database regarding casing and logs any found.

    Args:
        field (str): The field to check, usually Song or Artist.
    """
    songs = load_db()
    cased = set()
    uncased = set()
    for song in songs.rows(named=True):
        cased |= {song[field]}
        uncased |= {song[field].lower()}

    if len(cased) != len(uncased):
        logger.warning("Wrong casing detected")

        # Locates errors
        cased_L = []
        uncased_L = []
        for song in songs.iter_rows(named=True):
            thing = song[field]
            thing_l = thing.lower()
            if thing_l in uncased_L:
                x = uncased_L.index(thing_l)
                if cased_L[x] != thing:
                    logger.warning(f"{cased_L[x]} != {thing}")

            cased_L += [thing]
            uncased_L += [thing.lower()]
    else:
        logger.success(f"No casing inconsistency found in field '{field}'")


def check_mp3gain() -> None:
    """Checks for the mp3gain executable on the path"""
    with open("config.toml", "rb") as file:
        config = toml.load(file)
    if "mp3gain" in config["features"]["activated"]:
        if os.system("mp3gain -q") != 0:
            logger.error("mp3gain activated, but executable not found")
        else:
            logger.success("mp3gain executable found")
    else:
        logger.info("Not checking for mp3gain as option isn't activated")


def all_tests() -> None:
    """Runs all checks defined in this file"""
    format_logger(log_file=LOG_DIR / "checks.log")
    check_ascii()
    check_case("Artist")
    check_case("Song")
    check_hash()
    check_mp3gain()


if __name__ == "__main__":
    all_tests()
