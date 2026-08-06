# Own-stock B-roll library

Drop your own licensed/owned photos and video clips in the matching folder below.
`prepare_free_assets.py` checks this library **first**, before ever calling
Pixabay/Pexels/Commons. If a scene has enough files here, no external API call
is made for it at all — faster, and no risk of Pixabay returning an unrelated
image or clip.

| Folder        | Used for                                              |
|----------------|--------------------------------------------------------|
| `drone_views/` | Wide aerial / neighbourhood establishing shots (scene: `location`) |
| `roads/`       | Approach road, street, tar-road footage (scene: `road`) |
| `plots/`       | Vacant land / plot boundary shots (scene: `land`, for plot listings) |
| `exteriors/`   | House/villa front elevation, gate, parking (scene: `exterior`) |
| `interiors/`   | Living room, kitchen, bedroom walkthroughs (scene: `interior`) |

## Adding files

- **Photos**: `.jpg`, `.jpeg`, `.png`, or `.webp`.
- **Videos**: `.mp4`, `.mov`, `.webm`, or `.m4v`.
- Filenames don't matter — just drop the file in the right folder.
- Only use media you own or have explicit license/permission to reuse.

## Attribution (optional but recommended)

Next to any file, you can add a same-name `.json` sidecar for attribution/licensing
metadata. For example, alongside `exteriors/modern-villa-01.mp4`, add
`exteriors/modern-villa-01.mp4.json`:

```json
{
  "provider": "Your name or studio",
  "license": "Owned / licensed for commercial use",
  "source_url": ""
}
```

If you skip the sidecar, files are attributed as `Own stock library` /
`Owner supplied stock` automatically.

## How selection works

- For every property, the pipeline figures out which scenes it needs (a plot
  listing needs `location`, `road`, `land`; a house needs `location`, `road`,
  `exterior`, `interior`) and pulls a random file per scene from the matching
  folder here first.
- Only if this library doesn't have enough for a given property does the
  pipeline fall back to Pixabay → Wikimedia Commons → Pexels, in that order.
- Anything downloaded from those external sources during a run that passes
  the content filters gets **automatically copied back into this library**,
  tagged by scene — so the library grows over time and future runs depend on
  external APIs less and less. You don't need to do anything for that part;
  it happens on its own.

## Content rules

The same religious-imagery and off-topic filters that apply to Pixabay/Commons
results (see `BLOCKED_VISUAL_TERMS` / `SCENE_BLOCKED_TERMS` in
`media_sources.py`) are matched against file *names* for library files too, so
name your files descriptively and avoid blocked terms in the filename.
