"""Local MutationScientist application and command-line research report."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from scientific_evidence.evidence_api import search_graph
from scientific_evidence.retriever.graph import ATP_CONDITIONS, GRAPH_ASSAYS

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
            url = urlsplit(self.path)
            if url.path != "/":
                self.send_error(404)
                return
            params = parse_qs(url.query)
            if "graph" in params:
                question = params["graph"][0]
                try:
                    graph = search_graph(
                        question, offset=int(params.get("offset", ["0"])[0]),
                        exact_only=params.get("exact_only") == ["1"],
                        assay_type=params.get("assay_type", [None])[0],
                        cell_line=params.get("cell_line", [None])[0],
                        atp_condition=params.get("atp_condition", [None])[0],
                    )
                except ValueError as exc:
                    self.respond(400, render_page(question[:200], error=str(exc)))
                    return
                self.respond(200, render_page(question, graph=graph))
                return
            self.respond(200, render_page())

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
                fields = parse_qs(body)
                question = fields.get("question", [""])[0]
                if fields.get("mode") == ["graph"]:
                    self.respond(200, render_page(question, graph=search_graph(question)))
                    return
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
    parser.add_argument("--graph", action="store_true", help="Search the evidence graph using keyword arguments.")
    parser.add_argument("--exact-only", action="store_true", help="Require exact mutation matches in graph search.")
    parser.add_argument("--assay-type", choices=GRAPH_ASSAYS, help="Filter graph search by assay type.")
    parser.add_argument("--cell-line", help="Filter graph search by exact cell line or clone label.")
    parser.add_argument("--atp-condition", choices=ATP_CONDITIONS, help="Filter graph search by ATP condition.")
    parser.add_argument("--port", type=int, default=8765, help="Port for the local web app.")
    args = parser.parse_args()
    try:
        if args.graph:
            if not args.question:
                parser.error("--graph requires a keyword string")
            graph = search_graph(
                args.question, exact_only=args.exact_only, assay_type=args.assay_type,
                cell_line=args.cell_line, atp_condition=args.atp_condition,
            )
            print(json.dumps(graph, ensure_ascii=False, indent=2))
            return
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
