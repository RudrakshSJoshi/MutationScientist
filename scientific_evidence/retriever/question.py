"""Resolve natural-language questions to the indexed EGFR entities."""

import re
import sqlite3
from contextlib import closing
from itertools import product
from pathlib import Path

from .search import DATABASE, TOKEN

ATOM = re.compile(
    r"\b(?:[a-z][0-9]{2,4}[a-z]|(?:egfr|prof|cmp|bdb)_[a-z0-9_]+|[a-z]+tinib)\b", re.I
)
PMID = re.compile(r"(?:\bpmid\s*[:#]?\s*|pubmed\.ncbi\.nlm\.nih\.gov/)(\d+)", re.I)
DOI = re.compile(r"\b(10\.\d{4,9}/[^\s<>\"']+)", re.I)
ENDPOINT = re.compile(r"\b((?:IC|EC)\s*[5₅]\s*[0₀]|K[\s_]?[DI])s?\b", re.I)
CONCENTRATION = re.compile(r"([<>]?)\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(nM|[µμu]M|mM)\b")
METRIC_DEFINITION = re.compile(r"\b(?:pool(?:ed|ing)?|difference between|define|distinguish)\b", re.I)
ANNOTATION_TERMS = re.compile(
    r"\b(?:structural class|structural context|residue change|canonical|exon|allelic phase|cis|trans)\b",
    re.I,
)
CLONE_TERMS = re.compile(r"\bNCI[- ]H1975\b", re.I)
NAMED_CLONE = re.compile(r"\bclone\s+(\d+)\b", re.I)
ONE_MILLIMOLAR = r"(?<![\w.])1(?:\.0+)?\s*(?:mmol\s*/\s*l|mM|millimolar)\b"
HIGH_ATP = re.compile(rf"{ONE_MILLIMOLAR}[^.?]{{0,24}}\bATP\b|\bATP\b[^.?]{{0,24}}{ONE_MILLIMOLAR}", re.I)
KM_ATP = re.compile(r"\b(?:K_?m(?:\s*[, _-]?\s*ATP)?|Michaelis constant)\b", re.I)
ASSAY_TERMS = {
    "biochemical_binding": r"\b(?:direct binding|surface plasmon resonance|SPR)\b",
    "enzyme_inhibition": r"\b(?:enzyme (?:activity|inhibition|assay|IC50)|kinase inhibition|mobility.shift)\b",
    "cellular_viability": r"\b(?:cell(?:ular)? viability|viability|ATPlite)\b",
    "cellular_pathway_inhibition": r"\b(?:pathway inhibition|EGFR phosphorylation|pEGFR)\b",
    "clinical_observation": (
        r"\b(?:clinical (?:observations?|responses?|outcomes?)|works clinically|cfDNA|"
        r"progression[- ]free survival|overall survival|objective response rate|PFS|ORR)\b"
    ),
    "structural_experiment": r"\b(?:crystal structures?|crystallized|crystallised|crystallography)\b",
}
FILLER = frozenset(
    "the an a what which tell me show find give about of for is are does do how why in to from egfr can you "
    "provide evidence studies study mutation variant inhibitor results discuss with please on was reported".split()
)


def entity_spans(db, question):
    rows = db.execute(
        "SELECT kind, alias, canonical_id FROM aliases "
        "WHERE (kind <> 'compound' OR substr(canonical_id, 1, 4) = 'CMP_') "
        "AND alias NOT IN ('other', 'unspecified') "
        "ORDER BY CASE kind WHEN 'mutation' THEN 0 WHEN 'profile' THEN 1 ELSE 2 END"
    )
    aliases = {}
    for kind, label, canonical in rows:
        aliases.setdefault(label, (kind, canonical))
    aliases.update({
        "wild-type": ("mutation", "EGFR_WT"),
        "wild type": ("mutation", "EGFR_WT"),
        "exon 19 deletion": ("mutation", "EGFR_ex19del"),
    })
    patterns = {}
    for label in sorted(aliases, key=len, reverse=True):
        expression = re.escape(label).replace(r"\ ", r"\s+")
        # A slash or plus between substitutions denotes an explicit profile.
        expression = expression.replace("/", r"\s*[/+]\s*")
        patterns.setdefault(expression, label)
    names = {f"e{i}": label for i, label in enumerate(patterns.values())}
    pattern = "|".join(f"(?P<{key}>{expr})" for key, expr in zip(names, patterns))
    for match in re.finditer(rf"(?<!\w)(?:{pattern})(?!\w)", question, re.I):
        label = names[match.lastgroup]
        kind, value = aliases[label]
        if kind == "mutation" and "/" in label:
            kind, value = "profile", "PROF_" + value.removeprefix("EGFR_")
        yield kind, value, match.span()

    for match in re.finditer(r"\bBDB_\d+\b", question, re.I):
        identifier = match[0].upper()
        row = db.execute(
            "SELECT canonical_id FROM aliases WHERE kind = 'compound' AND alias = ?",
            (identifier.lower(),),
        ).fetchone()
        if row:
            equivalent = db.execute(
                "SELECT equivalent_id FROM compound_equivalents "
                "WHERE compound_id = ? AND substr(equivalent_id, 1, 4) = 'CMP_'",
                (identifier,),
            ).fetchone()
            yield "compound", equivalent[0] if equivalent else row[0], match.span()


def plan_question(question, *, database=DATABASE):
    """Resolve a question to bounded evidence lookups and ranking signals."""
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("Enter a question of 1–2,000 characters.")
    path = Path(database).resolve()
    # Ignore apparent mutation/compound IDs inside a DOI or a recognized alias.
    doi = DOI.search(question)
    pmid = PMID.search(question)
    entity_text = question
    for identifier in (doi, pmid):
        if identifier:
            start, end = identifier.span()
            entity_text = entity_text[:start] + " " * (end - start) + entity_text[end:]
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        entities = list(entity_spans(db, entity_text))
    spans = [span for _, _, span in entities] + [m.span() for m in (doi, pmid) if m]
    unknown = [
        token[0] for token in ATOM.finditer(question)
        if not any(start <= token.start() and token.end() <= end for start, end in spans)
    ]
    if unknown:
        raise ValueError("Unrecognized EGFR mutation, profile or inhibitor ID: " + ", ".join(unknown))

    variants = {}
    compounds = []
    for kind, value, _ in sorted(entities, key=lambda item: item[2]):
        if kind == "compound":
            if value not in compounds:
                compounds.append(value)
            continue
        suffix = value.split("_", 1)[1]
        if suffix not in variants or kind == "profile":
            variants[suffix] = {"mutation_profile" if kind == "profile" else "mutation_id": value}
    numbered_clones = {int(name) for name in NAMED_CLONE.findall(question)}
    parental = bool(re.search(r"\bparental\b", question, re.I))
    panel = bool(CLONE_TERMS.search(question))
    if panel and re.search(r"\bclones\b", question, re.I):
        variants.pop("C797S", None)
        variants.setdefault("L858R_T790M", {"mutation_profile": "PROF_L858R_T790M"})
        variants.setdefault("L858R_T790M_C797S", {"mutation_profile": "PROF_L858R_T790M_C797S"})
    elif panel and not variants:
        if parental:
            variants["L858R_T790M"] = {"mutation_profile": "PROF_L858R_T790M"}
        if numbered_clones:
            variants["L858R_T790M_C797S"] = {"mutation_profile": "PROF_L858R_T790M_C797S"}
    elif {"T790M", "L858R"} <= variants.keys() and re.search(r"\bL858R background\b", question, re.I):
        variants.setdefault("L858R_T790M", {"mutation_profile": "PROF_L858R_T790M"})
    if len(variants) > 3 or len(compounds) > 2:
        raise ValueError("Compare up to three EGFR profiles and two inhibitors per question.")

    citation = {}
    if doi:
        citation["doi"] = doi[1].rstrip(".,;?)]}")
    if pmid:
        citation["pmid"] = pmid[1]
    endpoints = {
        re.sub(r"[\s_]", "", m[0]).translate(str.maketrans("₅₀", "50")).upper()
        for m in ENDPOINT.finditer(question)
    }
    assays = [name for name, pattern in ASSAY_TERMS.items() if re.search(pattern, question, re.I)]
    concentrations = [
        (relation, float(value.replace(",", "")), unit.replace("μ", "µ"))
        for relation, value, unit in CONCENTRATION.findall(question)
    ]
    model_output = "affinity_pred_value" in question
    definitions = METRIC_DEFINITION.search(question) and len(endpoints) >= 2 and not (variants or compounds)
    annotation_first = bool(ANNOTATION_TERMS.search(question)) and not concentrations
    cell_line = None
    if assays == ["cellular_viability"] and (panel or "L858R_T790M_C797S" in variants):
        if len(numbered_clones) == 1 and not parental:
            cell_line = f"NCI-H1975 clone {next(iter(numbered_clones))}"
        elif panel and parental and not numbered_clones and not re.search(r"\bclones?\b", question, re.I):
            cell_line = "NCI-H1975 parental"
    atp_condition = None
    if assays == ["enzyme_inhibition"]:
        high_atp = HIGH_ATP.search(question)
        km_atp = KM_ATP.search(question)
        if bool(high_atp) != bool(km_atp):
            atp_condition = "1 mmol/L ATP" if high_atp else "Km,ATP"
    lookups = []
    for variant, drug in product(list(variants.values()) or [{}], compounds or [None]):
        lookup = {**variant, **citation}
        if drug:
            lookup["compound_id"] = drug
        if len(endpoints) == 1:
            lookup["measurement_type"] = next(iter(endpoints))
        if len(assays) == 1 and not (concentrations and assays == ["clinical_observation"]):
            lookup["assay_type"] = assays[0]
            if assays == ["clinical_observation"] and re.search(r"\bresponse(?:s| rate)?\b", question, re.I):
                lookup["evidence_category"] = "clinical_response"
        if cell_line:
            lookup["cell_line"] = cell_line
        if atp_condition:
            lookup["atp_condition"] = atp_condition
        lookups.append(lookup)
    if not (variants or compounds or citation) and len(assays) > 1:
        # Named methods distinguish measurements within the same assay category.
        method_queries = {
            "biochemical_binding": (r"\b(?:SPR|surface plasmon resonance)\b", "SPR"),
            "enzyme_inhibition": (r"\bmobility.shift\b", "mobility shift"),
            "cellular_viability": (r"\bATPlite\b", "ATPlite"),
            "clinical_observation": (r"\bcfDNA\b", "cfDNA"),
        }
        lookups = []
        for assay in assays:
            lookup = {"assay_type": assay}
            if assay in method_queries:
                pattern, keyword = method_queries[assay]
                if re.search(pattern, question, re.I):
                    lookup["query"] = keyword
            lookups.append(lookup)
    elif lookups == [{}] and not definitions:
        keywords = [word for word in TOKEN.findall(question.casefold()) if word not in FILLER]
        if not keywords:
            raise ValueError("Include an EGFR variant, inhibitor, publication identifier or search terms.")
        lookups = [{"query": " ".join(keywords)}]
    if definitions:
        lookups = []
    return lookups, concentrations, annotation_first or model_output, bool(definitions)
