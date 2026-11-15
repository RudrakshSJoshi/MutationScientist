import unittest

from application.pages.mutation_scientist import render_page
from scientific_evidence.evidence_api import search_graph


class EvidenceGraphTests(unittest.TestCase):
    def test_protein_aliases_share_the_canonical_graph(self):
        expected = search_graph("EGFR", limit=2)
        self.assertEqual(expected["anchors"], ["protein:P00533"])
        self.assertGreater(expected["total_matches"], 2)
        self.assertTrue({"Variants", "Inhibitors", "Assays"} <= expected["browse"].keys())
        for query in ("ERBB1", "HER-1", "P00533-1", "epidermal growth factor receptor"):
            with self.subTest(query=query):
                other = search_graph(query, limit=2)
                for key in ("anchors", "total_matches", "evidence"):
                    self.assertEqual(other[key], expected[key])
        self.assertEqual(search_graph("HER2")["evidence"], [])
        self.assertEqual(search_graph("EGFR P04626")["evidence"], [])

    def test_variant_expansion_keeps_compound_endpoint_and_profile_scope(self):
        graph = search_graph("ERBB-1 T790M Iressa KD")
        evidence = {row["evidence_id"]: row for row in graph["evidence"]}
        self.assertEqual(set(evidence), {"MEAS_001135", "MEAS_001139"})
        self.assertEqual(evidence["MEAS_001135"]["match_scope"], "direct")
        self.assertEqual(evidence["MEAS_001139"]["match_scope"], "related_profile")
        self.assertTrue(all(row["compound_id"] == "BDB_5447" for row in evidence.values()))
        self.assertIn(
            {"from": "mutation:EGFR_T790M", "relation": "part_of_profile",
             "to": "profile:PROF_L858R_T790M", "evidence_id": "PROF_L858R_T790M"},
            graph["edges"],
        )
        self.assertTrue(any(
            edge["relation"] == "same_compound_as" and edge["to"] == "compound:CMP_GEFITINIB"
            for edge in graph["edges"]
        ))
        nodes = {node["id"] for node in graph["nodes"]}
        self.assertTrue(all(edge["from"] in nodes and edge["to"] in nodes for edge in graph["edges"]))

    def test_explicit_profile_does_not_expand_to_other_genotypes(self):
        graph = search_graph("L858R/T790M gefitinib KD")
        self.assertEqual([row["evidence_id"] for row in graph["evidence"]], ["MEAS_001139"])
        self.assertEqual(graph["evidence"][0]["match_scope"], "direct")

    def test_structure_citation_and_keyword_routes(self):
        structure = search_graph("EGFR PDB 6LUD")
        self.assertEqual([row["evidence_id"] for row in structure["evidence"]], ["6LUD:experimental data"])
        self.assertIn("structure:6LUD", structure["anchors"])
        publication = search_graph("PMID:18227510")
        self.assertTrue(publication["evidence"])
        self.assertTrue(all(row["pmid"] == "18227510" for row in publication["evidence"]))
        self.assertTrue(search_graph("gatekeeper resistance")["evidence"])
        inhibition = search_graph("EGFR Ki", limit=3)
        self.assertTrue(inhibition["evidence"])
        self.assertTrue(all(row["details"]["measurement_type"] == "Ki" for row in inhibition["evidence"]))

    def test_graph_page_renders_links_and_actual_related_profile(self):
        graph = search_graph("EGFR", limit=2)
        html = render_page("EGFR", graph=graph)
        self.assertIn("Graph search results", html)
        self.assertIn("/?graph=P00533+EGFR_T790M&amp;offset=0", html)
        self.assertIn("/?graph=EGFR&amp;offset=2", html)
        following = search_graph("EGFR", limit=2, offset=2)
        self.assertNotEqual(graph["evidence"], following["evidence"])

        comparison = search_graph("C797S AZD9291 cellular viability")
        html = render_page(comparison["keywords"], graph=comparison)
        self.assertIn(">EGFR_C797S</a> is part of ", html)
        self.assertIn("/?graph=PROF_L858R_T790M_C797S&amp;offset=0", html)
        self.assertIn("assay_type=cellular_viability", html)
        self.assertIn("Source for SOURCE_MELIS:", html)
        self.assertTrue(all(row["match_scope"] == "related_profile" for row in comparison["evidence"]))

    def test_exact_only_and_assay_filters_do_not_relabel_related_evidence(self):
        graph = search_graph("EGFR T790M gefitinib", exact_only=True, assay_type="biochemical_binding")
        self.assertEqual([row["evidence_id"] for row in graph["evidence"]], ["MEAS_001135"])
        html = render_page(graph["keywords"], graph=graph)
        self.assertIn('name="exact_only" value="1" checked', html)
        self.assertIn('value="biochemical_binding" selected', html)
        empty = search_graph("C797S osimertinib", exact_only=True, assay_type="cellular_viability")
        self.assertEqual(empty["total_matches"], 0)
        self.assertEqual(empty["evidence"], [])

    def test_condition_and_clone_filters_are_exact(self):
        high = search_graph("L858R/C797S osimertinib", atp_condition="1 mmol/L ATP")
        self.assertEqual([row["evidence_id"] for row in high["evidence"]], ["MEAS_000042"])
        self.assertEqual(high["evidence"][0]["details"]["relation"], ">")
        clone = search_graph("C797S osimertinib", cell_line="NCI-H1975 clone 2")
        self.assertEqual(len(clone["evidence"]), 1)
        self.assertIn("clone 2", clone["evidence"][0]["evidence_id"])
        self.assertEqual(search_graph("C797S osimertinib", cell_line="NCI-H1975 clone 4")["total_matches"], 0)

    def test_bounded_query_rejects_invalid_controls(self):
        for params in ({"limit": 0}, {"limit": 51}, {"offset": -1}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                search_graph("EGFR", **params)
        self.assertEqual(search_graph("EGFR OR * outsideindex")["evidence"], [])


if __name__ == "__main__":
    unittest.main()
