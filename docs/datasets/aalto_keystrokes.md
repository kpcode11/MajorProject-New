# Dataset card: 136M Keystrokes (Aalto)

- **Source:** Aalto University, `136M Keystrokes`; local folder
  `Keystrokes`.
- **Access date:** 2026-10-14.
- **Citation:** Vivek Dhakal, Anna Maria Feit, Per Ola Kristensson, Antti
  Oulasvirta, “Observations on Typing from 136 Million Keystrokes,” CHI 2018,
  DOI [10.1145/3173574.3174220](https://doi.org/10.1145/3173574.3174220).
- **Licence / terms:** The supplied `readme.txt` permits non-commercial use in
  research or projects with attribution. Redistribution and any commercial use
  require separate review of the source terms.

## Local inventory

The configured path exists and is an extracted directory, not a ZIP archive:
`C:\Users\KESHAV\Downloads\datasets\Keystrokes`.

The corrected inventory report is
`docs/datasets/inventory_aalto_keystrokes.txt`. It records:

- 168,593 participant keystroke files;
- one `metadata_participants.txt` file and one `readme.txt`;
- 168,595 `.txt` files total;
- approximately 18.85 GB on disk, including approximately 21 MB of
  participant metadata;
- the dataset README's description of more than 168,000 users typing 15
  sentences each.

The inventory walks directory entries to count files but caps printed tree
output and only reads small text samples. It does not load the dataset into
memory.

## Observed format

Each participant file is named `<participant_id>_keystrokes.txt` and has
tab-separated rows with:

`PARTICIPANT_ID`, `TEST_SECTION_ID`, `SENTENCE`, `USER_INPUT`,
`KEYSTROKE_ID`, `PRESS_TIME`, `RELEASE_TIME`, `LETTER`, and `KEYCODE`.

`PRESS_TIME` and `RELEASE_TIME` are Unix timestamps in milliseconds. Each
sentence/test section is a natural typing window. The README states that some
keystrokes are not logged or displayed correctly and that the JavaScript
keycode is used in those cases.

`metadata_participants.txt` contains demographics and aggregate typing
statistics. It is not required for the text-agnostic keyboard feature
pipeline, and demographic fields must not be used as model inputs.

## Access and processing decision

The local copy is already extracted and is about 19 GB, so the loader must
stream one participant file at a time. It must support a seeded participant
sample, with a default maximum of 1,000 participants, and must never
concatenate all files or load the metadata table into memory.

Each typed sentence with at least 10 key events will become a canonical
keyboard window. The loader will convert timestamps to `down_ms` and `up_ms`,
map `LETTER`/`KEYCODE` to a coarse `key_class` in memory, and immediately
drop key identities and typed content. Produced shards must contain timing and
class information only.

The participant identifier may be retained as a split group for leakage-safe
evaluation, but raw sentence text, `USER_INPUT`, `LETTER`, `KEYCODE`, and
`KEYSTROKE_ID` must not be written to canonical keyboard shards. The
privacy-scan task will enforce this rule.

## Known limitations

- This is a typing-test dataset with prescribed sentences, not ordinary
  browsing behaviour.
- No second human keyboard source is currently available in the configured
  dataset root, so keyboard false-positive estimates rely on Aalto alone.
- It contains human typing only; bot labels must come from the documented
  synthetic generators, not from the source data.
- The source README reports logging/display problems for some keystrokes.
- Demographic metadata is sensitive and is excluded from feature generation.
- The local extracted copy is large. Dataset processing must remain
  participant-streaming and respect the repository's disk and memory limits.
