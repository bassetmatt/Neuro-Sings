import polars as pl

from neuro import LOG_DIR, SONGS_CSV
from neuro.song_detect import export_json, extract_all
from neuro.utils import format_logger


def main() -> None:
    format_logger(verbosity=5, log_file=LOG_DIR / "batches.log")
    songs = pl.read_csv(SONGS_CSV)
    out = extract_all(songs)
    export_json(out)


if __name__ == "__main__":
    main()
