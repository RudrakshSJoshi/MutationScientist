"""Local MutationScientist application and command-line research report."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from .pages.mutation_scientist import render_page
from .services.evidence_service import answer_question
from .services.llm_service import configured_model


def serve(port, generate, model_id):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, html):
            data = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                self.respond(200, render_page())
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path != "/":
                self.send_error(404)
                return
            question = ""
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 28000:
                    raise ValueError("Submit one research question of up to 2,000 characters.")
                body = self.rfile.read(length).decode("utf-8")
                question = parse_qs(body).get("question", [""])[0]
                report = answer_question(question, generate=generate, model_id=model_id)
            except ValueError as exc:
                self.respond(400, render_page(question[:2000], error=str(exc)))
                return
            self.respond(200, render_page(question, report=report))

    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"MutationScientist is running at http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="Print a source-linked research report as JSON.")
    parser.add_argument("--port", type=int, default=8765, help="Port for the local web app.")
    args = parser.parse_args()
    try:
        generate, model_id = configured_model()
        if args.question is not None:
            report = answer_question(args.question, generate=generate, model_id=model_id)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            serve(args.port, generate, model_id)
    except ValueError as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
