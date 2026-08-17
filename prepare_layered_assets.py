import math
import struct
import wave
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


def _portrait_bg(source: Path, target: Path) -> None:
    img = Image.open(source).convert('RGB')
    canvas = (1080, 1920)
    scale = max(canvas[0]/img.width, canvas[1]/img.height)
    img = img.resize((int(img.width*scale), int(img.height*scale)), Image.Resampling.LANCZOS)
    left = max(0, (img.width-canvas[0])//2)
    top = max(0, (img.height-canvas[1])//2)
    img = img.crop((left, top, left+canvas[0], top+canvas[1]))
    img = ImageEnhance.Brightness(img).enhance(0.72).filter(ImageFilter.GaussianBlur(2.2))
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target, 'JPEG', quality=92)


def _foreground(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        from rembg import new_session, remove
        session = new_session('u2netp')
        result = remove(source.read_bytes(), session=session)
        target.write_bytes(result)
        return
    except Exception as exc:
        print(f'Foreground segmentation fallback for {source}: {exc}')
    # Always create a valid transparent PNG so Remotion never fails.
    Image.new('RGBA', (1080, 1920), (0, 0, 0, 0)).save(target)


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
            frame = struct.pack('<hh', sample, sample)
            wav.writeframesraw(frame)


def prepare(video_id: str) -> None:
    ai_root = Path('assets/ai_broll') / video_id
    public = Path('professional_video/public/render') / video_id
    public.mkdir(parents=True, exist_ok=True)
    for scene in ('exterior', 'location', 'living', 'kitchen', 'bedroom'):
        folder = ai_root / scene
        candidates = sorted(folder.glob('*representative.jpg')) + sorted(folder.glob('*.jpg'))
        if not candidates:
            continue
        source = candidates[0]
        _portrait_bg(source, public / f'layer-{scene}-bg.jpg')
        if scene == 'exterior':
            _foreground(source, public / 'layer-exterior-fg.png')
    _bgm(public / 'bgm.wav')
    print(f'Layered V2 assets prepared for {video_id}')


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        raise SystemExit('usage: prepare_layered_assets.py VIDEO_ID')
    prepare(sys.argv[1])
