"""python marketing/video/thumb.py

Renders thumb.html's four scenes with headless Edge (scenes.mjs) and joins them, with short
crossfades, into out/ph-thumbnail.gif (240x240, loops) for Product Hunt, plus
out/youtube-thumbnail.jpg (1280x720) from the demo's title card.
"""
import shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image
import imageio_ffmpeg

HERE = Path(__file__).parent
OUT = HERE / "out"
FF = imageio_ffmpeg.get_ffmpeg_exe()
HOLD, FADE, FPS = 1.3, 0.3, 20

tmp = Path(tempfile.mkdtemp(prefix="thumb-"))
try:
    subprocess.run(["node", str(HERE / "scenes.mjs"), str(HERE / "thumb.html"), "4", str(tmp), "480"], check=True)
    scenes = [Image.open(tmp / f"s{f}.png").convert("RGB").resize((240, 240), Image.LANCZOS) for f in range(4)]
    n = 0
    for i, a in enumerate(scenes):
        b = scenes[(i + 1) % len(scenes)]
        for _ in range(int(HOLD * FPS)):
            a.save(tmp / f"g{n:04d}.png"); n += 1
        steps = int(FADE * FPS)
        for k in range(1, steps + 1):
            Image.blend(a, b, k / (steps + 1)).save(tmp / f"g{n:04d}.png"); n += 1
    gif = OUT / "ph-thumbnail.gif"
    subprocess.run([FF, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "g%04d.png"),
                    "-vf", "split[a][b];[a]palettegen=max_colors=128:stats_mode=full[p];[b][p]paletteuse=dither=none",
                    "-loop", "0", str(gif)], check=True)
    print(f"{gif.name}  {gif.stat().st_size // 1024} KB, {n} frames")

    demo = OUT / "blvkware-kits-demo.mp4"
    if demo.exists():
        jpg = OUT / "youtube-thumbnail.jpg"
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", "1.5", "-i", str(demo), "-frames:v", "1",
                        "-vf", "scale=1280:720:flags=lanczos", "-q:v", "2", str(jpg)], check=True)
        print(f"{jpg.name}  {jpg.stat().st_size // 1024} KB")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
