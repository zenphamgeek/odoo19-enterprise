import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MODULE = Path(__file__).resolve().parents[1]
DOCS = MODULE / "docs/tests"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    approval = json.loads((DOCS / "qa_baseline_approval.json").read_text())
    result_path = ROOT / approval["source"]["development_result_path"]
    corpus_path = ROOT / approval["source"]["synthetic_corpus_path"]
    workbook_path = ROOT / approval["source"]["workbook_path"]
    result, corpus = json.loads(result_path.read_text()), json.loads(corpus_path.read_text())
    assert approval["independent_compliance_certification"] is False
    assert approval["formal_golden_acceptance"] is False
    assert approval["non_production"] is True
    assert result["independent_compliance_certification"] is False and result["formal_golden_acceptance"] is False and result["non_production"] is True
    assert approval["source"]["workbook_sha256"] == sha256(workbook_path) == result["source"]["workbook_sha256"]
    assert approval["source"]["synthetic_corpus_sha256"] == sha256(corpus_path) == result["source"]["corpus_file_sha256"]
    assert approval["source"]["corpus_manifest_sha256"] == corpus["manifest_sha256"] == result["source"]["corpus_manifest_sha256"]
    assert approval["source"]["development_result_sha256"] == sha256(result_path)
    assert approval["counts"]["detailed"] == {"pass": 198, "fail": 0, "mapped_only": 0, "not_runnable": 0, "skipped": 0}
    assert result["detailed_case_counts"] == {"passed": 198, "failed": 0, "not_run": 0, "skipped": 0}
    assert approval["counts"]["golden"] == {"pass": 46, "partial": 2, "fail": 0, "mapped_only": 0, "not_runnable": 0, "skipped": 0}
    assert result["golden_counts"] == {"passed": 46, "partial": 2, "failed": 0, "not_run": 0, "skipped": 0}
    assert len(corpus["cases"]) == 198 and result["document_corpus_used"] is True
    print("QA baseline approval: VALID detailed=198/198 golden=46 pass/2 partial")


if __name__ == "__main__":
    main()
