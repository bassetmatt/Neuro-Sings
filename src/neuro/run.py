import os
import tomllib as toml
from pathlib import Path
from time import time

from loguru import logger

from neuro import DRIVE_DIR, LOG_DIR
from neuro.detection import export_json, extract_all
from neuro.file_tags import CustomSong, DriveSong
from neuro.polars_utils import Preset, load_dates, load_db
from neuro.utils import format_logger, time_format

DateDict = dict[str, dict[str, str]]


def new_batch_detection() -> None:
    """Re-runs the song detection based on regex. Adds songs that aren't already in\
        the database in a JSON file for them to be reviewed.
    """
    format_logger(verbosity=5, log_file=LOG_DIR / "batches.log")
    # These 3 lines could be ine call, but it would just make the code less clear
    songs = load_db()
    out = extract_all(songs)  # Exctacts data
    export_json(out)  # Writing into JSON


def generate_from_preset(preset: Preset, dates_dict: DateDict) -> None:
    """Generates all songs from a preset, filters songs that respect filters.

    Args:
        preset (Preset): Preset configuration.
        dates_dict (DateDict): Date dict to pass to drive song constructor.
    """
    os.makedirs(preset.path, exist_ok=True)

    t = time()
    songs_filtered = preset.get_filtered_df()
    for i, song_dict in enumerate(songs_filtered.iter_rows(named=True)):
        N_SONGS = len(songs_filtered)
        logger.debug(f"[GEN] [{i + 1:3d}/{N_SONGS}] Generating {song_dict['Song']}")

        # Differenciate songs from drive and custom songs. Mainly because they aren't
        # from the same contexts (streams vs collabs mainly). Their format is different.
        # Subathon mixes are put in custom, so drive songs are only mp3
        if Path(song_dict["File_IN"]).is_relative_to(DRIVE_DIR):
            date_dict = dates_dict.get(song_dict["Date"], {})
            s = DriveSong(song_dict, date_dict)
        else:
            s = CustomSong(song_dict)

        s.create_out_file(create=True, out_dir=preset.path)
        s.apply_tags()
    logger.success(f"[GEN] Done converting {N_SONGS} songs in {time_format(time() - t)} !")


def generate_songs() -> None:
    """Generates all songs files. For each files it first copies the files into\
    its destination, then edits the metadata of the destination file. This is\
    just to avoid tempering the original files.\
    Generates songs in preset groups.
    """

    format_logger(log_file=LOG_DIR / "generation.log")
    logger.info("[GEN] Starting generation batch")

    # Loading config file
    with open("config.toml", "rb") as file:
        config = toml.load(file)

    cfg_out = config["output"]
    if cfg_out["use-root"]:
        OUT_ROOT = Path(cfg_out["out-root"])
    else:
        OUT_ROOT = None

    # Start time
    t = time()

    # Easier data format to deal with
    dates_dict: DateDict = {k["Date"]: k for k in load_dates().iter_rows(named=True)}

    for preset in config["Presets"]:
        logger.info(f"[GEN] Generating preset '{preset['name']}'")
        preset_obj = Preset(preset, OUT_ROOT)
        generate_from_preset(preset_obj, dates_dict)

    logger.success(f"[GEN] Generated all presets in {time_format(time() - t)} !")


if __name__ == "__main__":
    generate_songs()
