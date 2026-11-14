import json
import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.error import URLError

from application.app import serve
from application.pages.mutation_scientist import render_page
from application.services.evidence_service import answer_question
from application.services.llm_service import configured_model

QUESTION = "Why does gefitinib lose potency against T790M?"
KD_ID = "MEAS_001135"
IC50_IDS = ["MEAS_002537", "MEAS_004357", "MEAS_009896"]
MECHANISM_ID = "18227510:Tables 1–2 and Figure 3"


class ResearchReportTests(unittest.TestCase):
    def test_find_gefitinib_evidence_from_natural_question(self):
        result = answer_question(QUESTION)
        self.assertEqual(result["exact_measurement_count"], 4)
        direct = result["evidence"]
        self.assertEqual([row["evidence_id"] for row in direct], [KD_ID, *IC50_IDS])
        self.assertTrue(all(row["compound_id"] == "BDB_5447" for row in direct))
        self.assertEqual(direct[0]["details"]["value"], "4.6")
        self.assertEqual(direct[0]["details"]["measurement_type"], "KD")
        self.assertEqual(direct[0]["assay_type"], "biochemical_binding")
        self.assertTrue(all(row["assay_type"] == "unspecified" for row in direct[1:]))
        self.assertIn(MECHANISM_ID, {row["evidence_id"] for row in result["claims"]})

    def test_model_prompt_and_rendered_citations(self):
        def model(messages):
            packet = json.loads(messages[-1]["content"])
            self.assertEqual(packet["question"], QUESTION)
            records = {row["evidence_id"]: row for row in packet["records"]}
            self.assertEqual(records[KD_ID]["details"]["measurement_type"], "KD")
            self.assertEqual(records[IC50_IDS[0]]["details"]["measurement_type"], "IC50")
            self.assertEqual(records[MECHANISM_ID]["profile_id"], "PROF_L858R_T790M")
            self.assertEqual(records[MECHANISM_ID]["match_scope"], "related_profile")
            self.assertNotIn("EVIDENCE_00009", records)
            self.assertTrue(all(row["compound_id"] in {"CMP_GEFITINIB", "BDB_5447", None}
                                for row in records.values()))
            return json.dumps({"evidence_ids": [MECHANISM_ID, KD_ID, *IC50_IDS]})

        result = answer_question(QUESTION, generate=model, model_id="test-model")
        self.assertEqual(result["status"], "model_selected_evidence")
        self.assertEqual([row["evidence_id"] for row in result["claims"]], [MECHANISM_ID, KD_ID, *IC50_IDS])
        html = render_page(QUESTION, report=result)
        self.assertIn('href="https://doi.org/10.1073/pnas.0709662105"', html)
        self.assertIn("Related profile · Enzyme inhibition · EGFR_L858R_T790M", html)
        self.assertIn("KD = 4.6 nM", html)
        self.assertIn("IC50 = 280.0 nM", html)

    def test_model_rejects_unretrieved_existing_id_and_arbitrary_claim(self):
        for payload in (
            {"evidence_ids": ["MEAS_000006"]},
            {"evidence_ids": [KD_ID], "claim": "Gefitinib has proven clinical efficacy."},
            {"evidence_ids": [KD_ID, KD_ID]},
        ):
            with self.subTest(payload=payload):
                result = answer_question(QUESTION, generate=lambda _: json.dumps(payload))
                self.assertEqual(result["status"], "local_evidence_summary")
                self.assertIn("failed citation validation", result["model_notice"])
                self.assertNotIn("MEAS_000006", {row["evidence_id"] for row in result["claims"]})

    def test_exact_pair_has_no_measurement_and_related_profile_keeps_genotype(self):
        question = "Why does osimertinib lose potency against C797S?"
        result = answer_question(question)
        self.assertEqual(result["exact_measurement_count"], 0)
        self.assertIn("MEAS_000006", {row["evidence_id"] for row in result["claims"]})
        related = next(row for row in result["claims"] if row["evidence_id"] == "MEAS_000006")
        self.assertEqual(related["mutation_id"], "EGFR_L858R_C797S")
        self.assertEqual(related["match_scope"], "related_profile")
        self.assertIn("No exact-pair experimental measurement", render_page(question, report=result))

    def test_empty_exact_pair_preserves_entity_background(self):
        result = answer_question("Any measurements for C797S and erlotinib?")
        self.assertEqual(result["exact_measurement_count"], 0)
        self.assertEqual(result["total_matches"], 0)
        self.assertTrue(result["claims"])
        self.assertTrue(all(row["match_scope"] == "entity_context" for row in result["claims"]))

    def test_profile_alias_and_cellular_endpoint(self):
        result = answer_question("What is the cellular viability IC₅₀ for AZD9291 with L858R + T790M + C797S?")
        self.assertEqual(result["lookup"]["mutation_profile"], "PROF_L858R_T790M_C797S")
        self.assertEqual(result["lookup"]["compound_id"], "CMP_OSIMERTINIB")
        self.assertEqual(result["exact_measurement_count"], 3)
        self.assertEqual({row["details"]["value"] for row in result["claims"]}, {"2950", "3550", "3860"})
        self.assertTrue(all(row["assay_type"] == "cellular_viability" for row in result["claims"]))

    def test_publication_filter_and_compound_synonym(self):
        result = answer_question("What direct binding KD does Iressa have for EGFR_T790M in PMID 18227510?")
        self.assertEqual([row["evidence_id"] for row in result["evidence"]], [KD_ID])
        self.assertEqual(result["exact_measurement_count"], 1)

    def test_unknown_entities_and_oversized_comparisons_fail(self):
        for question in ("Compare S768I, L861Q, T790M and C797S", "What is the effect of imatinib on T790M?"):
            with self.subTest(question=question), self.assertRaises(ValueError):
                answer_question(question)

    def test_multi_variant_clinical_and_binding_results_remain_scoped(self):
        report = answer_question("Compare the clinical response to osimertinib in S768I and L861Q.")
        self.assertEqual(len(report["lookup"]["comparisons"]), 2)
        self.assertEqual({row["evidence_id"] for row in report["claims"]},
                         {"31825714:Table 2 S768I", "31825714:Table 2 L861Q"})
        report = answer_question("Compare gefitinib KD and IC50s for T790M.")
        self.assertEqual(report["exact_measurement_count"], 4)
        self.assertEqual({row["details"]["measurement_type"] for row in report["evidence"]}, {"KD", "IC50"})

    def test_clinical_sources_keep_trial_populations_and_comparators(self):
        question = "Compare the clinical response to osimertinib and afatinib in S768I and L861Q."
        report = answer_question(question)
        self.assertEqual({row["pmid"] for row in report["claims"]}, {"31825714", "26051236"})
        self.assertEqual(len(report["claims"]), 4)
        self.assertIn("evaluated in separate studies", render_page(question, report=report))
        aura3 = answer_question("What was the PFS on osimertinib in AURA3 for T790M?")
        self.assertEqual(aura3["claims"][0]["evidence_id"], "27959700:AURA3 efficacy")
        self.assertEqual(aura3["claims"][0]["details"]["comparator"], "platinum–pemetrexed")

    def test_new_cellular_source_rows_retain_clones_and_assay(self):
        report = answer_question("Compare BLU-945 and JBJ-09-063 viability IC50 in L858R/T790M/C797S.")
        self.assertEqual([pair["count"] for pair in report["measurement_coverage"]], [3, 3])
        self.assertEqual({r["details"]["value"] for r in report["claims"]},
                         {"109", "123", "116", "8.64", "4.68", "33.8"})
        self.assertTrue(all(r["assay_type"] == "cellular_viability" for r in report["claims"]))

    def test_specified_clone_is_exact_and_an_unreported_clone_abstains(self):
        question = "Find BLU-945 cellular viability for clone {} of NCI-H1975 with L858R/T790M/C797S."
        actual = answer_question(question.format(2))
        self.assertEqual(actual["exact_measurement_count"], 1)
        self.assertEqual([row["details"]["cell_line"] for row in actual["claims"]], ["NCI-H1975 clone 2"])
        missing = answer_question(question.format(4))
        self.assertEqual(missing["exact_measurement_count"], 0)
        self.assertEqual(missing["claims"], [])

    def test_specified_atp_condition_filters_enzyme_measurements(self):
        question = "What enzyme IC50 did BLU-945 give for L858R/C797S with {}?"
        for condition, eid in (("ATP set to Km", "MEAS_000015"), ("1 mM ATP", "MEAS_000051")):
            with self.subTest(condition=condition):
                report = answer_question(question.format(condition))
                self.assertEqual(report["exact_measurement_count"], 1)
                self.assertEqual([row["evidence_id"] for row in report["claims"]], [eid])

    def test_mutation_description_surfaces_classification(self):
        report = answer_question("Explain the residue change and structural class of S768I.")
        self.assertEqual(report["claims"][0]["evidence_id"], "EGFR_S768I")
        self.assertIn("34526717:S768I PACC", {row["evidence_id"] for row in report["claims"]})

    def test_censored_comparison_surfaces_matching_values_and_bound(self):
        question = "For L858R/C797S, compare 574 nM and >10,000 nM. What is the fold change?"
        report = answer_question(question)
        self.assertEqual([row["evidence_id"] for row in report["evidence"][:2]], ["MEAS_000006", "MEAS_000042"])
        self.assertIn("More than 17.4-fold", render_page(question, report=report))

    def test_model_scale_calculation_is_labeled_and_linked(self):
        question = "For S768I, interpret Boltz-2 affinity_pred_value = -2."
        report = answer_question(question)
        self.assertIn("0.01 µM (10 nM)", report["interpretation"][0]["text"])
        self.assertIn("predicted IC50-scale", report["interpretation"][0]["text"])
        self.assertIn("Boltz-2 prediction documentation", render_page(question, report=report))

    def test_clone_shift_uses_cellular_pairs_and_cites_each_record(self):
        report = answer_question(
            "Describe osimertinib viability in parental NCI-H1975 cells and C797S clones. "
            "Give the range of shifts."
        )
        self.assertEqual([pair["count"] for pair in report["measurement_coverage"]], [1, 3])
        self.assertTrue(all(row["assay_type"] == "cellular_viability" for row in report["claims"]))
        self.assertIn("252–330-fold", report["interpretation"][0]["text"])
        self.assertEqual(len(report["interpretation"][0]["evidence_ids"]), 4)

    def test_define_endpoints_without_arbitrary_measurement_examples(self):
        report = answer_question("Why must KD, Ki and IC50 not be pooled?")
        self.assertEqual(report["evidence"], [])
        self.assertIn("equilibrium binding", report["interpretation"][0]["text"])
        self.assertEqual(report["interpretation"][0]["source_url"], "https://pubmed.ncbi.nlm.nih.gov/4202581/")

    def test_model_http_protocols(self):
        for protocol, response in (
            ("chat", {"choices": [{"message": {"content": '{"evidence_ids":["MEAS_001135"]}'}}]}),
            ("responses", {"output": [{"type": "message", "content": [
                {"type": "output_text", "text": '{"evidence_ids":["MEAS_001135"]}'},
            ]}]}),
        ):
            with self.subTest(protocol=protocol), patch.dict(os.environ, {
                "MUTATIONSCIENTIST_LLM_URL": "http://127.0.0.1:9090/model",
                "MUTATIONSCIENTIST_LLM_MODEL": "test-model",
                "MUTATIONSCIENTIST_LLM_PROTOCOL": protocol,
                "MUTATIONSCIENTIST_LLM_API_KEY": "test-key",
            }), patch("application.services.llm_service.build_opener") as opener:
                client = opener.return_value
                client.open.return_value.__enter__.return_value.read.return_value = json.dumps(response).encode()
                generate, model_id = configured_model()
                result = answer_question(QUESTION, generate=generate, model_id=model_id)
                request = client.open.call_args.args[0]
                body = json.loads(request.data)
                messages = body["messages" if protocol == "chat" else "input"]
                self.assertEqual(json.loads(messages[-1]["content"])["question"], QUESTION)
                self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
                self.assertEqual(result["claims"][0]["evidence_id"], KD_ID)

    def test_web_form_posts_through_model_and_retriever(self):
        class InProcessServer:
            server_port = 8765

            def __init__(self, address, handler):
                self.handler = handler

            def serve_forever(self):
                from io import BytesIO

                form = urlencode({"question": QUESTION}).encode()
                request = self.handler.__new__(self.handler)
                request.path = "/"
                request.headers = {"Content-Length": str(len(form))}
                request.rfile = BytesIO(form)
                request.respond = lambda status, html: rendered.append((status, html))
                request.do_POST()

        @contextmanager
        def server(address, handler):
            yield InProcessServer(address, handler)

        rendered = []
        with patch("application.app.ThreadingHTTPServer", server), patch("builtins.print"):
            serve(8765, lambda _: json.dumps({"evidence_ids": [KD_ID]}), "test-model")
        status, html = rendered[0]
        self.assertEqual(status, 200)
        self.assertIn("Model-selected evidence · test-model", html)
        self.assertIn("KD = 4.6 nM", html)

    def test_endpoint_failure_keeps_real_evidence_available(self):
        with patch.dict(os.environ, {
            "MUTATIONSCIENTIST_LLM_URL": "http://127.0.0.1:9090/model",
            "MUTATIONSCIENTIST_LLM_MODEL": "test-model",
            "MUTATIONSCIENTIST_LLM_PROTOCOL": "chat",
        }), patch("application.services.llm_service.build_opener") as opener:
            opener.return_value.open.side_effect = URLError("unavailable")
            generate, model_id = configured_model()
            result = answer_question(QUESTION, generate=generate, model_id=model_id)
        self.assertEqual(result["status"], "local_evidence_summary")
        self.assertIn("endpoint unavailable", result["model_notice"])
        self.assertEqual(result["claims"][0]["evidence_id"], KD_ID)


if __name__ == "__main__":
    unittest.main()
