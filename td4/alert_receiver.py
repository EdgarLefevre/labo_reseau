import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        for alert in payload.get("alerts", []):
            labels = alert.get("labels", {})
            print(f"[{alert.get('status', '?').upper()}] {labels.get('alertname', '?')} "
                  f"{labels.get('cible', labels.get('device', ''))}", flush=True)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


HTTPServer(("0.0.0.0", 5001), Handler).serve_forever()