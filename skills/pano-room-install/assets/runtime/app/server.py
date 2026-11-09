"""环映原画播放器：只读全景 MP4/MOV，HTTP Range 直读原文件。"""
import concurrent.futures
import rolling
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import subprocess
import threading
import tempfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

CACHE = Path(os.environ.get("CACHE_ROOT", "/cache")).resolve()
APP = Path(__file__).parent
CACHE.mkdir(parents=True, exist_ok=True)
# 只用于确认局域网目标属于同一份部署，不是访问凭据。
INSTANCE_FILE = CACHE / 'instance-id'
if not INSTANCE_FILE.exists():
    INSTANCE_FILE.write_text(secrets.token_hex(16))
INSTANCE_ID = INSTANCE_FILE.read_text().strip()
LAN_URL = os.environ.get('LAN_URL', '').rstrip('/')
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")
LOCK = threading.RLock()
METADATA_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1)
METADATA_LOCK = threading.Lock()
METADATA_JOBS = {}
CONFIG_LOCK = threading.Lock()
ROOT_CONFIG = json.loads(os.environ.get("MEDIA_ROOTS", '{"m2":{"label":"影片目录","path":"/sources/m2"}}'))
ROOTS = {key: {"label": value["label"], "path": Path(value["path"])} for key, value in ROOT_CONFIG.items()}
SETTINGS = CACHE / "folders.json"
def selected_folders():
    if SETTINGS.exists():
        return json.loads(SETTINGS.read_text())
    return [{"root": key, "path": "", "name": value["label"]} for key, value in ROOTS.items()]

def directory(root, relative=""):
    if root not in ROOTS:
        raise ValueError("请选择可用的存储空间。")
    base = ROOTS[root]["path"].resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise ValueError("目录超出可访问的存储空间。")
    if not path.is_dir():
        raise FileNotFoundError("这个文件夹不存在或存储盘未挂载。")
    return path

def folder_config():
    return {
        "roots": [{"id": key, "name": value["label"]} for key, value in ROOTS.items() if value["path"].is_dir()],
        "folders": selected_folders(),
    }

def change_folders(body):
    action = body.get("action")
    root = body.get("root", "")
    relative = body.get("path", "")
    if not isinstance(relative, str):
        raise ValueError("目录格式不正确。")
    with CONFIG_LOCK:
        entries = selected_folders()
        if action == "add":
            path = directory(root, relative)
            relative = str(path.relative_to(ROOTS[root]["path"].resolve()))
            if relative == ".":
                relative = ""
            if any(e["root"] == root and e["path"] == relative for e in entries):
                raise ValueError("这个文件夹已经在片库中。")
            entries.append({"root": root, "path": relative, "name": path.name if relative else ROOTS[root]["label"]})
        elif action == "remove":
            entries = [e for e in entries if (e["root"], e["path"]) != (root, relative)]
        else:
            raise ValueError("未知的目录操作。")
        with tempfile.NamedTemporaryFile(mode="w", dir=CACHE, delete=False) as stream:
            json.dump(entries, stream, ensure_ascii=False)
        Path(stream.name).replace(SETTINGS)
    return folder_config()

def browse(root, relative):
    path = directory(root, relative)
    base = ROOTS[root]["path"].resolve()
    current = str(path.relative_to(base))
    if current == ".":
        current = ""
    children = []
    for p in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if p.name.startswith(".") or p.is_symlink() or not p.is_dir():
            continue
        children.append({"name": p.name, "path": str(p.relative_to(base))})
    return {"root": root, "path": current, "directories": children}


def probe(path):
    result = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise ValueError("无法读取视频，请检查原片是否完整。")
    return json.loads(result.stdout)

def identify(path):
    st = path.stat()
    default = ROOTS.get("m2", next(iter(ROOTS.values())))["path"] / "全景视频"
    relative = str(path.relative_to(default)) if path.is_relative_to(default) else str(path)
    return hashlib.sha256((relative+str(st.st_size)+str(st.st_mtime_ns)).encode()).hexdigest()[:24]

def sources():
    files = []
    seen = set()
    for entry in selected_folders():
        try:
            selected = directory(entry["root"], entry["path"])
        except (ValueError, FileNotFoundError):
            continue
        for base, dirs, names in os.walk(selected, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for name in sorted(names):
                p = Path(base) / name
                if name.startswith(".") or p.suffix.lower() not in {".mp4", ".mov"}:
                    continue
                if not p.resolve().is_relative_to(selected):
                    continue
                st = p.stat()
                inode = (st.st_dev, st.st_ino)
                if inode in seen:
                    continue
                seen.add(inode)
                files.append(p)
    return files

def source_folder(path):
    for entry in selected_folders():
        base = ROOTS[entry["root"]]["path"] / entry["path"]
        if path.is_relative_to(base):
            relative = str(path.parent.relative_to(base))
            return entry["name"] if relative == "." else entry["name"] + " / " + relative
    return "其他"


def source_for(key):
    for p in sources():
        if identify(p) == key:
            return p
    raise FileNotFoundError("视频已移动或发生变化，请刷新片库。")

def info(path, key):
    target = CACHE / key
    target.mkdir(exist_ok=True)
    meta = target / "probe.json"
    if meta.exists():
        return json.loads(meta.read_text())
    details = probe(path)
    with tempfile.NamedTemporaryFile(mode="w", dir=target, delete=False) as temporary:
        json.dump(details, temporary)
    Path(temporary.name).replace(meta)
    return details

def available_info(path, key):
    cached = CACHE / key / "probe.json"
    if cached.exists():
        return json.loads(cached.read_text())
    with METADATA_LOCK:
        if key not in METADATA_JOBS:
            METADATA_JOBS[key] = METADATA_POOL.submit(info, path, key)
    return None

def media_details(path, key):
    details = info(path, key)
    video = next((s for s in details.get("streams", []) if s.get("codec_type") == "video"), {})
    width, height = int(video.get("width", 0)), int(video.get("height", 0))
    return {"width": width, "height": height, "codec": video.get("codec_name", ""), "hdr": video.get("color_transfer") in {"arib-std-b67", "smpte2084"}, "panorama": bool(height and abs(width/height-2) < .1)}

def library():
    result = []
    for path in sources():
        key = identify(path)
        details = available_info(path, key)
        if details:
            data = media_details(path, key)
            if not data["panorama"]:
                continue
        else:
            data = {"width": None, "height": None, "codec": "", "hdr": False, "panorama": None}
        fmt = details.get("format", {}) if details else {}
        created = fmt.get("tags", {}).get("creation_time", "")
        result.append({"id": key, "title": path.stem, "filename": path.name, "folder": source_folder(path), "seconds": float(fmt.get("duration", 0)) if details else None, "date": created[:10] or datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d"), "format": path.suffix[1:].upper(), "bytes": path.stat().st_size, "thumb": "/thumbnail/"+key, **data})
    return {"items": result}

class Handler(BaseHTTPRequestHandler):
    def json(self, value, code=200, cors=False):
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(code)
        if cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def file(self, path, mime=None):
        if not path.is_file():
            self.send_error(404)
            return
        size = path.stat().st_size
        start, end, partial = 0, size-1, False
        header = self.headers.get("Range")
        if header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
            if not match or not any(match.groups()):
                self.send_error(416)
                return
            left, right = match.groups()
            if left:
                start, end = int(left), min(int(right), size-1) if right else size-1
            else:
                start = max(0, size-int(right))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            partial = True
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", mime or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(end-start+1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store" if path.suffix.lower() in {".html", ".mp4", ".mov"} else "private, max-age=3600")
        self.send_header("X-Content-Type-Options", "nosniff")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if self.command == "HEAD":
            return
        with path.open("rb") as stream:
            stream.seek(start)
            remaining = end-start+1
            while remaining:
                chunk = stream.read(min(1024*1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_POST(self):
        try:
            route = urlsplit(self.path)
            if match := re.fullmatch(r"/api/playback-test/([a-f0-9]{24})", route.path):
                origin = self.headers.get("Origin")
                size = int(self.headers.get("Content-Length", "0"))
                if origin and urlsplit(origin).netloc != self.headers.get("Host"):
                    return self.json({"message":"来源不匹配"},403)
                if not 0 < size <= 12000:
                    return self.json({"message":"数据过大"},400)
                report = json.loads(self.rfile.read(size))
                if not isinstance(report,dict) or not isinstance(report.get("rounds"),list):
                    raise ValueError("无效报告")
                target = CACHE/"phone-tests"
                target.mkdir(exist_ok=True)
                with LOCK:
                    with tempfile.NamedTemporaryFile(mode="w",dir=target,delete=False) as f:
                        json.dump(report,f,ensure_ascii=False)
                    Path(f.name).replace(target/(match[1]+".json"))
                    for old in sorted(target.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True)[32:]:
                        old.unlink()
                self.json({"ok":True})
            elif route.path == "/api/folders":
                if self.headers.get("Origin") and urlsplit(self.headers["Origin"]).netloc != self.headers.get("Host"):
                    self.json({"message": "请从环映网页操作。"}, 403)
                    return
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 16384:
                    raise ValueError("请求大小不正确。")
                self.json(change_folders(json.loads(self.rfile.read(size))))
            elif route.path == "/api/prepare":
                key = parse_qs(route.query).get("id", [""])[0]
                path = source_for(key)
                details = media_details(path, key)
                if not details["panorama"]:
                    raise ValueError("请选择已经拼接好的 2:1 全景 MP4/MOV。")
                self.json({"state": "ready", "url": "/source/"+key, **details})
            else:
                self.send_error(404)
        except FileNotFoundError as e:
            self.json({"message": str(e)}, 404)
        except (ValueError, TypeError) as e:
            self.json({"message": str(e)}, 400)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            route = urlsplit(self.path)
            if route.path == "/api/connection":
                self.json({"lan_url": LAN_URL, "instance_id": INSTANCE_ID})
            elif route.path == "/api/lan":
                self.json({"instance_id": INSTANCE_ID}, cors=True)
            elif route.path == "/api/health":
                self.json({"ok": any(r["path"].is_dir() for r in ROOTS.values()), "version": "0.5.1"})
            elif route.path == "/api/folders":
                self.json(folder_config())
            elif route.path == "/api/directories":
                query = parse_qs(route.query)
                self.json(browse(query.get("root", [""])[0], query.get("path", [""])[0]))
            elif route.path == "/api/library":
                self.json(library())
            elif re.fullmatch(r"/thumbnail/[a-f0-9]{24}", route.path):
                key = route.path.rsplit("/", 1)[-1]
                thumb = CACHE/key/"thumb.jpg"
                if not thumb.exists():
                    # 缩略图单独生成，原视频始终直接读取。
                    path = source_for(key)
                    with LOCK:
                        if not thumb.exists():
                            tmp = thumb.with_name("thumb.tmp.jpg")
                            result = subprocess.run([FFMPEG, "-v", "error", "-y", "-threads", "1", "-i", str(path), "-map", "0:v:0", "-frames:v", "1", "-vf", "scale=240:135:force_original_aspect_ratio=increase,crop=240:135", str(tmp)], capture_output=True, timeout=30)
                            if result.returncode == 0:
                                tmp.replace(thumb)
                self.file(thumb)
            elif re.fullmatch(r"/source/[a-f0-9]{24}", route.path):
                key = route.path.rsplit("/", 1)[-1]
                self.file(source_for(key))
            elif match := re.fullmatch(r"/hls/([a-f0-9]{24})/(index\.m3u8|init\.mp4|[0-9]{1,9}\.m4s)", route.path):
                key, resource = match.groups()
                rolling.serve(self, source_for(key), key, resource)
            elif route.path == "/auto-test.js":
                self.file(APP/"auto.js","application/javascript")
            elif match := re.fullmatch(r"/api/playback-test/([a-f0-9]{24})", route.path):
                path = CACHE/"phone-tests"/(match[1]+".json")
                self.json(json.loads(path.read_text()) if path.exists() else {"status":"尚未连接"})
            elif route.path == "/hls.min.js":
                self.file(APP / "hls.min.js", "application/javascript")
            elif route.path in {"/", "/index.html"}:
                self.file(APP/"index.html", "text/html; charset=utf-8")
            else:
                self.send_error(404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except FileNotFoundError as e:
            self.json({"message": str(e)}, 404)
        except ValueError as e:
            self.json({"message": str(e)}, 400)
        except Exception as e:
            print(type(e).__name__, str(e), flush=True)
            self.json({"message": "读取失败，请稍后刷新。"}, 500)

if __name__ == "__main__":
    print("Pano Room original-player listening on 8765", flush=True)
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8765"))), Handler).serve_forever()
