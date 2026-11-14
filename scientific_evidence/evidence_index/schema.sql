CREATE TABLE evidence (
    row_id INTEGER PRIMARY KEY,
    evidence_id TEXT NOT NULL UNIQUE,
    mutation_id TEXT,
    profile_id TEXT,
    compound_id TEXT,
    evidence_type TEXT NOT NULL,
    assay_type TEXT,
    evidence_category TEXT NOT NULL,
    cancer_context TEXT,
    pmid TEXT,
    doi TEXT,
    priority INTEGER NOT NULL,
    payload TEXT NOT NULL,
    search_text TEXT NOT NULL
);
CREATE TABLE profile_components (
    component_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    PRIMARY KEY (component_id, profile_id)
);
CREATE TABLE aliases (
    kind TEXT NOT NULL,
    alias TEXT NOT NULL,
    canonical_id TEXT NOT NULL,
    PRIMARY KEY (kind, alias)
);
CREATE TABLE compound_equivalents (
    compound_id TEXT NOT NULL,
    equivalent_id TEXT NOT NULL,
    PRIMARY KEY (compound_id, equivalent_id)
);
CREATE TABLE coverage (
    mutation_id TEXT NOT NULL,
    compound_id TEXT NOT NULL,
    spread_json TEXT NOT NULL,
    PRIMARY KEY (mutation_id, compound_id)
);
CREATE INDEX evidence_mutation ON evidence(mutation_id);
CREATE INDEX evidence_profile ON evidence(profile_id);
CREATE INDEX evidence_compound ON evidence(compound_id);
CREATE INDEX evidence_pmid ON evidence(pmid);
CREATE INDEX evidence_doi ON evidence(doi);
CREATE VIRTUAL TABLE search USING fts5(search_text, content='evidence', content_rowid='row_id');
