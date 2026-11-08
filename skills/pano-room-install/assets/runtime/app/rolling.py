"""Serve virtual HLS fragments from the source MP4. Only the sample index is retained."""
import base64
import functools
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import threading

BUILD_LOCK = threading.Lock()
PROCESS_DIR = tempfile.TemporaryDirectory(prefix="pano-hls-")
APP = Path(__file__).resolve().parent

@functools.lru_cache(maxsize=1)
def indexer():
    override = os.environ.get("PANO_INDEXER")
    if override:
        return override
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if arch is None:
        raise ValueError("此 NAS 架构不支持分段索引。")
    exe = Path(PROCESS_DIR.name) / "indexer"
    shutil.copyfile(APP / ("indexer-" + arch), exe)
    exe.chmod(0o700)
    return str(exe)

@functools.lru_cache(maxsize=3)
def _load(path, key):
    proc = subprocess.run([indexer(), str(path)], capture_output=True, timeout=120)
    if proc.returncode:
        raise ValueError("此文件的封装暂不能建立关键帧索引。")
    data = json.loads(proc.stdout)
    segments = data["Segments"]
    if not segments:
        raise ValueError("文件没有可播放的片段。")
    lines = ["#EXTM3U", "#EXT-X-VERSION:7", "#EXT-X-PLAYLIST-TYPE:VOD",
             "#EXT-X-TARGETDURATION:" + str(max(1, math.ceil(max(s["Duration"] for s in segments)))),
             '#EXT-X-MAP:URI="init.mp4"', "#EXT-X-MEDIA-SEQUENCE:0"]
    for i, seg in enumerate(segments):
        lines.extend([f'#EXTINF:{seg["Duration"]:.6f},', f"{i}.m4s"])
        seg["Header"] = base64.b64decode(seg["Header"])
    lines.append("#EXT-X-ENDLIST")
    return ("\n".join(lines) + "\n").encode(), base64.b64decode(data["Init"]), segments

def serve(handler, path, key, resource):
    with BUILD_LOCK:
        playlist, init, segments = _load(path, key)
    parts = []
    if resource == "index.m3u8":
        prefix, mime = playlist, "application/vnd.apple.mpegurl"
    elif resource == "init.mp4":
        prefix, mime = init, "video/mp4"
    else:
        number = int(resource.split(".")[0])
        if number >= len(segments):
            handler.send_error(404)
            return
        seg = segments[number]
        prefix, parts, mime = seg["Header"], seg["Ranges"], "video/iso.segment"
    size = len(prefix) + sum(length for _, length in parts)
    start, end, partial = 0, size - 1, False
    if header := handler.headers.get("Range"):
        import re
        r = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
        if r and any(r.groups()):
            left, right = r.groups()
            start = int(left) if left else max(0, size-int(right))
            end = min(end, int(right)) if left and right else end
        if not r or not any(r.groups()) or start > end:
            handler.send_response(416)
            handler.send_header("Content-Range", f"bytes */{size}")
            handler.end_headers()
            return
        partial = True
    handler.send_response(206 if partial else 200)
    if partial:
        handler.send_header("Content-Range", f"bytes {start}-{end}/{size}")
    handler.send_header("Content-Type", mime)
    handler.send_header("Accept-Ranges", "bytes")
    handler.send_header("Content-Length", str(end-start+1))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    if handler.command == "HEAD":
        return
    if start < len(prefix):
        handler.wfile.write(prefix[start:end+1])
    position = len(prefix)
    if not parts or end < position:
        return
    with path.open("rb") as src:
        for offset, length in parts:
            skip = max(0, start-position)
            count = min(length-skip, end-position+1-skip)
            if count > 0:
                sent = handler.connection.sendfile(src, offset+skip, count)
                if sent != count:
                    raise ConnectionResetError("原片读取中断")
            position += length
            if position > end:
                break
