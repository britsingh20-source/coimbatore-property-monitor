import json
import math
import struct
import wave
from pathlib import Path

from PIL import Image


def _portrait_bg(source: Path, target: Path) -> None:
    img = Image.open(source).convert('RGB')
    canvas = (1080, 1920)
    scale = max(canvas[0] / img.width, canvas[1] / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
    left = max(0, (img.width - canvas[0]) // 2)
    top = max(0, (img.height - canvas[1]) // 2)
    img = img.crop((left, top, left + canvas[0], top + canvas[1]))
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target, 'JPEG', quality=92)


def _bgm(target: Path, seconds: int = 45, rate: int = 44100) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), 'w') as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        for i in range(seconds * rate):
            t = i / rate
            beat = (t * 1.8) % 1.0
            kick = math.exp(-beat * 18.0) * math.sin(2 * math.pi * 56 * t)
            pad = 0.38 * math.sin(2 * math.pi * 110 * t) + 0.22 * math.sin(2 * math.pi * 164.81 * t)
            shimmer = 0.12 * math.sin(2 * math.pi * 329.63 * t)
            amp = max(-1.0, min(1.0, 0.22 * kick + 0.12 * pad + 0.05 * shimmer))
            sample = int(amp * 32767)
            wav.writeframesraw(struct.pack('<hh', sample, sample))


def _sfx(target: Path, kind: str, rate: int = 44100) -> None:
    durations = {'aircraft': 1.35, 'whoosh': 1.05, 'impact': 0.9}
    seconds = durations[kind]
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), 'w') as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        for i in range(int(seconds * rate)):
            t = i / rate
            if kind == 'aircraft':
                env = math.sin(min(1.0, t / .18) * math.pi / 2) * max(0.0, 1 - t / seconds) ** .35
                signal = .42 * math.sin(2 * math.pi * 62 * t) + .22 * math.sin(2 * math.pi * 124 * t)
                signal += .10 * math.sin(2 * math.pi * (210 + 45 * t) * t)
            elif kind == 'whoosh':
                env = math.sin(math.pi * min(1.0, t / seconds)) ** 1.5
                signal = .46 * math.sin(2 * math.pi * (180 + 920 * t / seconds) * t)
                signal += .18 * math.sin(2 * math.pi * (75 + 240 * t / seconds) * t)
            else:
                env = math.exp(-t * 8.5)
                signal = .72 * math.sin(2 * math.pi * (78 - 42 * t) * t)
                signal += .32 * math.sin(2 * math.pi * 42 * t)
            amp = max(-1.0, min(1.0, env * signal))
            sample = int(amp * 32767)
            wav.writeframesraw(struct.pack('<hh', sample, sample))


def prepare(video_id: str) -> None:
    ai_root = Path('assets/ai_broll') / video_id
    public = Path('professional_video/public/render') / video_id
    public.mkdir(parents=True, exist_ok=True)

    prepared = []
    for folder in sorted(path for path in ai_root.iterdir() if path.is_dir()):
        candidates = sorted(folder.glob('*representative.jpg')) + sorted(folder.glob('*.jpg'))
        if not candidates:
            continue
        scene = folder.name
        _portrait_bg(candidates[0], public / f'layer-{scene}-bg.jpg')
        prepared.append(scene)

    if not prepared:
        raise RuntimeError(f'No AI scene images found for {video_id} in {ai_root}')

    props_path = Path('data/remotion_props') / f'{video_id}.json'
    props = json.loads(props_path.read_text(encoding='utf-8'))
    key_for = {
        'price': 'exterior',
        'facing': 'exterior',
        'builtUp': 'living',
        'verify': 'location',
        'road': 'location',
    }
    preferred_fallbacks = {
        'land': ('location', 'exterior', 'living'),
        'location': ('exterior', 'land', 'living'),
        'living': ('exterior', 'location', 'bedroom'),
        'exterior': ('location', 'living', 'land'),
        'kitchen': ('living', 'exterior', 'bedroom'),
        'bedroom': ('living', 'exterior', 'kitchen'),
    }
    prepared_set = set(prepared)
    required = {key_for.get(scene, scene) for scene in props.get('sceneOrder', [])}
    required.discard('cta')
    first_scene = prepared[0]
    for scene in sorted(required):
        target = public / f'layer-{scene}-bg.jpg'
        if target.exists():
            continue
        fallback = next(
            (candidate for candidate in preferred_fallbacks.get(scene, ()) if candidate in prepared_set),
            first_scene,
        )
        source = public / f'layer-{fallback}-bg.jpg'
        target.write_bytes(source.read_bytes())
        prepared.append(f'{scene}<-{fallback}')

    _bgm(public / 'bgm.wav')
    _sfx(public / 'sfx-aircraft.wav', 'aircraft')
    _sfx(public / 'sfx-whoosh.wav', 'whoosh')
    _sfx(public / 'sfx-impact.wav', 'impact')
    print(f'Full-frame AI image assets prepared for {video_id}: {", ".join(prepared)}')


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        raise SystemExit('usage: prepare_layered_assets.py VIDEO_ID')
    prepare(sys.argv[1])
