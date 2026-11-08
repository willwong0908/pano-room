import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/pano-room-install"

sys.path.insert(0, str(SKILL / "assets/runtime/app"))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class PackageTests(unittest.TestCase):
    def test_generate_portable_deployment(self):
        prepare = load("prepare", SKILL / "scripts/prepare.py")
        with tempfile.TemporaryDirectory() as tmp:
            output = prepare.prepare(Path(tmp) / "app", ["/nas/旅行 全景", "/nas/另一个目录"], "http://192.0.2.2:9000", 9000)
            compose = json.loads((output / "compose.yaml").read_text())
            service = compose["services"]["pano-room"]
            self.assertEqual(service["ports"], ["9000:8765"])
            self.assertIn("/nas/旅行 全景:/sources/m2:ro", service["volumes"])
            roots = json.loads(service["environment"]["MEDIA_ROOTS"])
            self.assertEqual(len(roots), 2)
            self.assertEqual(service["environment"]["LAN_URL"], "http://192.0.2.2:9000")
            self.assertTrue((output / "app/server.py").is_file())
            with self.assertRaises(ValueError):
                prepare.prepare(output, ["/other"], "", 8765)

    def test_media_and_identity_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp).resolve() / "cache"
            media = Path(tmp).resolve() / "media"
            media.mkdir()
            previous = {key: os.environ.get(key) for key in ("CACHE_ROOT", "MEDIA_ROOTS", "LAN_URL")}
            os.environ.update(CACHE_ROOT=str(cache), MEDIA_ROOTS=json.dumps({"m2": {"label": "样片", "path": str(media)}}), LAN_URL="http://192.0.2.2:8765")
            try:
                app = load("pano_test", SKILL / "assets/runtime/app/server.py")
                source = media / "sample.mp4"
                data = bytes(range(256)) * 32
                source.write_bytes(data)
                key = app.identify(source)
                (cache / key).mkdir()
                (cache / key / "probe.json").write_text(json.dumps({"streams": [{"codec_type": "video", "width": 7680, "height": 3840, "codec_name": "hevc"}], "format": {"duration": "5.84"}}))
                server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                base = "http://127.0.0.1:" + str(server.server_port)
                try:
                    library = json.load(urllib.request.urlopen(base + "/api/library"))
                    self.assertEqual(library["items"][0]["width"], 7680)
                    response = urllib.request.urlopen(urllib.request.Request(base + "/source/" + key, headers={"Range": "bytes=1024-2047"}))
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.read(), data[1024:2048])
                    config = json.load(urllib.request.urlopen(base + "/api/connection"))
                    probe = urllib.request.urlopen(base + "/api/lan")
                    self.assertEqual(probe.headers["Access-Control-Allow-Origin"], "*")
                    self.assertEqual(config["instance_id"], json.load(probe)["instance_id"])
                    self.assertFalse(list(cache.rglob("*.mp4")))
                finally:
                    server.shutdown()
                    server.server_close()
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

if __name__ == "__main__":
    unittest.main()
