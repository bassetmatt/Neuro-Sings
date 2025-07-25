import os
import tomllib as toml
from pathlib import Path
from time import time

from loguru import logger

from neuro import DRIVE_DIR, LOG_DIR
from neuro.detection import export_json, extract_all
from neuro.file_tags import CustomSong, DriveSong
from neuro.polars_utils import Preset, load_dates
from neuro.utils import MP3GainMode, MP3ModeTuple, format_logger, time_format

DateDict = dict[str, dict[str, str]]


def new_batch_detection() -> None:
    """Re-runs the song detection based on regex. Adds songs that aren't already in\
        the database in a JSON file for them to be reviewed.
    """
    format_logger(verbosity=5, log_file=LOG_DIR / "batches.log")
    # These 3 lines could be ine call, but it would just make the code less clear
    out = extract_all()  # Exctacts data
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

        # Differenciate songs from drive and custom songs. Mainly because they aren't
        # from the same contexts (streams vs collabs mainly). Their format is different.
        # Subathon mixes are put in custom, so drive songs are only mp3
        if Path(song_dict["File_IN"]).is_relative_to(DRIVE_DIR):
            date_dict = dates_dict.get(song_dict["Date"], {})
            s = DriveSong(song_dict, date_dict)
        else:
            s = CustomSong(song_dict)

        created = s.create_out_file(create=False, out_dir=preset.path)
        if created:
            s.apply_tags()
        logger.debug(
            f"[GEN] [{preset.name}] [{i + 1:3d}/{N_SONGS}] {'Generated' if created else 'Skipped'} {song_dict['Song']}"
        )
    run_mp3gain(preset)
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

    mp3gain = parse_mp3gain(config)

    # Start time
    t = time()

    # Easier data format to deal with
    dates_dict: DateDict = {k["Date"]: k for k in load_dates().iter_rows(named=True)}

    for preset in config["Presets"]:
        logger.info(f"[GEN] Generating preset '{preset['name']}'")
        preset_obj = Preset(preset, mp3gain, OUT_ROOT)
        generate_from_preset(preset_obj, dates_dict)

    logger.success(f"[GEN] Generated all presets in {time_format(time() - t)} !")


def parse_mp3gain(config: dict) -> MP3ModeTuple:
    """Gets the mp3gain global config from the config file.

    Args:
        config (dict): Dictionnary representing the whole configuration file.

    Raises:
        ValueError: If the configuration has unexpected.

    Returns:
        MP3ModeTuple: Tuple with the mode (per-preset or on-all) and the type \
            of gain modification (tag or gain on file).
    """
    mp3gain: MP3ModeTuple
    if "mp3gain" in config["features"]["activated"]:
        mp3_config = config["features"]["mp3gain"]
        match mp3_config["mode"]:
            case "per-preset":
                mode = MP3GainMode.PER_PRESET
            case "on-all":
                mode = MP3GainMode.ON_ALL
            case x:
                logger.error(f"Unknown mp3gain mode '{x}'")
                raise ValueError(f"Unknown mp3gain mode '{x}'")
        match mp3_config["type"]:
            case "gain":
                type = MP3GainMode.GAIN
            case "tag":
                type = MP3GainMode.TAG
        mp3gain = (mode, type)
    else:
        mp3gain = (MP3GainMode.OFF, MP3GainMode.OFF)

    return mp3gain


def run_mp3gain(preset: Preset) -> None:
    """Runs gain equalization for a given preset.

    Args:
        preset (Preset): The preset to run mp3gain on, contains all relevant information.
    """
    if preset.mp3gain is MP3GainMode.OFF:
        return
    logger.info(f"[GEN] Running mp3gain for preset {preset.name}")
    options = ""
    if preset.mp3gain is MP3GainMode.GAIN:
        options = "-r -k"
    OUT_LOG = Path(LOG_DIR / "mpgain.log")
    os.system(f"mp3gain {options} {preset.path}/*.mp3 > {OUT_LOG}")


def mp3gain_standalone() -> None:
    """Runs mp3gain on all presets without creating the files"""
    format_logger(log_file=LOG_DIR / "generation.log")
    logger.info("[MP3G] Starting generation batch")

    # Loading config file
    with open("config.toml", "rb") as file:
        config = toml.load(file)

    cfg_out = config["output"]
    if cfg_out["use-root"]:
        OUT_ROOT = Path(cfg_out["out-root"])
    else:
        OUT_ROOT = None

    mp3gain = parse_mp3gain(config)

    for preset in config["Presets"]:
        logger.info(f"[MP3G] Generating preset '{preset['name']}'")
        preset_obj = Preset(preset, mp3gain, OUT_ROOT)
        run_mp3gain(preset_obj)


if __name__ == "__main__":
    generate_songs()
