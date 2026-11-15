"""Render the MutationScientist research report as HTML."""

from html import escape
from urllib.parse import urlencode

from scientific_evidence.retriever.graph import ATP_CONDITIONS, GRAPH_ASSAYS

ASSAY_NAMES = {
    "biochemical_binding": "Biochemical binding",
    "enzyme_inhibition": "Enzyme inhibition",
    "cellular_viability": "Cellular viability",
    "cellular_pathway_inhibition": "Cellular pathway inhibition",
    "structural_experiment": "Experimental structure",
    "clinical_observation": "Clinical observation",
    "unspecified": "Assay format unspecified",
}
TYPE_NAMES = {
    "annotation": "Curated annotation",
    "assay_status": "Assay status",
    "literature_reported": "Literature annotation",
    "literature_hypothesis": "Literature hypothesis",
    "computational_prediction": "Computational prediction",
    "reference": "Publication record",
    "experimental": "Experimental result",
}
SCOPES = {
    "direct": "Direct match",
    "related_profile": "Related profile",
    "entity_context": "Entity background",
}

STYLE = """
:root { color-scheme: light; font: 16px 'Inter', system-ui, sans-serif; color: #152d35; background: #f3f6f5; }
* { box-sizing: border-box; }
body { margin: 0; }
main { max-width: 920px; padding: 56px 26px 80px; margin: 0 auto; }
header { border-bottom: 1px solid #c9d8d4; padding-bottom: 24px; }
h1 { font-size: clamp(2rem, 6vw, 3.1rem); letter-spacing: -.055em; margin: 0 0 10px; }
h2 { font-size: 1.4rem; letter-spacing: -.03em; margin: 0; }
p { line-height: 1.55; margin: 8px 0; }
form { margin: 26px 0 0; }
label { font-weight: 650; display: block; margin-bottom: 8px; }
.question { display: flex; gap: 10px; align-items: flex-start; }
textarea { flex: 1; width: 100%; min-width: 0; font: inherit; min-height: 50px; padding: 12px; color: inherit;
  border: 1px solid #a5b8b4; border-radius: 6px; background: white; resize: vertical; }
button { font: inherit; font-weight: 650; border: 0; border-radius: 6px; padding: 13px 18px;
  background: #155c51; color: #fff; cursor: pointer; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; }
.actions .secondary { border: 1px solid #8aa9a1; color: #135f53; background: white; }
a { color: #135f53; text-underline-offset: .18em; overflow-wrap: anywhere; }
section { margin-top: 32px; }
.report-header { display: flex; align-items: baseline; flex-wrap: wrap; gap: 8px 15px; }
.mode, small, .muted { color: #46635e; }
.note, .error { padding: 12px 14px; border-left: 3px solid #688f85; background: #e5eeeb; margin: 12px 0; }
.error { border-left-color: #a33c2c; color: #782b21; background: #faeee9; }
article { background: white; border: 1px solid #cddbd7; border-radius: 6px; margin: 10px 0;
  padding: 14px 16px; overflow-wrap: anywhere; }
article p { margin: 6px 0; }
.meta { color: #46635e; font-size: .84rem; }
summary { cursor: pointer; color: #135f53; padding: 8px 0; }
details { margin-top: 14px; }
code { font-size: .88em; }
.graph-links { display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 6px 0 14px; }
.graph-links a { font-size: .9rem; }
.graph-path { margin-top: 8px; }
.graph-filters { display: flex; align-items: flex-end; flex-wrap: wrap; gap: 10px 14px; margin: 16px 0; }
.graph-filters label { font-size: .88rem; margin-bottom: 0; }
.graph-filters select, .graph-filters input[type=text] { display: block; font: inherit; color: inherit;
  background: white; border: 1px solid #a5b8b4; border-radius: 5px; padding: 8px; margin-top: 4px; }
.graph-filters .check { padding: 8px 0; }
.graph-filters button { padding: 8px 14px; font-size: .88rem; }
@media (max-width: 560px) { main { padding: 32px 16px 56px; } .question { flex-direction: column; } }
"""


def evidence_card(row, path_html=""):
    meta = [SCOPES[row["match_scope"]]]
    meta.append(ASSAY_NAMES.get(row["assay_type"]) or TYPE_NAMES.get(row["evidence_type"], row["evidence_type"]))
    meta.extend(row[key] for key in ("mutation_id", "compound_id") if row[key])
    details = row["details"]
    context = " · ".join(details[key] for key in (
        "protein_construct", "cell_line", "treatment_duration", "interpretation_note",
        "study_design", "variant_scope",
    ) if details.get(key))
    specificity = details.get("locator") or details.get("source_record_id")
    source = row["source_title"] or row["source_id"] or "Source"
    link = f'<a href="{escape(row["source_url"], quote=True)}">{escape(source)}</a>'
    location = f' · {escape(specificity)}' if specificity else ""
    claim = escape(row["claim"])
    if details.get("claim_verification") == "dataset_annotation_unverified":
        claim = f"Dataset annotation pending source-level verification. {claim}"
    return (
        f'<article><div class="meta">{escape(" · ".join(meta))}</div>'
        f'<p>{claim}</p>'
        + (f'<p class="meta">{escape(context)}</p>' if context else "")
        + f'<div class="meta">{link}{location} · <code>{escape(row["evidence_id"])}</code></div>'
        + path_html
        + "</article>"
    )


def render_report(report):
    mode = "Model-selected evidence" if report["status"] == "model_selected_evidence" else "Local evidence summary"
    if report["status"] == "model_selected_evidence" and report["model_id"]:
        mode += " · " + report["model_id"]
    count = report["exact_measurement_count"]
    notes = []
    if count == 0:
        notes.append("No exact-pair experimental measurement matched this query. Related profiles and entity background are labeled below.")
    elif count is not None:
        notes.append(f"Exact-pair measurements found: {count}.")
    elif report["measurement_coverage"]:
        notes.extend(
            f"{pair['mutation_id']} with {pair['compound_id']} · {pair['count']} exact-pair experimental measurements."
            for pair in report["measurement_coverage"]
        )
    if report["model_notice"]:
        notes.append(report["model_notice"])
    if report.get("clinical_comparison_notice"):
        notes.append(report["clinical_comparison_notice"])
    notices = "".join(f'<p class="note">{escape(note)}</p>' for note in notes)
    interpretation = "".join(
        f'<article><p>{escape(note["text"])}</p><div class="meta">'
        f'<a href="{escape(note["source_url"], quote=True)}">{escape(note["source_title"])}</a></div></article>'
        for note in report["interpretation"]
    )
    cards = "".join(evidence_card(row) for row in report["claims"])
    if not (interpretation or cards):
        cards = "<p>No source-linked result for this question.</p>"
    other = ""
    selected = {row["evidence_id"] for row in report["claims"]}
    for label, rows in (("More direct matches", report["evidence"]), ("More supporting context", report["context"])):
        hidden = [row for row in rows if row["evidence_id"] not in selected]
        if hidden:
            other += f"<details><summary>{label} ({len(hidden)})</summary>"
            other += "".join(evidence_card(row) for row in hidden) + "</details>"
    return (
        f'<section aria-labelledby="report-title"><div class="report-header">'
        f'<h2 id="report-title">Research report</h2><small>{escape(mode)}</small></div>'
        f'{notices}{interpretation}{cards}{other}</section>'
    )


def graph_link(keywords, label, *, offset=0, filters=None):
    params = {key: "1" if value is True else value for key, value in (filters or {}).items() if value}
    query = urlencode({"graph": keywords, "offset": offset, **params})
    return f'<a href="/?{escape(query, quote=True)}">{escape(label)}</a>'


def graph_controls(graph):
    filters = graph["filters"]

    def options(name, labels):
        entries = ['<option value="">Any</option>']
        for value, label in labels:
            selected = " selected" if filters[name] == value else ""
            entries.append(f'<option value="{escape(value, quote=True)}"{selected}>{escape(label)}</option>')
        return "".join(entries)

    assays = options("assay_type", [(value, ASSAY_NAMES[value]) for value in GRAPH_ASSAYS])
    atp = options("atp_condition", [(ATP_CONDITIONS[0], "ATP Km"), (ATP_CONDITIONS[1], ATP_CONDITIONS[1])])
    checked = " checked" if filters["exact_only"] else ""
    cell = escape(filters["cell_line"] or "", quote=True)
    keywords = escape(graph["keywords"], quote=True)
    return (
        f'<form action="/" method="get" class="graph-filters" aria-label="Filter graph evidence">'
        f'<input type="hidden" name="graph" value="{keywords}">'
        f'<label>Assay<select name="assay_type">{assays}</select></label>'
        f'<label>ATP condition<select name="atp_condition">{atp}</select></label>'
        f'<label>Cell line or clone<input type="text" name="cell_line" value="{cell}" maxlength="100" '
        f'placeholder="NCI-H1975 clone 2"></label>'
        f'<label class="check"><input type="checkbox" name="exact_only" value="1"{checked}> Exact variants only</label>'
        f'<button type="submit">Apply filters</button></form>'
    )


def graph_path(row, links, members, nodes, anchors, filters):
    profile = links.get("reports_on_profile")
    variant = links.get("reports_on_variant")
    scope = nodes[profile or variant]["identifier"] if profile or variant else ""
    path = []
    if links.get("references_protein") or scope:
        path.append(graph_link("P00533", "P00533"))
    if row["match_scope"] == "related_profile" and profile:
        components = [nodes[node]["identifier"] for node in members.get(profile, ()) if node in anchors]
        if components:
            components_html = " / ".join(graph_link(component, component) for component in components)
            path.append(components_html + " is part of " + graph_link(scope, scope))
    elif scope:
        path.append(graph_link(scope, scope))
    if compound_node := links.get("mentions_inhibitor"):
        compound = nodes[compound_node]
        path.append(graph_link(compound["identifier"], compound["label"]))
    if assay_node := links.get("has_assay_type"):
        assay = nodes[assay_node]["identifier"]
        query = " ".join(part for part in (scope, row["compound_id"]) if part) or "P00533"
        path.append(graph_link(query, ASSAY_NAMES.get(assay, assay), filters={**filters, "assay_type": assay}))
    if links.get("reported_in"):
        url = escape(row["source_url"], quote=True)
        path.append(f'<a href="{url}">Source for {escape(row["evidence_id"])}</a>')
    return '<nav class="graph-path meta" aria-label="Evidence relationships">' + " → ".join(path) + "</nav>"


def render_graph(graph):
    nodes = {node["id"]: node for node in graph["nodes"]}
    anchors = []
    for identifier in graph["anchors"]:
        node = nodes[identifier]
        label = escape(f'{node["label"]} · {node["identifier"]}' if node["type"] == "protein" else node["label"])
        if node["source_url"]:
            label = f'<a href="{escape(node["source_url"], quote=True)}">{label}</a>'
        anchors.append(label)
    summary = f'<p class="muted">{graph["total_matches"]:,} linked records'
    if anchors:
        summary += " · " + " · ".join(anchors)
    content = [summary + "</p>", graph_controls(graph)]
    for label, links in graph["browse"].items():
        content.append(f'<details><summary>{escape(label)}</summary><div class="graph-links">')
        content.extend(graph_link(f'P00533 {item["keyword"]}', item["label"], filters=graph["filters"]) for item in links)
        content.append("</div></details>")

    membership = {}
    record_links = {}
    for edge in graph["edges"]:
        if edge["relation"] == "part_of_profile":
            membership.setdefault(edge["to"], []).append(edge["from"])
        if nodes[edge["from"]]["type"] == "evidence":
            record_links.setdefault(edge["evidence_id"], {})[edge["relation"]] = edge["to"]
    for row in graph["evidence"]:
        path = graph_path(row, record_links[row["evidence_id"]], membership, nodes, graph["anchors"], graph["filters"])
        content.append(evidence_card(row, path))
    if not graph["evidence"]:
        content.append("<p>No linked evidence matched these keywords.</p>")
    previous = graph["offset"] - graph["limit"]
    following = graph["offset"] + graph["limit"]
    pages = []
    if graph["offset"]:
        pages.append(graph_link(graph["keywords"], "Previous", offset=max(0, previous), filters=graph["filters"]))
    if following < graph["total_matches"]:
        pages.append(graph_link(graph["keywords"], "Next", offset=following, filters=graph["filters"]))
    if pages:
        content.append('<nav class="graph-links" aria-label="Evidence pages">' + "".join(pages) + "</nav>")
    return '<section aria-labelledby="graph-title"><h2 id="graph-title">Graph search results</h2>' + "".join(content) + "</section>"


def render_page(question="", *, report=None, graph=None, error=None):
    message = f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    result = render_graph(graph) if graph else render_report(report) if report else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MutationScientist</title><style>{STYLE}</style></head>
<body><main>
<header><h1>MutationScientist</h1><p class="muted">Search source-linked evidence on EGFR mutations and inhibitors.</p></header>
<form method="post" action="/">
<label for="question">Research question or keywords</label>
<div class="question"><textarea id="question" name="question" maxlength="2000" rows="2"
placeholder="Why does gefitinib lose potency against T790M?" required>{escape(question)}</textarea>
<div class="actions"><button type="submit">Find evidence</button>
<button class="secondary" type="submit" name="mode" value="graph">Search graph</button></div></div>
</form>{message}{result}
</main></body></html>"""
