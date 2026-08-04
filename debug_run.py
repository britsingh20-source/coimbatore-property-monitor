import os
import sys
import traceback
import platform

OUT = "debug_output.txt"

lines = []
lines.append(f"python: {platform.python_version()}")
lines.append(f"YOUTUBE_API_KEY set: {bool(os.environ.get('YOUTUBE_API_KEY'))}")
lines.append(f"GEMINI_API_KEY set: {bool(os.environ.get('GEMINI_API_KEY'))}")

try:
    import main
    main.run()
    lines.append("RESULT: SUCCESS - main.run() completed without raising")
except Exception:
    lines.append("RESULT: FAILURE")
    lines.append("")
    lines.append("--- TRACEBACK ---")
    lines.append(traceback.format_exc())

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("\n".join(lines))
