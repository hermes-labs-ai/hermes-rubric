"""The quickstart recipe must stay runnable and keep its published invariants.

`docs/quickstart.md` gives a reader with no checkout one complete synthetic
assessment and then tells them which properties of the result they may assert.
This module is the gate on that promise:

* the documented target is extracted from the doc itself, so the recipe cannot
  drift from what is published;
* the documented CLI invocation still names a real class template and passes an
  explicit ``--backend``, because automatic backend selection must never be
  inherited by a pasted recipe;
* the recipe writes and reads only inside a private `mktemp -d` workdir that a
  trap removes, never a predictable path in shared `/tmp`;
* the published claims about run-to-run behaviour stay inside what the repo can
  actually show;
* the structural invariants the doc licenses — schema version, one score per
  rubric dimension, one evidence entry per score, the no-evidence and hedge
  clamps, coverage, receipt — hold end to end.

**This is a plumbing test.** The backend is a stub, so nothing here says
anything about a real model's scores, and no assertion pins a score value. A
live receipt is a separate artifact.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_rubric import __version__, assess_path
from hermes_rubric import cli as cli_mod
from hermes_rubric import backends as backends_mod
from hermes_rubric.classes import load_class, to_rubric

DOC = Path(__file__).resolve().parent.parent / "docs" / "quickstart.md"
ARTIFACT_CLASS = "social-post"
# The backend the published command names. The stub answers the calls, but the
# assessment is driven through this backend name so the recipe under test is
# the documented one rather than a placeholder.
DOCUMENTED_BACKEND = "ollama-local"


def _doc_text() -> str:
    return DOC.read_text(encoding="utf-8")


def _quickstart_target() -> str:
    bodies = re.findall(r"<<'EOF'\n(.*?)\nEOF\n", _doc_text(), re.DOTALL)
    assert bodies, "docs/quickstart.md must publish a self-contained target heredoc"
    return bodies[0]


def _quickstart_command() -> str:
    match = re.search(r"^hermes-rubric \\\n(?:.*\\\n)*.*$", _doc_text(), re.MULTILINE)
    assert match, "docs/quickstart.md must publish a hermes-rubric invocation"
    return match.group(0)


def _bash_blocks() -> list[str]:
    blocks = re.findall(r"```bash\n(.*?)```", _doc_text(), re.DOTALL)
    assert blocks, "docs/quickstart.md must publish runnable bash blocks"
    return blocks


def _recipe_block() -> str:
    """The block that creates the workdir and runs the assessment."""
    matching = [b for b in _bash_blocks() if "hermes-rubric \\\n" in b]
    assert len(matching) == 1, "exactly one bash block must run the assessment"
    return matching[0]


def _reader_block() -> str:
    """The block that reads the result back."""
    matching = [b for b in _bash_blocks() if "python3 - <<'EOF'" in b]
    assert len(matching) == 1, "exactly one bash block must read the result back"
    return matching[0]


def _reader_script() -> str:
    """The Python heredoc body inside the reader block."""
    match = re.search(r"<<'EOF'\n(.*?)\nEOF\n", _reader_block(), re.DOTALL)
    assert match, "the reader block must publish a python heredoc"
    return match.group(1)


def test_quickstart_command_pins_a_class_template_and_an_explicit_backend():
    command = _quickstart_command()
    assert f"--artifact-class {ARTIFACT_CLASS}" in command
    assert "--backend " in command, (
        "the published recipe must pass an explicit --backend so a pasted "
        "command cannot inherit automatic backend selection"
    )


@pytest.fixture
def stub_backend(monkeypatch):
    """Answer both pipeline stages deterministically, without a model.

    Citations must carry an ``evidence_id`` that resolves to a section of the
    real target and a quote that actually appears in it — otherwise
    ``_normalize_evidence`` rejects every citation and forces
    ``evidence_found: false`` on every dimension, which would make the clamp
    assertions below pass for the wrong reason. The stub therefore reads the
    section id and a real quote straight out of the prompt it is given.
    """
    template = to_rubric(load_class(ARTIFACT_CLASS))
    by_name = {dim["name"]: dim for dim in template["dimensions"]}
    ids = [dim["id"] for dim in template["dimensions"]]
    seen_backends: list[str | None] = []
    # One dimension returns no evidence at all and is hedged (both clamps
    # apply); a second has real evidence but low confidence (hedge clamp only).
    no_evidence_id, hedged_id = ids[0], ids[1]

    def _dim_for(prompt: str) -> dict:
        for name, dim in by_name.items():
            if f"DIMENSION: {name}\n" in prompt:
                return dim
        raise AssertionError("stub backend could not identify the dimension")

    def _section(prompt: str) -> tuple[str, str]:
        match = re.search(
            r'<SECTION id="([^"]+)"[^>]*>\n(.*?)\n</SECTION>', prompt, re.DOTALL
        )
        assert match, "evidence prompt must expose a citable section"
        section_id, body = match.group(1), match.group(2)
        quote = next(line for line in body.splitlines() if line.strip())
        return section_id, quote.strip()

    def fake_call(prompt: str, backend: str | None = None, max_tokens: int = 2048) -> str:
        seen_backends.append(backend)
        dim = _dim_for(prompt)
        if prompt.startswith("You are an evidence collector"):
            if dim["id"] == no_evidence_id:
                return json.dumps({
                    "dim_id": dim["id"],
                    "evidence_found": False,
                    "confidence": "low",
                    "hedge": True,
                    "citations": [],
                    "evidence_summary": "nothing observable for this dimension",
                })
            section_id, quote = _section(prompt)
            return json.dumps({
                "dim_id": dim["id"],
                "evidence_found": True,
                "confidence": "low" if dim["id"] == hedged_id else "high",
                "hedge": dim["id"] == hedged_id,
                "citations": [
                    {
                        # `code` keeps the self-marketing clamp (which caps
                        # doc-only citations at 6) out of the way, so the hedge
                        # clamp is the only thing that can pull the stub's 10
                        # down into [3, 7].
                        "evidence_id": section_id,
                        "quote": quote,
                        "location": section_id,
                        "source_class": "code",
                    }
                ],
                "evidence_summary": "quoted the opening claim",
            })
        assert prompt.startswith("You are a structured scorer")
        # Deliberately over-score, so the clamps must do the work.
        return json.dumps({
            "dim_id": dim["id"],
            "score": 10,
            "score_rationale": "stub",
            "evidence_drove_score": "stub",
            "hedge_applied": False,
        })

    monkeypatch.setattr(backends_mod, "call", fake_call)
    return {
        "no_evidence_id": no_evidence_id,
        "hedged_id": hedged_id,
        "seen_backends": seen_backends,
    }


def _documented_argv(workdir: Path) -> list[str]:
    """The published command, tokenised, with `$workdir` bound to a real path.

    Built from the doc rather than hand-written, so the argv under test is the
    one a reader copies. Only the shell variable is expanded — every other
    token, including the file names under it, is whatever the doc publishes.
    """
    command = _quickstart_command().replace("\\\n", " ")
    argv = shlex.split(command)
    assert argv[0] == "hermes-rubric"
    # Checked before expansion: the substituted path is a real directory name
    # and may legitimately contain `$` (pytest honours `--basetemp`), so only
    # the published tokens are screened for shell variables.
    assert not any("$" in token.replace("$workdir", "") for token in argv[1:]), (
        "the published command must not depend on any shell variable other "
        "than $workdir"
    )
    return [token.replace("$workdir", str(workdir)) for token in argv[1:]]


def _assess(target: Path):
    """Run the assessment exactly as the published command does."""
    return assess_path(
        target,
        intent=f"Score against the {ARTIFACT_CLASS} class template.",
        context_path=target,
        artifact_class=ARTIFACT_CLASS,
        backend=DOCUMENTED_BACKEND,
    )


def test_quickstart_command_omits_intent_and_context():
    """The recipe must stay self-contained: no user file, no undefined flag."""
    command = _quickstart_command()
    assert f"--backend {DOCUMENTED_BACKEND}" in command
    assert "--intent" not in command
    assert "--context" not in command
    assert '--target "$workdir/post.md"' in command
    assert '--out "$workdir/result.json"' in command


def test_quickstart_recipe_uses_a_private_temporary_workdir():
    """The recipe must not write or read predictable names in shared `/tmp`.

    A published command that writes `/tmp/post.md` and `/tmp/result.json` is a
    symlink/pre-creation target for any other user on a multi-user host
    (CWE-377), and the reader copies it verbatim. The contract is: one
    `mktemp -d` directory, removed by a trap, every path quoted and rooted in
    it, and nothing in any shell block naming a fixed `/tmp` file.
    """
    recipe = _recipe_block()

    assert 'workdir="$(mktemp -d)" || exit 1' in recipe, (
        "the recipe must allocate its own private directory with mktemp -d and "
        "stop if that fails — an empty $workdir collapses every path below to "
        "the filesystem root"
    )
    assert "trap 'rm -rf -- \"$workdir\"' EXIT" in recipe, (
        "the recipe must remove its workdir on shell exit"
    )

    # Every expansion is double-quoted, so a workdir containing a space or a
    # glob character cannot word-split into a different path.
    for block in _bash_blocks():
        for index in (m.start() for m in re.finditer(r"\$workdir", block)):
            assert index > 0 and block[index - 1] == '"', (
                f"unquoted $workdir expansion in: {block[max(0, index - 40):index + 20]!r}"
            )

    # Both files the recipe touches live under the workdir...
    assert 'cat > "$workdir/post.md" <<' in recipe
    assert '--target "$workdir/post.md"' in recipe
    assert '--out "$workdir/result.json"' in recipe

    # ...and no shell block falls back to a fixed path in shared /tmp.
    for block in _bash_blocks():
        assert "/tmp/" not in block, f"fixed /tmp path in a runnable block: {block!r}"


def _run_published_recipe(
    tmp_path: Path, *, workdir: Path, record: Path, mktemp_fails: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run the doc's shell block with `mktemp` and the CLI shimmed.

    The `mktemp` shim honours the contract the recipe relies on — `-d` creates
    a fresh owner-only directory and prints its path — or, with
    ``mktemp_fails``, fails the way a full or read-only temp filesystem would.
    The CLI shim records the argv it was handed.
    """
    shim = tmp_path / "bin"
    shim.mkdir()

    mktemp = shim / "mktemp"
    body = (
        "import sys; sys.exit(1)\n"
        if mktemp_fails
        else (
            "import os\n"
            f"os.makedirs({str(workdir)!r}, mode=0o700, exist_ok=True)\n"
            f"print({str(workdir)!r})\n"
        )
    )
    mktemp.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "assert sys.argv[1:] == ['-d'], sys.argv\n" + body,
        encoding="utf-8",
    )
    mktemp.chmod(0o755)

    cli = shim / "hermes-rubric"
    cli.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"open({str(record)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
        "out = sys.argv[sys.argv.index('--out') + 1]\n"
        "open(out, 'w').write('{}')\n"
        "target = sys.argv[sys.argv.index('--target') + 1]\n"
        "open(target).read()\n",
        encoding="utf-8",
    )
    cli.chmod(0o755)

    return subprocess.run(
        ["bash", "-s"],
        input=_recipe_block(),
        env={**os.environ, "PATH": f"{shim}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_quickstart_recipe_stops_when_mktemp_fails(tmp_path):
    """A failed `mktemp -d` must abort, not fall through to the filesystem root.

    Without the guard, `workdir` is empty and every quoted path in the block
    expands to `/post.md` and `/result.json` — the exact predictable-shared-path
    failure the workdir was introduced to remove, and writable for a root user.
    """
    record = tmp_path / "argv.json"
    proc = _run_published_recipe(
        tmp_path,
        workdir=tmp_path / "unused",
        record=record,
        mktemp_fails=True,
    )

    assert proc.returncode != 0, "the recipe must fail when mktemp -d fails"
    assert not record.exists(), (
        "the recipe reached hermes-rubric with an empty $workdir; every path "
        "would have collapsed to the filesystem root"
    )
    assert "/post.md" not in proc.stdout + proc.stderr


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_quickstart_recipe_block_executes_and_cleans_up(tmp_path):
    """Run the published shell block for real, with `mktemp` and the CLI shimmed.

    Static assertions can only say the recipe *looks* quoted. This runs it. The
    `mktemp` shim hands back a directory whose name contains a space and a
    glob character — legal on any real machine, and fatal to an unquoted
    expansion, which would word-split into the wrong path and fail the block.
    It then checks the three things a reader depends on: the target heredoc
    lands in the private directory, the CLI receives paths inside it, and the
    trap removes it when the shell exits.

    (`mktemp` is shimmed rather than steered with `TMPDIR` because BSD
    `mktemp -d` ignores `TMPDIR` and uses the Darwin per-user temp directory,
    so the environment variable is not a portable lever.)
    """
    workdir = tmp_path / "work dir [1]"
    record = tmp_path / "argv.json"
    proc = _run_published_recipe(tmp_path, workdir=workdir, record=record)
    assert proc.returncode == 0, f"published recipe failed: {proc.stderr}"

    argv = json.loads(record.read_text(encoding="utf-8"))
    target = Path(argv[argv.index("--target") + 1])
    out = Path(argv[argv.index("--out") + 1])
    # The space and the bracket survived: no word-splitting, no globbing.
    assert target.parent == workdir, f"--target escaped the workdir: {target}"
    assert out.parent == workdir, f"--out escaped the workdir: {out}"
    assert argv[argv.index("--backend") + 1] == DOCUMENTED_BACKEND

    # The trap fired on shell exit and took the whole directory with it, so the
    # heredoc target and the result JSON do not outlive the recipe.
    assert not workdir.exists(), "the recipe must remove its workdir on exit"


def test_quickstart_reader_block_takes_the_workdir_from_the_environment():
    """The reader must be handed the workdir, not re-derive a guessable path."""
    reader = _reader_block()
    assert reader.startswith('WORKDIR="$workdir" python3 - <<'), (
        "the reader block must run with WORKDIR bound to the recipe's workdir"
    )

    script = _reader_script()
    assert 'os.environ["WORKDIR"]' in script
    assert "/tmp" not in script
    assert "import os" in script
    compile(script, "docs/quickstart.md:reader", "exec")


def test_rubric_hash_is_stable_across_two_runs(stub_backend, tmp_path):
    """The doc pins rubric selection, not scores; prove the hash half.

    Two runs of the same published command over the same target must produce
    the same `stage_1_rubric_hash_sha256`, which is what makes the caveat about
    differing scores meaningful rather than an excuse for drift.
    """
    target = tmp_path / "post.md"
    target.write_text(_quickstart_target() + "\n", encoding="utf-8")

    first = _assess(target).to_dict()
    second = _assess(target).to_dict()

    def _hash(payload):
        return payload["receipt"]["pipeline"]["stage_1_rubric_hash_sha256"]

    assert _hash(first) == _hash(second)
    assert len(_hash(first)) == 64
    assert first["receipt"]["pipeline"]["stage_1_rubric_source"] == "class-template"
    assert [d["id"] for d in first["rubric"]["dimensions"]] == [
        d["id"] for d in second["rubric"]["dimensions"]
    ]


def test_quickstart_recipe_holds_its_published_invariants(
    stub_backend, tmp_path, monkeypatch
):
    # Stand in for `mktemp -d`: a private directory the recipe owns. The file
    # names come from the doc, not from this test, so a renamed file in the
    # published recipe fails here rather than drifting silently.
    workdir = tmp_path / "workdir"
    workdir.mkdir(mode=0o700)
    target = workdir / "post.md"
    target.write_text(_quickstart_target() + "\n", encoding="utf-8")

    # Drive the published command through the real CLI entry point: argv is
    # parsed from the doc, the backend is the documented one (answered by the
    # stub), and the assertions read the JSON the CLI actually wrote.
    out = workdir / "result.json"
    argv = _documented_argv(workdir)
    assert "--intent" not in argv and "--context" not in argv
    assert argv[argv.index("--backend") + 1] == DOCUMENTED_BACKEND
    assert argv[argv.index("--target") + 1] == str(target)
    assert argv[argv.index("--out") + 1] == str(out)

    monkeypatch.setattr(sys, "argv", ["hermes-rubric", *argv])
    cli_mod.main()

    assert out.is_file(), "the published --out path must be written"
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert stub_backend["seen_backends"], "the stub must have answered the calls"
    assert set(stub_backend["seen_backends"]) == {DOCUMENTED_BACKEND}

    assert payload["schema_version"]

    rubric_ids = [dim["id"] for dim in payload["rubric"]["dimensions"]]
    score_ids = [score["dim_id"] for score in payload["per_dim_scores"]]
    evidence_ids = [item["dim_id"] for item in payload["evidence_citations"]]
    assert score_ids == rubric_ids
    assert sorted(evidence_ids) == sorted(rubric_ids)

    # The two clamps are independent, so a dimension that is both hedged and
    # evidence-free must satisfy BOTH bounds, not whichever one is checked
    # first. Checking them with `elif` would let a future regression push the
    # intersection below 3 unnoticed.
    evidence_by_id = {item["dim_id"]: item for item in payload["evidence_citations"]}
    scores_by_id = {score["dim_id"]: score["score"] for score in payload["per_dim_scores"]}

    # Non-degeneracy guard. If citations were rejected, every dimension would
    # come back evidence-free and clamp to 3, and the assertions below would
    # pass without ever exercising the hedge clamp.
    hedged = evidence_by_id[stub_backend["hedged_id"]]
    assert hedged["evidence_found"] is True
    assert hedged["citations"], "the hedged dimension must keep a real citation"
    assert hedged["hedge"] is True
    for dim_id, score in scores_by_id.items():
        evidence = evidence_by_id[dim_id]
        if not evidence["evidence_found"]:
            assert score <= 3, f"no-evidence clamp must survive ({dim_id})"
        if evidence["hedge"]:
            assert 3 <= score <= 7, f"hedge clamp must survive ({dim_id})"

    # The stub makes this dimension hedged *and* evidence-free: both clamps
    # apply, and their intersection is exactly 3.
    intersection = stub_backend["no_evidence_id"]
    assert evidence_by_id[intersection]["hedge"] is True
    assert evidence_by_id[intersection]["evidence_found"] is False
    assert scores_by_id[intersection] == 3

    assert 3 <= scores_by_id[stub_backend["hedged_id"]] <= 7

    coverage = payload["coverage"]
    assert coverage["status"] == "complete"
    assert coverage["limitations"] == []

    receipt = payload["receipt"]
    assert receipt["tool_version"].startswith("hermes-rubric ")
    assert receipt["backend"] == DOCUMENTED_BACKEND
    assert receipt["pipeline"]["stage_1_rubric_source"] == "class-template"
    assert len(receipt["pipeline"]["stage_1_rubric_hash_sha256"]) == 64
    assert receipt["inputs"]["target_path"].endswith("post.md")
    # The published command passes no --context, so the CLI must fill it from
    # the target; otherwise the recipe silently assesses against nothing.
    assert receipt["inputs"]["context_path"] == receipt["inputs"]["target_path"]
    assert receipt["inputs"]["context_hash_sha256"] == receipt["inputs"]["target_hash_sha256"]

    # The published reader block, run verbatim against what the CLI just wrote:
    # it must locate the result through WORKDIR and touch only fields that
    # exist. Anything it prints is incidental; that it runs at all is the point.
    script = _reader_script()
    monkeypatch.setenv("WORKDIR", str(workdir))
    exec(compile(script, "docs/quickstart.md:reader", "exec"), {"__name__": "__main__"})


def test_quickstart_pins_the_packaged_release():
    """The published install must stay pinned to the version it documents.

    A floating `pip install hermes-rubric` stops being release-matched the
    moment a new version ships. Pinning is only honest while the pin tracks
    the package, so this fails the release that forgets to bump the doc.
    """
    text = _doc_text()
    assert f"pip install hermes-rubric=={__version__}" in text
    assert f"hermes-rubric {__version__}" in text, (
        "the documented `--version` output must match the packaged version"
    )


def test_quickstart_cites_a_source_for_its_operational_numbers():
    """AGENTS.md rule 5: numeric claims carry a pointer to their source."""
    text = _doc_text()
    for pointer in (
        "src/hermes_rubric/backends.py",
        "src/hermes_rubric/cli.py",
        "src/hermes_rubric/score.py",
        "src/hermes_rubric/classes/social-post.yaml",
        # the documented --version output
        "src/hermes_rubric/__init__.py",
        # the description of what the reproducibility note does and does not say
        "src/hermes_rubric/receipt.py",
        # the decoding settings behind the "scores are not pinned" statement
        "_call_ollama()",
        "_call_openai()",
    ):
        assert pointer in text, f"missing source pointer: {pointer}"


def test_version_pointer_names_where_the_version_actually_lives():
    """The cited file must really define the version the doc publishes."""
    source = (
        Path(__file__).resolve().parent.parent
        / "src" / "hermes_rubric" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert f'__version__ = "{__version__}"' in source
    assert f"`hermes-rubric {__version__}`" in _doc_text()


def test_nondeterminism_pointer_names_where_the_note_actually_lives(
    stub_backend, tmp_path
):
    """The cited file must really emit the note, and the note must reach the result."""
    source = (
        Path(__file__).resolve().parent.parent
        / "src" / "hermes_rubric" / "receipt.py"
    ).read_text(encoding="utf-8")
    assert "reproducibility_note" in source

    target = tmp_path / "post.md"
    target.write_text(_quickstart_target() + "\n", encoding="utf-8")
    note = _assess(target).to_dict()["receipt"]["reproducibility_note"]

    assert "not deterministic" in note
    assert "not directly comparable" in note


def test_quickstart_labels_the_backend_prerequisites():
    text = _doc_text()
    for backend in ("ollama-local", "claude-cli", "openai-sdk"):
        assert backend in text
    assert "OPENAI_API_KEY" in text


def test_nondeterminism_claim_does_not_overstate_the_receipt(stub_backend, tmp_path):
    """The note warns about rubric hashes and Stage 1; it is not a scores proof.

    Earlier wording ("Each result says so itself", then "two runs of this exact
    command on the same file can differ") implied the receipt demonstrates that
    scores vary between runs. It does not — the class template bypasses Stage 1
    and the hash is identical across runs, and nothing in this repo measures
    run-to-run score movement. The doc may say the scores are *unpinned*, which
    the backend code shows; it may not say they *do* differ.
    """
    text = _doc_text()
    assert "does not settle it either" in text
    assert "Each result says so itself" not in text

    target = tmp_path / "post.md"
    target.write_text(_quickstart_target() + "\n", encoding="utf-8")
    note = _assess(target).to_dict()["receipt"]["reproducibility_note"]

    # What the note actually covers, and what it does not.
    assert "rubric_hash" in note
    assert "Stage-1 rubric synthesis is not deterministic" in note
    assert "not directly comparable" in note
    # It never claims run-to-run score variance for an unchanged rubric hash.
    assert "two runs" not in note
    assert "can differ" not in note


def test_doc_does_not_assert_unmeasured_run_to_run_score_variance():
    """Ban the formulation the receipt was cited for but does not support.

    "two runs of this exact command on the same file can differ" is an
    empirical claim about model behaviour. No fixture, receipt or test in this
    repo measures it, so the doc must not state it as fact — in that wording or
    the looser "across backends and runs" variant that replaced it.
    """
    text = " ".join(_doc_text().split())
    for banned in (
        "two runs of this exact command",
        "can score differently across backends and runs",
    ):
        assert banned not in text, (
            f"unsupported run-to-run variance claim restored: {banned!r}"
        )
    assert "two runs" not in text


def test_score_stability_claim_cites_the_decoding_settings_it_rests_on():
    """What replaces it must be code-checkable, and the code must still match.

    The doc says the recipe pins no decoding parameters. That is a statement
    about `_call_ollama()`, so it fails here the moment that function starts
    sending a temperature or a seed — rather than quietly becoming false in
    published documentation.
    """
    text = " ".join(_doc_text().split())
    assert "It does not make the scores deterministic." in text
    assert (
        "`_call_ollama()` in `src/hermes_rubric/backends.py` sends only "
        "`num_predict`, no `temperature` and no `seed`" in text
    )
    # The guidance the finding asked us to keep.
    assert "Do not assert a particular aggregate or per-dimension score." in text

    source = (
        Path(__file__).resolve().parent.parent
        / "src" / "hermes_rubric" / "backends.py"
    ).read_text(encoding="utf-8")

    def _body(name: str) -> str:
        start = source.index(f"def {name}(")
        end = source.index("\ndef ", start + 1)
        return source[start:end]

    ollama = _body("_call_ollama")
    assert "num_predict" in ollama
    assert "temperature" not in ollama, (
        "_call_ollama now sets a temperature; the quickstart claim that it "
        "sends none is stale"
    )
    assert "seed" not in ollama

    openai = _body("_call_openai")
    assert '"temperature": 0' in openai and '"seed": 42' in openai, (
        "the quickstart contrasts _call_openai's pinned decoding with "
        "_call_ollama's; that contrast must still hold"
    )


def test_exit_guidance_separates_success_from_failures_and_usage_errors():
    """Exit 2 is shared between Stage 1 and argparse; the doc must say so."""
    text = " ".join(_doc_text().split())
    assert "Exit `0` means the pipeline completed and produced that output" in text
    assert "a low aggregate still exits `0`" in text
    assert "Exit `2` is shared" in text
    assert "argparse also uses it for a CLI usage error" in text
    assert "prints `usage:`" in text and "prints `ERROR in Stage 1`" in text
