
![Static Badge](https://img.shields.io/badge/latest-2025%2007%2009-a)
# Neuro-sing-DB
A project dedicated to creating a database of covers from [Neuro-Sama](https://en.wikipedia.org/wiki/Neuro-sama).
The main goal of this project is to have an easy way to export all covers for offline uses.
The databse aims to provide as much metadata as possible/reasonable for the files to be easily classified by offline music players and provide a nice display thanks to the files images covers.

This project has been realised in Python (3.12) with the use of the [PDM package manager](https://pdm-project.org) for python.

## Downloading songs and new batches
On each new karaoke the database needs to be updated.\
Should only be fetching the diffs from my drive.\
I recommand using a tool like [rclone](https://rclone.org/) or any alternative to just download the diff instead or redownloading everything everytime.

### For someone using this project
Wait for me to do all this work and upload it properly (pls be patient, I try to be fast)
I should have put a Google Drive link somewhere with all files ready to be downloaded. I don't want to put them on github (even the link). I may send them somewhere on Discord.

TODO: Detail drives maybe? And detail how to contact me

### For me (for each batch)
- [x] Get the new song names + order
- [x] Download new drive songs `rclone sync -v gdrive:Neuro songs/drive`
- [x] Generate json `update-json`
- [x] Sanitize json
  - [x] Check Artists name, check coherency with database with queries
  - [x] Set track number
  - [x] ASCII check
- [x] Update the csv database `update-csv`
- [x] Check for errors again
- [x] Run all checks `db-check`
- [x] Generate new thumbnails `thumbnails-generate`
  - [x] If not in the date png, add the new date
- [x] Generate songs `songs-generate`
- [x] Upload the result to the drive `rclone sync -v --copy-links --exclude .directory out gdrive:Neuro-Custom/`
- [x] Profit

*Note*: Create manually the "Song ASCII" or "Artist ASCII" key in JSON if needed, they are fields for a sanitized name for filenames e.g. `"Artist": "DECO*27"`, `"Artist ASCII": "DECO 27"`

*Another Note*: Yes calling this "ASCII" isn't really correct, as "*" for example is an ASCII character. It means sanitized, but it was longer and less clear imo. The goal with this field is firstly to make titles/artists compatible with a filename, and also to ease search for songs e.g. P!NK -> PINK

## What are "duplicates" ?
In the databse there are songs with a "duplicate" flag. What is it?\
It means it's a song that was sung on a given karaoke but has no file corresponding on the drive because it was already sung before.
Since this database sorts covers by albums with one album per karaoke stream with track number for the tracks to be ordered, those missing songs create gaps in numbers.
So even if the audio files are identical, it is possible to generate those "duplicates" using the same files, so the albums will be complete.

## Disclaimers
- I don't have extended knowledge about vocaloids, so if I put a producer or lyricist or singer as the "Artist" it doesn't mean anyting, I just probbaly took the name indicated or did some very basic search and put the first name I found as the artist. If a name is more appropriated for any given song please tell me.
- This lack of knowledge extends to pretty much all the artist that I don't know that well. So if a title or artist isn't correct, please tell me.
- There may be 2-3 exceptions but I don't intend to put all japanese titles in kanas or kanjis.
- You can create flags in the database, but they work by scanning the flags column, not splitting using the separator, so don't name a flag to be a substring of another or the code may misbehave.
- There may be instances of DD-MM-YYYY and YYYY-MM-DD dates format in the code, I may someday go through all the code to be more consistent but I'm too lazy for now.
- I do not own any of the images used for covers, I think I gived proper credit in the README file in the `images/` directory. If credit is missing please notify me.


## Scripts
TODO

## Setup
All this setup is written using a Linux environment, I don't have a Windows environment to test right now.
### tl;dr (Linux)
[Install pipx](https://pipx.pypa.io/stable/installation/)
```bash
pipx install pdm
pdm install
eval $(pdm venv activate)
```

### More details
1. Use your package manager to install pipx or python-pipx, check [here](https://pipx.pypa.io/stable/installation/).
2. Check if you have python installed, pipx should install it anyways.
3. Install pdm via pipx by typing `pipx install pdm`.
4. On the root of the project run `pdm install` to download the packages and create scripts shortcuts.
5. Activate venv for python `eval $(pdm venv activate)` on linux, see [this part of the documentation](https://pdm-project.org/en/latest/usage/venv/#activate-a-virtualenv)
6. Run the scripts you want. [See this part](#scripts)

### Windows
NOT TESTED

1. Install [scoop.sh](https://scoop.sh/)
2. Use scoop to install pipx and python 3.12 (python312 in versions bucket)
3. Install pdm via pipx
4. The lockfile may be linux-specific, if you encounter any problems, you may delete the lockfile.

## Config file
There is a config file in the root directory: `config.toml`. This section will detail its options.

### Output
This section simply defines a folder where all files are exported (in subdirectories).

### Features
As of now, the only feature available is to use [`mp3gain`](https://mp3gain.sourceforge.net). To disable a feature, just remove its name from the "activated" array.
#### mp3gain
> [!WARNING]
> This option increases the song generation time by a lot! Also some options modify the file volume directly. Also mp3gain needs to be installed an available in the PATH.

Its goal is to normalize the gain across all files for a more pleasant experience.\
The more detailed options are described in the file.

### Presets
These are the main parts of the config files. They define groups that are generated and output in a given directory.\
Each preset is defined by the flags to include and to exclude. The preset is defined by all the files that have one of the include flags and has none of the exclude flags.\
You can create as many presets as you want, they can totaly overlap.\
Some examples are commented out.


## Repo organization
- `images/`: Cover images
  - dates: The way I generate dates text is cursed, but it works really well for now, so fixing this is really low priority.
- `data/`
- `Song List.md`
- `Notes.md`
- `Duplicates.md`
- `config.toml`

### Code files
- `checks.py`
- `detection.py`
- `file_tags.py`
- `json_to_csv.py`
- `polars_utils.py`
- `run.py`
- `thumbnails.py`
- `utils.py`

## License
<sup>
Licensed under either of <a href="LICENSE-APACHE">Apache License, Version
2.0</a> or <a href="LICENSE-MIT">MIT license</a> at your option.
</sup>

<br>

<sub>
Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion by you, as defined in the Apache-2.0 license, shall be
dual licensed as above, without any additional terms or conditions.
</sub>
