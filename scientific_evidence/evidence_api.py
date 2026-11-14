"""Public in-process retrieval interface for MutationScientist."""

from .retriever.search import retrieve as retrieve_evidence

__all__ = ["retrieve_evidence"]
