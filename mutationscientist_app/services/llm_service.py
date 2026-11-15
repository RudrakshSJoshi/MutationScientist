"""
llm_service.py — the MutationScientist report interface (Person 1 / Adaption).

Modes:
  * REAL  — built context is sent to a served model. Two providers are supported:
      1. Adaption Responses API (PRIMARY) — when ADAPTION_API_KEY + ADAPTION_STACK
         are set. POST {base}/api/v1/responses with body
         {model:"stack:<slug>", input:<context text>, instructions:<persona>,
         temperature}. Reply read from JSON "output_text" (fallback output[]).
         Base defaults to https://api.prod.adaptionlabs.ai.
      2. Generic OpenAI-compatible endpoint (SECONDARY) — when OPENAI_BASE_URL +
         OPENAI_API_KEY + OPENAI_MODEL are set. POST {base}/chat/completions.
    Adaption takes precedence when both are configured. Any failure degrades
    gracefully to the template.
  * MOCK  — a grounded TEMPLATE report. It only ever restates values that are
            present in the supplied context (mutation record, measurements,
            Boltz prediction, evidence). It invents no numbers, no mechanisms
            and no citations, and it is clearly labelled as not-the-model.

Per the Person 4 brief: the LLM is handed the COMPLETE actual prediction plus
the score definition at inference time, because the training data does not yet
teach prediction interpretation. `build_context()` is that structured payload.
"""
from __future__ import annotations
import json, hashlib

import config.settings as S


class LLMService:
    def __init__(self):
        # Adaption Responses API (Person 1) — the PRIMARY real path. The served
        # fine-tuned model is referenced as "stack:<slug>".
        self.adaption_key = S.env(S.ENV_ADAPTION_API_KEY)
        # Prefer ADAPTION_STACK; fall back to the legacy ADAPTION_MODEL_ID slug.
        self.adaption_stack = S.env(S.ENV_ADAPTION_STACK) or S.env(S.ENV_ADAPTION_MODEL)
        self.adaption_base = S.env(S.ENV_ADAPTION_BASE_URL) or S.ADAPTION_DEFAULT_BASE_URL
        self._adaption_ready = bool(self.adaption_key and self.adaption_stack)

        # Generic OpenAI-compatible endpoint — SECONDARY real path. A full trio
        # is required (a hosted endpoint has no built-in default base url).
        self.openai_base = S.env(S.ENV_OPENAI_BASE_URL)
        self.openai_key = S.env(S.ENV_OPENAI_API_KEY)
        self.openai_model = S.env(S.ENV_OPENAI_MODEL)
        self._openai_ready = bool(self.openai_base and self.openai_key and self.openai_model)

        # Adaption takes precedence when both are configured.
        if self._adaption_ready:
            self.provider = "adaption"
            self.model_id = f"stack:{self.adaption_stack}"
        elif self._openai_ready:
            self.provider = "openai"
            self.model_id = self.openai_model
        else:
            self.provider = None
            self.model_id = None

        self.real_mode = self._adaption_ready or self._openai_ready

        # Context-keyed disk cache of REAL model outputs. A local fine-tuned model
        # can be slow (tens of seconds); caching makes a re-run of the same pair
        # instant for the demo. The cache stores the model's OWN output verbatim —
        # it is never fabricated, and the key includes the full context, so if any
        # input changes (e.g. Boltz goes mock->real) it regenerates.
        self._cache_dir = S.APP_DIR / ".llm_cache"

    # ------------------------------------------------------------------ cache
    def _cache_key(self, ctx: dict) -> str:
        blob = json.dumps({"p": self.provider, "m": self.model_id, "ctx": ctx},
                          sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:24]

    def _cache_get(self, ctx: dict):
        try:
            f = self._cache_dir / f"{self._cache_key(ctx)}.json"
            if f.exists():
                rep = json.loads(f.read_text())
                rep["_cached"] = True
                return rep
        except Exception:
            pass
        return None

    def _cache_put(self, ctx: dict, rep: dict):
        try:
            self._cache_dir.mkdir(exist_ok=True)
            (self._cache_dir / f"{self._cache_key(ctx)}.json").write_text(json.dumps(rep))
        except Exception:
            pass

    def mode_label(self) -> str:
        if self.provider == "adaption":
            return f"REAL (Adaption {self.model_id})"
        if self.provider == "openai":
            return f"REAL ({self.model_id})"
        return "MOCK (grounded template)"

    # ------------------------------------------------------------------ context
    def build_context(self, mutation, compound, boltz_predictions, experimental_evidence,
                      measurements, data_service) -> dict:
        """The exact structured payload the model receives. Real numbers only."""
        meas = [{
            "measurement_id": m.get("measurement_id"),
            "measurement_type": m.get("measurement_type"),
            "value": m.get("original_value"),
            "unit": m.get("original_unit"),
            "relation": m.get("measurement_relation"),
            "assay_type": m.get("assay_type"),
            "source": m.get("publication") or m.get("source_database"),
        } for m in (measurements or [])][:12]  # cap: keep the prompt (and latency) bounded
        return {
            "score_definition": S.SCORE_DEFINITION,
            "mutation": {
                "mutation_id": mutation.get("mutation_id"),
                "notation": mutation.get("mutation_notation"),
                "type": mutation.get("mutation_type"),
                "domain": mutation.get("protein_domain"),
                "known_mechanism": mutation.get("known_mechanism"),
                "resistance_association": mutation.get("resistance_association"),
                "classification": mutation.get("mutation_classification"),
            } if mutation else None,
            "compound": {
                "compound_id": compound.get("compound_id"),
                "name": compound.get("compound_name"),
                "drug_class": compound.get("drug_class"),
                "covalent_status": compound.get("covalent_status"),
                "warhead_type": compound.get("warhead_type"),
            } if compound else None,
            "boltz_predictions": boltz_predictions or [],
            "experimental_measurements": meas,
            "experimental_evidence": [
                {"claim": e["claim"], "evidence_type": e["evidence_type"],
                 "assay_type": e.get("assay_type"), "pmid": e.get("pmid"),
                 "doi": e.get("doi"), "source_title": e.get("source_title")}
                for e in (experimental_evidence or [])[:10]
            ],
        }

    # ------------------------------------------------------------------ generate
    def generate(self, mutation, compound, boltz_predictions, experimental_evidence,
                 measurements, data_service) -> dict:
        ctx = self.build_context(mutation, compound, boltz_predictions,
                                 experimental_evidence, measurements, data_service)
        if self.real_mode:
            cached = self._cache_get(ctx)
            if cached is not None:
                return cached
            try:
                if self.provider == "adaption":
                    rep = self._generate_real_adaption(ctx)
                else:
                    rep = self._generate_real_openai(ctx)
                self._cache_put(ctx, rep)
                return rep
            except Exception as e:  # never break the demo; fall back and say so
                rep = self._generate_template(ctx)
                rep["is_mock"] = True
                rep["model"] = f"{self.model_id} (call failed: {e}) — fell back to template"
                return rep
        return self._generate_template(ctx)

    # The persona / system instructions, shared by both real providers. It forbids
    # fabricated numbers, mechanisms and citations.
    _SYSTEM = (
        "You are MutationScientist, an evidence-grounded EGFR/NSCLC research "
        "assistant. Use ONLY the supplied context. Never invent numbers, "
        "mechanisms or citations. Keep biochemical affinity, cellular assays "
        "and clinical response distinct. Respect the score definition exactly. "
        "Separate established mechanism from computational prediction, and label "
        "uncertainty. Not for clinical decisions."
    )

    def _user_text(self, ctx: dict) -> str:
        return ("CONTEXT:\n" + json.dumps(ctx, indent=2) +
                "\n\nWrite the structured research report.")

    def _generate_real_adaption(self, ctx: dict) -> dict:
        """PRIMARY: Adaption Responses API (POST {base}/api/v1/responses)."""
        import urllib.request
        url = self.adaption_base.rstrip("/") + "/api/v1/responses"
        body = json.dumps({
            "model": f"stack:{self.adaption_stack}",
            "input": self._user_text(ctx),
            "instructions": self._SYSTEM,
            "temperature": 0.2,
            "max_output_tokens": 800,
        }).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {self.adaption_key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=360) as resp:
            out = json.loads(resp.read())
        text = out.get("output_text") or self._extract_output_text(out)
        if not text:
            raise ValueError("Adaption response had no output_text")
        return {"is_mock": False, "model": self.model_id, "context": ctx,
                "report_markdown": text, "sections": None}

    @staticmethod
    def _extract_output_text(out: dict) -> str:
        """Fallback for the Responses API: concatenate output[].content[].text."""
        chunks = []
        for item in out.get("output", []) or []:
            for c in (item.get("content") if isinstance(item, dict) else None) or []:
                t = c.get("text") if isinstance(c, dict) else None
                if t:
                    chunks.append(t)
        return "\n".join(chunks)

    def _generate_real_openai(self, ctx: dict) -> dict:
        """SECONDARY: generic OpenAI-compatible /chat/completions endpoint."""
        import urllib.request
        url = self.openai_base.rstrip("/") + "/chat/completions"
        body = json.dumps({
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": self._SYSTEM},
                {"role": "user", "content": self._user_text(ctx)},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=360) as resp:
            out = json.loads(resp.read())
        text = out["choices"][0]["message"]["content"]
        return {"is_mock": False, "model": self.model_id, "context": ctx,
                "report_markdown": text, "sections": None}

    # ------------------------------------------------------------------ template
    def _generate_template(self, ctx: dict) -> dict:
        mut = ctx["mutation"] or {}
        cmp_ = ctx["compound"] or {}
        preds = ctx["boltz_predictions"]
        meas = ctx["experimental_measurements"]
        ev = ctx["experimental_evidence"]
        any_mock_pred = any(p.get("is_mock") for p in preds)

        def mech(v):
            return v.strip().rstrip(".") if v and v.strip() else "not annotated in the dataset for this variant"

        sections = {}

        # 1. Mutation explanation (established)
        sections["Mutation"] = (
            f"**{mut.get('mutation_id','?')}** ({mut.get('notation') or 'profile'}), "
            f"type *{mut.get('type') or 'n/a'}*, in the *{mut.get('domain') or 'n/a'}*. "
            f"Classification: {mut.get('classification') or 'n/a'}. "
            f"Known mechanism (established): {mech(mut.get('known_mechanism'))}. "
            f"Resistance association: {mut.get('resistance_association') or 'none recorded'}."
        )

        # 2. Compound
        cov = cmp_.get("covalent_status") or "unknown"
        is_cov = S.is_covalent(cov)
        inhibitor_line = (
            f"**{cmp_.get('name') or cmp_.get('compound_id','?')}** — class "
            f"{cmp_.get('drug_class') or 'n/a'}; covalent status: **{cov}**"
        )
        if cmp_.get("warhead_type"):
            inhibitor_line += f" (warhead: {cmp_.get('warhead_type')})"
        inhibitor_line += "."
        if is_cov:
            inhibitor_line += (" Covalent inhibitors have time-dependent inhibition that "
                               "conventional equilibrium affinity does not fully capture.")
        sections["Inhibitor"] = inhibitor_line

        # 3. Computational prediction (clearly separated, flagged if mock)
        if preds:
            lines = []
            for p in preds:
                tag = " _(MOCK placeholder — not a real prediction)_" if p.get("is_mock") else ""
                lines.append(
                    f"- `{p['complex_id']}` [{p['model_checkpoint']}]: "
                    f"affinity_pred_value = **{p['affinity_pred_value']}** "
                    f"({S.BOLTZ_LABEL_UNIT}, lower=stronger), "
                    f"binder prob = {p.get('affinity_probability_binary')}{tag}"
                )
            sections["Computational prediction (Boltz-2)"] = (
                ("> ⚠️ These values are MOCK placeholders for interface demo only.\n\n" if any_mock_pred else "")
                + "\n".join(lines)
                + f"\n\n_Score convention:_ {ctx['score_definition']}"
            )
        else:
            sections["Computational prediction (Boltz-2)"] = (
                "No Boltz complex exists for this mutation–inhibitor pair in the dataset, "
                "so no prediction is shown (not fabricated)."
            )

        # 4. Experimental evidence (established, cited)
        if meas or ev:
            parts = []
            for m in meas[:8]:
                rel = m["relation"] if m["relation"] and m["relation"] != "=" else ""
                parts.append(
                    f"- {m['measurement_type']} {rel}{m['value']} {m['unit']} "
                    f"({m['assay_type'] or 'assay n/a'}; {m['source'] or 'source n/a'})"
                )
            for e in ev[:8]:
                cite = e.get("pmid") and f"PMID:{e['pmid']}" or (e.get("doi") and f"DOI:{e['doi']}") or ""
                parts.append(f"- {e['claim']} ({e['evidence_type']}; {cite})")
            sections["Experimental evidence (established)"] = "\n".join(parts)
        else:
            sections["Experimental evidence (established)"] = \
                "No curated measurement or evidence row matched this pair."

        # 5. Resistance implications
        sections["Potential resistance implications"] = (
            f"{mut.get('resistance_association') or 'No resistance association is recorded for this variant.'} "
            "Interpretation of affinity shifts must separate biochemical binding from cellular/clinical response."
        )

        # 6. Confidence & uncertainties
        caveats = [
            "Predicted binding affinity ≠ enzyme inhibition, cell killing, or clinical efficacy.",
            "KD, Ki and IC50 are distinct; biochemical and cellular measurements are not interchangeable.",
        ]
        if is_cov:
            caveats.append("Covalent kinetics are not fully represented by equilibrium affinity.")
        if any_mock_pred:
            caveats.append("Boltz values above are MOCK placeholders, not model outputs.")
        caveats.append("This report is a grounded TEMPLATE, not the fine-tuned MutationScientist model.")
        sections["Confidence & uncertainties"] = "\n".join(f"- {c}" for c in caveats)

        # 7. Suggested validation experiments (generic, appropriate)
        sections["Suggested validation experiments"] = "\n".join([
            "- Biochemical kinase IC50 at Km,ATP for this mutant construct vs WT (dose–response).",
            "- Cellular viability / pEGFR assay in an isogenic line carrying the variant.",
            "- Where covalency is relevant, time-dependent / jump-dilution assays.",
            "- If a structure is available, inspect the binding pocket around the mutated residue.",
        ])

        # 8. References
        refs = []
        for e in ev:
            if e.get("pmid"):
                refs.append(f"- PMID:{e['pmid']} — {e.get('source_title','')}")
            elif e.get("doi"):
                refs.append(f"- DOI:{e['doi']} — {e.get('source_title','')}")
        sections["References"] = "\n".join(dict.fromkeys(refs)) or "- (none matched)"

        md = "\n\n".join(f"### {k}\n{v}" for k, v in sections.items())
        return {"is_mock": True, "model": "grounded template (not the fine-tuned model)",
                "context": ctx, "sections": sections, "report_markdown": md}
