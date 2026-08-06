# Owned property and locality photographs

Create one folder named with the approved YouTube video ID and add at least three
ordered images, for example `01-street.jpg`, `02-exterior.jpg`, `03-living.jpg`.

Use only photographs you own or have explicit permission to reuse. Do not copy
competitor YouTube frames or thumbnails.

## R2 alternative

Instead of committing real property photos into git, you can upload them to the
R2 bucket under `own-footage/<video-id>/` (same filename convention as above).
Every render pulls `own-footage/` down into this folder before rendering (see
`r2_storage.sync_own_footage_down()`), so either approach works — whichever
files are present locally at render time (from git or from R2) get used.
