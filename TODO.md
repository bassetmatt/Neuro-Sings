# TODO
## High-prio
- [x] Write the code that actually runs mp3gain. 2 Options
  - [x] Write gain value: `mp3gain <file>`
  - [x] Force gain change: `mp3gain -r -k <file>`

## Mid-prio
- [x] Write documentation
  - [x] Code
  - [x] README

- [ ] Preset prefix/suffix (pass preset to Song)
- [ ] More complex flag selection with AND/OR
  - [ ] Maybe at first just an option in the preset to tell include-type = "AND" | "OR" (same for exclude). Write stack_and function and check for option in preset.
  - [ ] Or have a "complex mode" flag, tell if it's AND->OR or OR->AND. And put conditions in arrays of arrays and apply operation 1 between level1 arrays...

## To do before release
- [x] Have my drive as custom source -> Maybe don't put the link on github
  - [x] Also as source of songs.csv

- [x] Create a v3 tag to be able to separate v3 duplicates songs.
- [x] Bundle all CLI things in a python file to ease the command typing
  - [x] Write a function to sync the databases between the two formats. (Load the CSV and re-write the DB file with its content)
