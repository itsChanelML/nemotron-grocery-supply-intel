from typing import Optional
# backend/agents/document.py
# Document Agent — BOL & Invoice RAG Intelligence
#
# Models:
#   nvidia/nemotron-3-embed-1b — embedding (NeMo Retriever pattern)
#   nvidia/nemotron-3-super-120b-a12b — grounded generation
# Temperature: 0.1
#
# Why two models:
#   1. nv-embedqa converts BOL/invoice text chunks into dense vectors.
#      At query time, the query is embedded with the same model and
#      we find the nearest document chunks (semantic search).
#   2. Nemotron 3 Super 120B takes retrieved chunks + query and generates a
#      grounded answer. The 120B model is required here because document
#      intelligence involves cross-referencing multiple records
#      (BOL qty vs invoice qty vs PO lot number) — smaller models
#      hallucinate on multi-document reasoning tasks.
#
# Pipeline: PDF → Cloud Storage → Document AI → nv-embedqa → BigQuery
#           → vector search → top-k chunks → Nemotron generation

from lib.nim import NEMOTRON_LARGE, NV_EMBED


DOCUMENT_AGENT = {
    "id": "document",
    "name": "Document Agent",
    "role": "BOL & Invoice RAG Intelligence",
    "model": NEMOTRON_LARGE,
    "embedding_model": NV_EMBED,
    "temperature": 0.1,
}


def build_system_prompt(documents: Optional[dict] = None, retrieved_chunks: Optional[list] = None) -> str:
    """
    Build the Document Agent system prompt.
    Injects retrieved RAG chunks when available.
    """
    doc_section = ""
    if retrieved_chunks:
        import json
        doc_section = f"""
## Retrieved Document Context (from BigQuery vector search — NeMo Retriever pattern)
{json.dumps(retrieved_chunks, indent=2, default=str)}
"""
    else:
        doc_section = """
## Document Corpus — Last 72 Hours (Synthetic — Demo Mode)
47 BOLs received · 3 discrepancies flagged · 12 invoices pending 3-way match

BOL #74808 | Vendor: Fresh Express | 2 days ago
  Product: Romaine Lettuce (bagged) | Lot: #RLT-2024-0891
  Status: QUARANTINED — matches active FDA Class II recall F-2024-0033

BOL #74821 | Vendor: Del Monte | 2 days ago
  Invoiced: 480 cases roma tomatoes | Received: 462 cases | Delta: -18 cases (~$340)
  Status: DISPUTED — quantity discrepancy, vendor dispute workflow opened

BOL #74839 | Vendor: Tyson Foods | Yesterday
  Cold chain shipment — temperature log: MISSING
  Status: FLAGGED — FDA 21 CFR 117 non-compliance risk

BOL #74851 | Vendor: Dole | Today
  Lot on BOL: #DL-0442 | Lot on PO: #DL-0441
  Status: FLAGGED — lot number mismatch, hold pending vendor confirmation

Pending 3-way match: 12 invoices | Oldest: 8 days (Sysco)
Vendor SLA breach: Chobani on-time delivery 78% vs 85% SLA (30-day avg)
"""

    return f"""You are the Document Agent for Orchaid — an NVIDIA NIM-powered logistics
document intelligence agent for the Stater Bros. Distribution Center,
San Bernardino, CA.

You run on nvidia/nemotron-3-super-120b-a12b via NVIDIA NIM microservices,
with nvidia/nemotron-3-embed-1b for semantic vector search.

You use a Hybrid RAG pipeline built on the NeMo Retriever pattern:
- Google Cloud Document AI extracts structured data from BOL/invoice PDFs
- Google Cloud Storage archives raw documents
- NVIDIA NV-EmbedQA generates dense vectors
- BigQuery stores and searches the vector index
- Nemotron 3 Super 120B generates grounded answers from retrieved chunks

You ONLY answer based on what has been retrieved from the vector index.
If a document is not in the corpus, say so explicitly — never hallucinate.

{doc_section}

## Response Guidelines
- Always cite document numbers (BOL #, Invoice #, PO #)
- State the dollar value of discrepancies where calculable
- Distinguish "dispute with vendor" vs "quarantine immediately"
- If a document is not in the corpus: "Not found — please upload for Document AI processing"
- Surface patterns across documents (e.g., recurring vendor discrepancies)
""".strip()
