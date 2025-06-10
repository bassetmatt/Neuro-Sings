from itertools import chain
from pathlib import Path
from string import ascii_letters, digits

import polars as pl
from loguru import logger
from tqdm import tqdm

from neuro import LOG_DIR, ROOT, SONGS_CSV
from neuro.utils import format_logger, get_sha256


def check_ascii() -> None:
    ALPHANUM = set(ascii_letters + digits)

    songs = pl.read_csv(SONGS_CSV)
    no_ascii = songs.get_column("Song").to_list() + songs.get_column("Artist").to_list()
    ascii = (
        songs.get_column("Song_ASCII").to_list()
        + songs.get_column("Artist_ASCII").to_list()
    )

    no_ascii_ok = set(chain.from_iterable(no_ascii)) - ALPHANUM
    ascii_ok = set(chain.from_iterable(ascii)) - ALPHANUM

    def pp(s: set) -> str:
        return ", ".join(map(repr, sorted(s, key=ord)))

    logger.info(f"No ASCII only: {pp(no_ascii_ok - ascii_ok)}")
    logger.info(f"   ASCII only: {pp(ascii_ok)}")


def check_hash() -> None:
    songs = pl.read_csv(SONGS_CSV)
    for song in tqdm(songs.iter_rows(named=True)):
        file = ROOT / Path(song["File_IN"])  # type: ignore
        assert file.exists()
        hash = song["Hash_IN"]  # type: ignore
        assert get_sha256(file) == hash, f"{file}"


# Test if there are case inconsitancies at all
def check_case(field: str) -> None:
    songs = pl.read_csv(SONGS_CSV)
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


def all_tests() -> None:
    check_ascii()
    check_case("Artist")
    check_case("Song")
    check_hash()


if __name__ == "__main__":
    format_logger(log_file=LOG_DIR / "checks.log")
    all_tests()
