#!/usr/bin/env python3
"""Plain static host with Range/206 — no manifest, no route map.

Mimics ordinary static hosting (Netlify/S3/nginx) so the deliverable is tested
under the conditions it will actually ship on, minus the one thing
http.server lacks: byte-range requests, which video playback requires.
"""
import os, re, sys, functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class H(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404); return None
        size = os.fstat(f.fileno()).st_size
        m = re.match(r"bytes=(\d*)-(\d*)", rng.strip())
        if not m:
            f.close(); self.send_error(400); return None
        s, e = m.group(1), m.group(2)
        if s == "":
            length = int(e); start = max(0, size - length); end = size - 1
        else:
            start = int(s); end = int(e) if e else size - 1
        if start >= size:
            f.close(); self.send_error(416); return None
        end = min(end, size - 1)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(65536, remaining))
            if not chunk: break
            try: self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError): break
            remaining -= len(chunk)
        f.close()
        return None

    def log_message(self, *a): pass

if __name__ == "__main__":
    root, port = sys.argv[1], int(sys.argv[2])
    os.chdir(root)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
