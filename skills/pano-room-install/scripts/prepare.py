#!/usr/bin/env python3
"""生成独立的环映部署目录，宿主机路径必须来自目标 NAS 的实际查询结果。"""
import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit

def prepare(output, media, lan_url, port, build=False):
    if output.exists():
        raise ValueError("输出目录已存在，请检查现有部署后使用新的暂存目录。")
    if not 1 <= port <= 65535:
        raise ValueError("端口必须在 1 到 65535 之间。")
    if not media or any(not path.startswith("/") or ":" in path for path in media):
        raise ValueError("影片目录必须使用 NAS 原生绝对路径，路径中不能包含冒号。")
    if lan_url:
        parsed = urlsplit(lan_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("局域网入口应为完整的 http(s)://主机:端口。")
    assets = Path(__file__).resolve().parent.parent / "assets/runtime"
    roots = {}
    volumes = ["./app:/app:ro", "./cache:/cache"]
    for index, path in enumerate(media):
        key = "m2" if index == 0 else "source" + str(index + 1)
        container = "/sources/" + key
        roots[key] = {"label": Path(path).name or "影片目录", "path": container}
        volumes.append(path + ":" + container + ":ro")
    service = {
        "restart": "unless-stopped",
        "ports": [str(port) + ":8765"],
        "volumes": volumes,
        "environment": {
            "LAN_URL": lan_url.rstrip("/"),
            "MEDIA_ROOTS": json.dumps(roots, ensure_ascii=False),
            "TZ": "Asia/Shanghai",
            "PYTHONUNBUFFERED": "1",
        },
        "healthcheck": {
            "test": ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health')"],
            "interval": "30s", "timeout": "5s", "retries": 3,
        },
    }
    if build:
        service["build"] = "."
    else:
        service["image"] = "ubuntu:24.04"
        service["command"] = ["sh", "/app/start.sh"]
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(assets, output)
    # JSON 是合法的 YAML，Compose 可直接读取，避免额外的 YAML 依赖。
    (output / "compose.yaml").write_text(json.dumps({"services": {"pano-room": service}}, ensure_ascii=False, indent=2) + "\n")
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--media", action="append", required=True, help="可重复传入目标 NAS 原生目录")
    parser.add_argument("--lan-url", default="", help="当前用户的 NAS 局域网入口")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--build", action="store_true", help="部署时构建 Dockerfile")
    args = parser.parse_args()
    try:
        print(prepare(args.output.resolve(), args.media, args.lan_url, args.port, args.build))
    except ValueError as error:
        parser.error(str(error))

if __name__ == "__main__":
    main()
