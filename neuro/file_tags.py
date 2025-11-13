"""Applies all metadata tags on music files"""

import os
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional

from loguru import logger
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC, TALB, TBPM, TDRC, TDRL, TIT2, TKEY, TPE1, TPE2, TRCK, TSO2, TYER, TextFrame
from PIL import Image

from neuro import IMAGES_COVERS_DIR, IMAGES_CUSTOM_DIR, LOG_DIR, ROOT_DIR
from neuro.detection import SongEntry
from neuro.utils import file_check, format_logger


class Song:
    """Represents a Song's Metadata. Abstract class, used for common code between drive/custom songs."""

    @dataclass
    class Flags:
        v1: bool
        """Neuro v1 voice"""
        v2: bool
        """Neuro v2 voice"""
        v3: bool
        """Neuro/Evil v3 voice"""
        neuro: bool
        evil: bool
        duet: bool
        duplicate: bool
        """Duplicate song, file doesn't exist in drive, but song was sung that day"""
        as_drive: bool
        """Use the same naming convention as drive files for filename"""
        as_custom: bool
        """Use the same naming convention as custom files for filename"""
        arg: bool
        """Songs from the ARG channel"""

    def init_flags(self, flags: Optional[str]) -> None:
        """Detects song's flags by searching substrings in the flags column.\
            Stores the result in `self.flags`.

        Args:
            flags (Optional[str]): Content of the flags column
        """

        # flag is false if song has no flags of if it has flags but not the selected one
        def flag_check(flag: str, flag_field: Optional[str]) -> bool:
            if flag_field is None:
                return False
            return flag in flag_field

        # Strange code, but just expands into `"v1": flags_check("v1", flags)`...
        # for all flags. It uses the fact that Flags fields are exactly the same
        # strings as the flags
        self.flags = self.Flags(**{flag: flag_check(flag, flags) for flag in self.Flags.__dataclass_fields__.keys()})

    def __init__(self, song_dict: SongEntry, karaoke_dict: dict = {}) -> None:
        # Lots of asserts, mainly for type checking, but also detects irregular entries in database
        assert song_dict["Song"] is not None
        assert song_dict["Song_ASCII"] is not None
        self.title: str = song_dict["Song"]
        self.title_ascii: str = song_dict["Song_ASCII"]

        assert song_dict["Artist"] is not None
        assert song_dict["Artist_ASCII"] is not None
        self.artist: str = song_dict["Artist"]
        self.artist_ascii: str = song_dict["Artist_ASCII"]

        assert song_dict["File_IN"] is not None
        self.file: Path = ROOT_DIR / Path(song_dict["File_IN"])
        file_check(self.file)

        assert song_dict["Album_ID"] is not None
        self.track_n: str = song_dict["Album_ID"]

        assert song_dict["Date"] is not None
        self.date: str = song_dict["Date"]

        assert song_dict["Album"] is not None
        self.album: str = song_dict["Album"]

        self.key = song_dict["Key"]  # Can be None
        self.tempo = song_dict["Tempo (1/4 beat)"]  # Can be None

        self.image: Optional[str] = song_dict["Image"]
        self.outfile: Optional[Path] = None

        self.d: SongEntry = song_dict
        self.k: SongEntry = karaoke_dict

        self.init_flags(song_dict["Flags"])

    def create_out_file(self, *, out_dir: Path, create: bool = True) -> bool:
        """Virtual method"""
        raise NotImplementedError

    def id3_pic(self, cover: Path) -> APIC:
        """Creates a Cover picture from a given image for files using ID3 tags.

        Args:
            cover (Path): Path to the image used for cover. File must exist (not checked in function).

        Returns:
            APIC: Mutagen APIC type picture to be stored in ID3 tags.
        """
        img = APIC(
            encoding=3,  # 3 is for utf-8
            mime="image/jpeg",  # image/jpeg or image/png
            type=18,  # 3 is for the cover image
            desc="Cover",
            data=open(cover, "rb").read(),
        )
        return img

    def get_id3_frames(self) -> list[TextFrame]:
        """Gets tags specific to ID3 tags.

        Returns:
            _ (list[TextFrame]): Dictionary with Album artist.
        """
        additional = [
            # Title
            TIT2(text=self.title, encoding=3),
            # Artist
            TPE1(text=self.artist, encoding=3),
            # Album
            TALB(text=self.album, encoding=3),
            # Year-Month-Day | Using all frames for different software compatibility
            TDRL(text=self.date, encoding=3),
            TYER(text=self.date[:4], encoding=3),
            TDRC(text=self.date, encoding=3),
            # Track number
            TRCK(text=f"{self.track_n}", encoding=3),
        ]

        if self.key is not None:
            # Initial key tag
            additional.append(TKEY(text=self.key, encoding=3))
        if self.tempo is not None:
            # Tempo tag
            additional.append(TBPM(text=str(self.tempo), encoding=3))
        return additional

    def get_vorbis_frames(self) -> dict[str, str]:
        """Gets tags specific to Vorbis comments.

        Returns:
            dict[str, str]: Dictionary with Album artist.
        """
        additional = {
            "ALBUM": self.album,
            "ARTIST": self.artist,
            "DATE": self.date,
            "TITLE": self.title,
            "TRACKNUMBER": f"{self.track_n}",
            "PERFORMER": "Neuro-Sama/Evil Neuro",
        }
        return additional

    @property
    def album_artist(self) -> str:
        """Album artist for karaokes. Defined it as a property for consistency with other attributes.

        Returns:
            str: The artist. Can be Neuro-Sama, Evil Neuro, or Neuro [v1]/[v2].
        """
        # They are mutually exclusive so it's okay
        if self.album in ["Extra", "Originals", "Subathons"]:
            return "Neuro-Sama/Evil Neuro"
        if self.flags.v1:
            return "Neuro [v1]"
        if self.flags.v2:
            return "Neuro [v2]"
        if self.flags.evil:
            return "Evil Neuro"
        if self.flags.arg:
            return "Study-sama"
        return "Neuro-Sama"

    @property
    def name_tag(self) -> str:
        """Name tag to be put in brackets in the file name. Defined it as a property for consistency with\
            other attributes.

        Raises:
            ValueError: When a song doesn't have at least neuro or evil tag.

        Returns:
            str: The tag: Neuro, Evil, Duet, Neuro + Vedal, Neuro v1/v2.
        """
        if self.flags.v1:
            return "Neuro v1"
        if self.flags.v2:
            return "Neuro v2"
        if self.title == "Chinatown Blues":
            return "Neuro + Vedal"
        # A song can have both evil/neuro and duet tags, but the duet tag is prioritized
        if self.flags.duet:
            return "Duet"
        if self.flags.evil:
            return "Evil"
        if self.flags.neuro:
            return "Neuro"
        # A song must have the Neuro or Evil tag, if it has neither, raise an Error
        logger.error(f"Song '{self.file}' has no flags to define its tag!")
        raise ValueError(f"Song '{self.file}' has no flags to define its tag!")

    def file_name(self, custom: bool) -> str:
        """Returns the output filename using song properties.

        Args:
            custom (bool): Use the drive or custom format. **Warning**: A custom song can use the drive\
                format if it has the `as_drive` flag, same for a drive song with `as_custom`.

        Returns:
            str: The filename without type extension.
        """
        if custom:
            return f"{self.artist_ascii} - {self.title_ascii}"
        else:
            return f"{self.artist_ascii} - {self.title_ascii} [{self.name_tag}] [{self.date}]"


class DriveSong(Song):
    """Metadata for a song from the drive."""

    def __init__(self, song_dict: dict, karaoke_dict: dict) -> None:
        super().__init__(song_dict, karaoke_dict)

    def create_out_file(self, *, out_dir: Path = Path("out"), create: bool = True) -> bool:
        """Creates the output file on the filesystem by copying the original. The metadata are written later.

        Args:
            out_dir (Path, optional): Output directory. Should be defined in the config file. \
                Defaults to Path("out").
            create (bool, optional): Force to create a copy of the file even if a file already exists. \
                Defaults to True.

        Returns:
            bool: True if a file was created.
        """
        # Ensures the output directory exists
        os.makedirs(ROOT_DIR / out_dir, exist_ok=True)
        # If the song is flagged as custom, use the custom format
        name = self.file_name(self.flags.as_custom)
        self.outfile = ROOT_DIR / out_dir / f"{name}.mp3"

        if create or (not self.outfile.exists()):
            shutil.copy2(self.file, self.outfile)
            return True
        return False

    def apply_tags(self) -> None:
        """Applies ID3 tags on the file. First uses EasyID3 for text tags. Then ID3 to write the cover
        picture to the file.
        """
        # Text tags
        id3 = ID3(self.outfile)

        common_props = self.get_id3_frames()
        for frame in common_props:
            id3.add(frame)

        id3.add(TPE2(encoding=3, text=self.album_artist))
        id3.add(TSO2(encoding=3, text=self.album_artist))

        # Cover Image
        if self.image is None:
            if self.flags.duet:
                cover = IMAGES_COVERS_DIR / Path(f"duet-{self.date}.jpg")
            else:
                cover = IMAGES_COVERS_DIR / Path(f"{self.date}.jpg")
        else:
            cover = IMAGES_CUSTOM_DIR / f"{self.image}.jpg"

        file_check(cover)
        id3.delall("APIC")
        id3.add(self.id3_pic(cover))
        id3.save()


class CustomSong(Song):
    """Metadata for a song added manually (not from the drive)."""

    def __init__(self, song_dict: dict, karaoke_dict: dict = {}) -> None:
        super().__init__(song_dict, karaoke_dict)

    def create_out_file(self, *, out_dir: Path, create: bool = True) -> bool:
        """Creates the output file on the filesystem by copying the original. The metadata are written later.

        Args:
            out_dir (Path, optional): Output directory. Should be defined in the config file. \
                Defaults to Path("out").
            create (bool, optional): Force to create a copy of the file even if a file already exists. \
                Defaults to True.
        Returns:
            bool: True if a file was created.
        """
        file = self.file
        ext = file.suffix

        name = self.file_name(not self.flags.as_drive)
        self.outfile = ROOT_DIR / out_dir / f"{name}{ext}"

        if create or (not self.outfile.exists()):
            shutil.copy2(file, self.outfile)
            return True
        return False

    def apply_tags(self) -> None:
        """Custom Song version of the tag management. Here it needs to check the file's format first\
            to apply the right type of tag.

        Raises:
            ValueError: If the file isn't a .mp3 or .flac file.
        """
        ext = self.file.suffix
        if self.image is None:
            logger.error(f"Image can't be None for custom song {self.file}")

        self.cover = IMAGES_CUSTOM_DIR / f"{self.image}.jpg"
        file_check(self.cover)

        match ext:
            case ".mp3":
                self.apply_id3()
            case ".flac":
                self.apply_tags_vorbis()
            case _:
                logger.error(f"Unimplemented file suffix for {self.file}")
                raise ValueError(f"Unimplemented file suffix for {self.file}")

    def apply_id3(self) -> None:
        """ID3 version of the metadata management. Similar to the one for Drive Songs."""
        id3 = ID3(self.outfile)

        for frame in self.get_id3_frames():
            id3.add(frame)

        if self.flags.as_drive or self.flags.arg:
            album_artist = self.album_artist
        else:
            album_artist = "Neuro-Sama/Evil Neuro"

        id3.add(TPE2(encoding=3, text=album_artist))
        id3.add(TSO2(encoding=3, text=album_artist))

        # Cover Image
        id3.delall("APIC")
        id3.add(self.id3_pic(self.cover))
        id3.save()

    def get_flac_pic(self) -> Picture:
        """Generates a picture for a FLAC file's cover. This very particular method works, so\
            I won't modify it without a valid reason.

        Returns:
            Picture: The encoded cover picture.
        """
        img = Image.open(self.cover)
        if img.mode == "RGBA":
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(
            buffer,
            format="JPEG",
            quality=85,
            optimize=True,
            progressive=False,
        )
        image_file = buffer.getvalue()
        img.close()

        image = Picture()
        image.type = 3
        image.mime = "image/jpeg"
        image.desc = "Cover"
        image.data = image_file
        return image

    def apply_tags_vorbis(self) -> None:
        """FLAC specific tag handling (for 2 files atm...).

        Raises:
            ValueError: If the file has no tag header present.
        """
        # Based on https://exiftool.org/TagNames/Vorbis.html tags descriptions
        file = FLAC(self.outfile)
        if file.tags is None:
            logger.error(f"File {self.file} has no tags header.")
            raise ValueError

        common = self.get_vorbis_frames()
        for k, v in common.items():
            # Uppercase totaly unneeded I think
            file.tags[k.upper()] = v  # type: ignore

        # Cover
        image = self.get_flac_pic()

        file.clear_pictures()
        file.add_picture(image)
        file.save()


if __name__ == "__main__":
    format_logger(log_file=LOG_DIR / "tags.log")
