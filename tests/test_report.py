"""Stored result presentation never repeats assessment or invents evidence."""

from __future__ import annotations

import copy
import io
import json
import os
import sys
from pathlib import Path

import pytest

from hermes_rubric import AssessmentResult, CoverageReport, backends, cli
from hermes_rubric.report import main, render_markdown


@pytest.fixture
def result():
    return json.loads((Path(__file__).parent / "fixtures/report-result.json").read_text())


def test_complete_report_preserves_scores_citations_and_receipt(result):
    original = copy.deepcopy(result)
    rendered = render_markdown(result)
    assert "**Status:** complete" in rendered
    assert "**Aggregate:** 5.33 / 10.0" in rendered
    assert "### Correctness (correctness)" in rendered
    assert "**Score:** 8" in rendered
    assert "logs/staging\\.txt:12: all rows verified" in rendered
    assert "The cited log matches the answer\\." in rendered
    assert "frozen-test-backend" in rendered
    assert "2026-10-24T00:00:00Z" in rendered
    assert "frozen-rubric" in rendered
    assert result == original
    assert render_markdown(result) == rendered


def test_partial_coverage_is_visible_before_aggregate(result):
    result["coverage"].update(status="partial", visible_bytes=80, considered_sources=1,
                              limitations=["Only staging was inspected; production was omitted."])
    rendered = render_markdown(result)
    assert rendered.index("**Status:** partial") < rendered.index("**Aggregate:")
    assert "**Bytes inspected:** 80 / 100" in rendered
    assert "**Sources considered:** 1 / 2" in rendered
    assert "Only staging was inspected; production was omitted\\." in rendered
    assert "Uninspected material is not evidence" in rendered


def test_hedged_and_no_evidence_dimensions_keep_their_recorded_scores(result):
    rendered = render_markdown(result)
    coverage = rendered.split("### Coverage (coverage)")[1].split("### ")[0]
    assert "**Score:** 5" in coverage
    assert "**Hedged:** yes" in coverage
    production = rendered.split("### Production evidence (production)")[1]
    assert "**Score:** 3" in production
    assert "**Evidence found:** no" in production
    assert "No production evidence found\\." in production


def test_typed_result_matches_json_dictionary(result):
    typed = AssessmentResult(**{**result, "coverage": CoverageReport(**result["coverage"])})
    assert render_markdown(typed) == render_markdown(result)


def test_missing_legacy_coverage_and_receipt_are_not_invented(result):
    result.pop("coverage")
    result.pop("receipt")
    rendered = render_markdown(result)
    assert "unknown \\(not recorded\\)" in rendered
    assert "No receipt was recorded." in rendered
    assert "Uninspected material is not evidence" in rendered


def test_untrusted_markdown_html_and_fences_remain_literal(result):
    result["per_dim_scores"][0]["dim_name"] = "<script>bad</script> [click](javascript:x)\n# injected"
    result["receipt"]["backend"] = "```\n# forged receipt"
    rendered = render_markdown(result)
    assert "<script>" not in rendered
    assert "\\[click\\]\\(javascript:x\\)" in rendered
    assert "\n# injected" not in rendered
    assert "````json\n" in rendered
    assert rendered.endswith("\n````\n")


@pytest.mark.parametrize("field", ["aggregate", "max_possible"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, "8"])
def test_invalid_scores_are_not_presented_as_measurements(result, field, bad):
    result[field] = bad
    with pytest.raises(ValueError, match="finite numbers"):
        render_markdown(result)


def test_duplicate_dimension_evidence_is_not_silently_dropped(result):
    result["evidence_citations"].append(copy.deepcopy(result["evidence_citations"][0]))
    with pytest.raises(ValueError, match="duplicate evidence dim_id"):
        render_markdown(result)


def test_cli_dispatch_never_assesses_or_detects_backend(result, tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("render attempted a scoring/backend call")

    monkeypatch.setattr(cli, "assess_path", forbidden)
    monkeypatch.setattr(backends, "detect", forbidden)
    source = tmp_path / "assessment.json"
    source.write_text(json.dumps(result))
    monkeypatch.setattr(sys, "argv", ["hermes-rubric", "render", str(source)])
    with pytest.raises(SystemExit) as exit_info:
        cli.main()
    assert exit_info.value.code == 0
    assert capsys.readouterr().out == render_markdown(result)


def test_cli_stdin_output_and_source_preservation(result, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(result)))
    output = tmp_path / "assessment.md"
    assert main(["-", "--out", str(output)]) == 0
    assert output.read_text() == render_markdown(result)
    source = tmp_path / "assessment.json"
    source.write_text(json.dumps(result))
    before = source.read_bytes()
    assert main([str(source), "--out", str(source)]) == 2
    assert source.read_bytes() == before


def test_output_hardlink_cannot_replace_input_json(result, tmp_path):
    source = tmp_path / "assessment.json"
    source.write_text(json.dumps(result))
    alias = tmp_path / "assessment.md"
    os.link(source, alias)
    before = source.read_bytes()
    assert main([str(source), "--out", str(alias)]) == 2
    assert source.read_bytes() == before


@pytest.mark.parametrize("payload", ["null", "[]", "{}", "not json"])
def test_cli_rejects_invalid_input_without_output(payload, tmp_path, capsys):
    source = tmp_path / "invalid.json"
    source.write_text(payload)
    destination = tmp_path / "report.md"
    assert main([str(source), "--out", str(destination)]) == 2
    assert not destination.exists()
    assert "ERROR rendering assessment:" in capsys.readouterr().err
