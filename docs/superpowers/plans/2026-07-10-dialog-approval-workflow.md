# Dialog Approval Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed dialog approval workflow in which one exact user reply, `批准`, authorizes reproducible source commits, two profile-bound governance signoffs, verification, and a normal fast-forward push to `origin/main`.

**Architecture:** A shared path policy first removes generated and human-decision state from all evidence surfaces. Immutable approval-card and transaction-journal models bind evaluation identity to a proposed Git tree, while an injected Git backend performs exact staging, clean-worktree reproduction, append-only signoff commits, and explicit refspec push. The existing CLI remains the entrypoint and delegates `prepare-review` and `approve-card` to the new approval package.

**Tech Stack:** Python 3.13 standard library, frozen dataclasses, canonical JSON/SHA-256, subprocess argument arrays, Git temporary indexes/worktrees, pytest, the existing Harness evaluator and legacy KB validator.

---

## File Map And Ownership

| owner | files | responsibility |
|:---|:---|:---|
| Red-test agent | `tests/test_harness_path_policy.py`, `tests/test_approval_cards.py`, `tests/test_approval_git_backend.py`, `tests/test_approval_transaction.py`, `tests/test_approval_cli.py`, focused additions to existing Harness tests | executable behavior contract before production edits |
| Validator/lifecycle agent | `harness/engine/path_policy.py`, `harness/engine/report.py`, `scripts/validate_benchmark_kb.py`, `.gitignore`, `tests/test_harness_path_policy.py`, `tests/test_harness_engine.py`, `tests/test_harness_pipeline.py` | one exclusion policy and pending/accepted production smoke |
| Card/signoff agent | `harness/approval/models.py`, `harness/approval/cards.py`, `harness/approval/signoff_payloads.py`, `harness/engine/signoffs.py`, `harness/signoffs/signoff.schema.json`, `tests/test_approval_cards.py`, `tests/test_harness_signoffs.py` | immutable cards, exact approval binding, safe supersession |
| Git transaction agent | `harness/approval/git_backend.py`, `harness/approval/journal.py`, `harness/approval/transaction.py`, `tests/approval_git_helpers.py`, `tests/test_approval_git_backend.py`, `tests/test_approval_transaction.py` | proposed tree, commit/worktree verification, recovery, push |
| CLI agent | `harness/approval/service.py`, `harness/approval/render.py`, `harness/engine/cli.py`, `tests/test_approval_cli.py` | prepare/approve orchestration and Chinese approval card |
| Documentation agent | `harness/signoffs/README.md`, `ops/plans/harness_engineering_plan_v1.0.md`, `README.md`, `index.md`, `RELEASE_NOTES.md`, `ops/log.md` | operator workflow and no-overclaim boundary |

Tasks 2 and 3 may run in parallel only after Task 1 freezes their tests and only while their file ownership remains disjoint. Tasks 4-8 are sequential. The root agent performs every exact-path commit after review; implementation agents do not stage unrelated files.

### Task 1: Freeze The Red-Test Contract

**Files:**
- Create: `tests/test_harness_path_policy.py`
- Create: `tests/test_approval_cards.py`
- Create: `tests/approval_git_helpers.py`
- Create: `tests/test_approval_git_backend.py`
- Create: `tests/test_approval_transaction.py`
- Create: `tests/test_approval_cli.py`
- Modify: `tests/test_harness_engine.py`
- Modify: `tests/test_harness_pipeline.py`
- Modify: `tests/test_harness_signoffs.py`

- [ ] **Step 1: Add the path-policy and digest-invariance red tests**

Create a path matrix that cannot be weakened by broad prefix matching:

```python
@pytest.mark.parametrize(
    ("path", "excluded"),
    [
        ("ops/acceptance/project_acceptance_report.json", True),
        ("ops/acceptance/dialog_cards/approval_abc.json", True),
        ("ops/acceptance/dialog_transactions/approval_abc.json", True),
        ("harness/PROJECT_ACCEPTANCE.md", True),
        ("harness/signoffs/signoff_request_v1.json", True),
        ("harness/signoffs/signoff_governance_v2.json", True),
        ("harness/signoffs/signoff_current_phase_v1.json", True),
        ("harness/signoffs/signoff.schema.json", False),
        ("harness/signoffs/README.md", False),
        ("ops/validation/wiki_validation_report.md", False),
        ("harness/engine/report.py", False),
    ],
)
def test_acceptance_state_path_policy_is_exact(path: str, excluded: bool) -> None:
    assert is_acceptance_state_path(path) is excluded
```

Add tests that write generated/card/journal/decision fixtures and assert both `workspace_source_digest()` and the legacy tracked-file count remain unchanged. Assert that changing `signoff.schema.json` still changes the workspace digest.

- [ ] **Step 2: Add lifecycle and signoff-hardening red tests**

Keep isolated unsigned roll-up coverage and add the signed case:

```python
def test_machine_pass_with_required_signoff_is_accepted() -> None:
    result = roll_up_profile(
        profile_with_governance_role,
        passing_gate_results,
        {"governance_owner"},
    )
    assert result.harness_status is HarnessStatus.VALID
    assert result.project_status is ProjectVerdict.ACCEPTED
    assert result.missing_signoff_roles == ()
    assert exit_code_for(result) == 0
```

Add a production-state assertion that accepts only these exact mappings:

```python
allowed = {
    ProjectVerdict.PENDING_HUMAN_SIGNOFF: ((), ("governance_owner",), 1),
    ProjectVerdict.ACCEPTED: (("governance_owner",), (), 0),
}
expected_valid, expected_missing, expected_exit = allowed[evaluation.profile.project_status]
assert evaluation.valid_signoff_roles == expected_valid
assert evaluation.profile.missing_signoff_roles == expected_missing
assert completed.returncode == expected_exit
```

Add adversarial signoff tests for partial approval binding and cross-profile supersession:

```python
def test_supersedes_rejects_same_role_from_other_profile(tmp_path: Path) -> None:
    write_json(tmp_path / "governance.json", signoff(profile_id="governance"))
    write_json(
        tmp_path / "current.json",
        signoff(profile_id="current_phase", supersedes="governance.json"),
    )
    result = validate_signoff_directory(tmp_path, current_phase_context())
    assert result.invalid_signoffs[0].reason_code == "signoff_supersedes_invalid"
```

- [ ] **Step 3: Add immutable-card red tests**

The tests must inject time and nonce instead of reading wall-clock or random state:

```python
def test_card_id_is_canonical_and_stable() -> None:
    card = create_approval_card(card_input(), now=NOW, nonce=b"0" * 16)
    assert card.card_id == f"approval_{card.card_sha256[:24]}"
    assert load_approval_card(write_card(card), card.card_sha256, now=NOW) == card

@pytest.mark.parametrize("message", ["批准。", '"批准"', "我批准", "不批准", "批准\n继续"])
def test_only_exact_normalized_approval_message_is_accepted(message: str) -> None:
    assert is_exact_approval_message(message) is False
```

Also cover expiry, tamper, unsupported profile set, mismatched profile identity, mutable overwrite rejection, fixed rationale, per-profile signoff filename, and Governance-only supersedes.

- [ ] **Step 4: Add Git backend and transaction red tests with a small bare remote**

Create an explicit helper instead of copying the real repository:

```python
def init_repo_with_bare_remote(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    run(["git", "init", "--bare", str(remote)])
    run(["git", "init", "-b", "main", str(work)])
    run(["git", "-C", str(work), "config", "user.name", "Test Reviewer"])
    run(["git", "-C", str(work), "config", "user.email", "reviewer@example.test"])
    run(["git", "-C", str(work), "remote", "add", "origin", str(remote)])
    return work, remote
```

Cover index-not-clean rejection, source manifest mode/hash/deletion, exact staged paths, proposed tree equality, active hooks/config rejection, remote movement, non-fast-forward push, clean worktree callback, local-commit preservation, idempotent resume, and no duplicate signoffs.

- [ ] **Step 5: Add CLI red tests**

Use dependency injection and temporary roots. Assert `prepare-review` accepts exactly the bundled profiles and `approve-card` requires both card ID and full expected digest. Assert release/full profiles and skip-verification flags are rejected by `argparse`.

- [ ] **Step 6: Run focused red tests and record the expected failures**

Run:

```bash
pytest -q \
  tests/test_harness_path_policy.py \
  tests/test_harness_signoffs.py \
  tests/test_approval_cards.py \
  tests/test_approval_git_backend.py \
  tests/test_approval_transaction.py \
  tests/test_approval_cli.py
```

Expected: failures are limited to missing `harness.engine.path_policy`, missing `harness.approval` modules, unsupported dialog binding, and cross-profile supersession currently being accepted. Syntax, fixture, and unrelated baseline failures are not acceptable.

### Task 2: Stabilize The Validator And Signoff Lifecycle

**Files:**
- Create: `harness/engine/path_policy.py`
- Modify: `harness/engine/report.py`
- Modify: `scripts/validate_benchmark_kb.py`
- Modify: `.gitignore`
- Modify: `tests/test_harness_path_policy.py`
- Modify: `tests/test_harness_engine.py`
- Modify: `tests/test_harness_pipeline.py`

- [ ] **Step 1: Implement one shared acceptance-state predicate**

```python
from pathlib import Path

_EXACT_STATE_FILES = frozenset(
    {
        "harness/PROJECT_ACCEPTANCE.md",
        "harness/signoffs/signoff_request_v1.json",
    }
)


def is_acceptance_state_path(value: str | Path) -> bool:
    normalized = Path(value).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    path = Path(normalized)
    if path.is_absolute() or ".." in path.parts:
        return False
    if normalized in _EXACT_STATE_FILES or normalized.startswith("ops/acceptance/"):
        return True
    return (
        path.parts[:2] == ("harness", "signoffs")
        and path.suffix == ".json"
        and path.name not in {"signoff.schema.json", "signoff_request_v1.json"}
    )
```

Move workspace source inclusion into a public `is_workspace_source_path()` in the same module. `report.py` delegates to it; it must no longer maintain a second exclusion list.

- [ ] **Step 2: Apply the predicate to every legacy scan before counting or reading**

Add repository root to `sys.path` in the validator, import the shared predicate, and skip acceptance state in both `check_markdown_links()` and `check_tracked_large_or_forbidden_files()` before incrementing counters. Remove `GENERATED_ACCEPTANCE_MARKDOWN_PATHS` after its behavior is covered by the shared policy.

- [ ] **Step 3: Add anchored generated-state ignore rules**

Append exactly:

```gitignore
/harness/PROJECT_ACCEPTANCE.md
/harness/signoffs/signoff_request_v1.json
/ops/acceptance/project_acceptance_report.json
/ops/acceptance/project_acceptance_report.md
/ops/acceptance/dialog_cards/
/ops/acceptance/dialog_transactions/
```

Do not ignore human decision files under `harness/signoffs/`.

- [ ] **Step 4: Make production smoke lifecycle-aware without weakening assertions**

Rename the actual-state tests and assert the complete pending or accepted tuple, including CLI exit code, valid roles, missing roles, zero invalid signoffs, and byte-for-byte read-only generated outputs.

- [ ] **Step 5: Run focused tests and the validator twice**

Run:

```bash
pytest -q tests/test_harness_path_policy.py tests/test_harness_engine.py tests/test_harness_pipeline.py
python scripts/validate_benchmark_kb.py
sha256sum ops/validation/wiki_validation_report.md
python scripts/validate_benchmark_kb.py
sha256sum ops/validation/wiki_validation_report.md
```

Expected: tests pass; validator reports 0 errors and 0 warnings; the two report SHA-256 values are identical.

- [ ] **Step 6: Root review and commit exact files**

```bash
git add -- .gitignore harness/engine/path_policy.py harness/engine/report.py \
  scripts/validate_benchmark_kb.py tests/test_harness_path_policy.py \
  tests/test_harness_engine.py tests/test_harness_pipeline.py \
  ops/validation/wiki_validation_report.md
git commit -m "fix: stabilize acceptance evidence surface"
```

### Task 3: Implement Immutable Cards And Harden Signoffs

**Files:**
- Create: `harness/approval/__init__.py`
- Create: `harness/approval/models.py`
- Create: `harness/approval/cards.py`
- Create: `harness/approval/signoff_payloads.py`
- Modify: `harness/engine/signoffs.py`
- Modify: `harness/signoffs/signoff.schema.json`
- Modify: `tests/test_approval_cards.py`
- Modify: `tests/test_harness_signoffs.py`

- [ ] **Step 1: Define frozen card models and errors**

```python
class ApprovalError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceEntry:
    path: str
    status: str
    mode: str | None
    sha256: str | None


@dataclass(frozen=True)
class ProfileApproval:
    profile_id: str
    gate_result_digest: str
    gate_count: int
    rationale: str
    signoff_filename: str
    supersedes: str | None


@dataclass(frozen=True)
class ApprovalCard:
    card_id: str
    card_sha256: str
    schema_version: str
    nonce: str
    created_at: str
    expires_at: str
    contract_id: str
    contract_version: str
    contract_digest: str
    evaluator_version: str
    registry_digest: str
    evaluation_id: str
    evidence_digest: str
    reviewer_id: str
    head_oid: str
    remote_name: str
    remote_url: str
    remote_ref: str
    remote_oid: str
    proposed_tree_oid: str
    diff_stat: str
    ahead_commits: tuple[str, ...]
    source_manifest: tuple[SourceEntry, ...]
    profiles: tuple[ProfileApproval, ...]
```

Profile validation must require the exact ordered tuple `("governance", "current_phase")` and shared evaluation identity.

- [ ] **Step 2: Implement canonical card creation and strict loading**

Use `canonical_json()` from the Harness models. Hash only a binding payload that omits `card_id` and `card_sha256`, then derive both fields. Open the final path with
`os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)` so a card cannot
overwrite an existing file. `load_approval_card()` must verify schema, digest,
expected full SHA-256, expiry, allowed profiles, path safety, and exact field
sets.

Implement exact message normalization:

```python
def is_exact_approval_message(value: str) -> bool:
    return unicodedata.normalize("NFC", value).strip() == "批准"
```

- [ ] **Step 3: Generate fixed per-profile signoff payloads**

```python
def build_signoff_payloads(
    card: ApprovalCard,
    *,
    reviewed_at: str,
    approval_event_id: str,
) -> dict[str, dict[str, object]]:
    return {
        profile.signoff_filename: {
            "contract_id": card.contract_id,
            "contract_version": card.contract_version,
            "contract_digest": card.contract_digest,
            "profile_id": profile.profile_id,
            "evaluation_id": card.evaluation_id,
            "evidence_digest": card.evidence_digest,
            "role": "governance_owner",
            "reviewer_id": card.reviewer_id,
            "decision": "approved",
            "rationale": profile.rationale,
            "reviewed_at": reviewed_at,
            "supersedes": profile.supersedes,
            "approval_card_id": card.card_id,
            "approval_card_digest": card.card_sha256,
            "approval_event_id": approval_event_id,
        }
        for profile in card.profiles
    }
```

The Current Phase rationale must retain the exact facts: ten blockers, zero parsed/generated candidates, target/control not frozen, and no scoring/ranking.

- [ ] **Step 4: Harden signoff binding and supersession**

Extend `_SIGNOFF_FIELDS` with the three approval fields. Implement all-or-none validation:

```python
def _valid_approval_binding(value: Mapping[str, Any]) -> bool:
    fields = ("approval_card_id", "approval_card_digest", "approval_event_id")
    present = tuple(field in value for field in fields)
    if not any(present):
        return True
    return all(present) and bool(
        re.fullmatch(r"approval_[0-9a-f]{24}", str(value[fields[0]]))
        and re.fullmatch(r"[0-9a-f]{64}", str(value[fields[1]]))
        and isinstance(value[fields[2]], str)
        and value[fields[2]].strip()
    )
```

For `supersedes`, require equal `contract_id`, `profile_id`, and `role`. In production context, use Git history to prove the target existed before the source signoff's first commit; two files first added in the same commit cannot supersede one another.

- [ ] **Step 5: Update the schema without invalidating legacy v1**

Add the three optional properties and `dependentRequired` in both directions so any one requires the other two. Existing v1 files without all three remain valid.

- [ ] **Step 6: Run focused tests**

```bash
pytest -q tests/test_approval_cards.py tests/test_harness_signoffs.py
```

Expected: all card, legacy, dialog-binding, cross-profile, same-commit and prior-history tests pass.

- [ ] **Step 7: Root review and commit exact files**

```bash
git add -- harness/approval/__init__.py harness/approval/models.py \
  harness/approval/cards.py harness/approval/signoff_payloads.py \
  harness/engine/signoffs.py harness/signoffs/signoff.schema.json \
  tests/test_approval_cards.py tests/test_harness_signoffs.py
git commit -m "feat: add immutable approval cards"
```

### Task 4: Implement The Git Backend And Journal

**Files:**
- Create: `harness/approval/git_backend.py`
- Create: `harness/approval/journal.py`
- Create: `tests/approval_git_helpers.py`
- Modify: `tests/test_approval_git_backend.py`

- [ ] **Step 1: Implement a redacting Git runner**

```python
def run_git(
    root: Path,
    *args: str,
    timeout: int = 30,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=None if env is None else {**os.environ, **env},
    )
    if completed.returncode != 0:
        raise GitApprovalError(redact_git_error(completed.stderr))
    return completed
```

The redactor must remove URL userinfo, common token forms, and SSH environment values. Never log the full environment.

Add `run_git_optional()` for `git config --get` and `--get-regexp`: return
`None` only when Git exits 1 for a missing key/match; all other nonzero exits
raise `GitApprovalError`. A missing `remote.origin.pushurl` means the effective
push URL is `remote.origin.url`; a present push URL must equal the expected SSH
URL.

- [ ] **Step 2: Implement repository and remote preflight**

Define the immutable remote binding before the preflight functions:

```python
@dataclass(frozen=True)
class RemoteSnapshot:
    name: str
    fetch_url: str
    push_url: str
    ref: str
    oid: str
    head_oid: str
    ahead_commits: tuple[str, ...]
```

Implement `require_main_with_clean_index()`, `reject_active_git_customization()`,
`fetch_remote_snapshot()` and `list_ahead_commits()` around this exact command
sequence:

```bash
git symbolic-ref --short HEAD
git diff --cached --quiet
git config --get remote.origin.url
git config --get remote.origin.pushurl
git config --get core.hooksPath
git config --get core.sshCommand
git config --get-regexp '^url\..*\.(insteadOf|pushInsteadOf)$'
git fetch --no-tags origin refs/heads/main
git rev-parse HEAD
git rev-parse refs/remotes/origin/main
git merge-base --is-ancestor refs/remotes/origin/main HEAD
git rev-list --reverse refs/remotes/origin/main..HEAD
```

The branch output must be `main`; cached diff must exit 0; fetch/push URL must
equal `git@github.com:luvega/pep-design.git`; optional customization queries
must have no value; remote ref must exist; and the merge-base check must exit
0. Inspect `.git/hooks/` and reject executable non-sample commit or push hooks.

- [ ] **Step 3: Implement source manifest and proposed tree construction**

Collect modified/deleted and untracked names in an ephemeral config-free Git view; filter with `is_workspace_source_path()`. For each path, record status, Git mode and the SHA-256 of the Git-clean blob that will actually enter the commit, or an explicit deletion marker. Hash binary blobs as raw bytes.

Build the tree using an isolated temporary index:

```python
with tempfile.TemporaryDirectory() as tmp:
    index = Path(tmp) / "index"
    env = {"GIT_INDEX_FILE": str(index)}
    run_git(root, "read-tree", "HEAD", env=env)
    run_git(root, "add", "-A", "--", *manifest_paths, env=env)
    tree_oid = run_git(root, "write-tree", env=env).stdout.strip()
```

- [ ] **Step 4: Implement exact staging, commits, clean worktree and push**

Implement `stage_exact_manifest()`, `commit_source()`,
`temporary_clean_worktree()`, `commit_signoffs()` and `push_exact()` with these
operations, always passing manifest paths as separate subprocess arguments:

```bash
git add -A -- "$MANIFEST_PATH_1" "$MANIFEST_PATH_2"
git diff --cached --name-only -z
git commit -m "chore: checkpoint dialog approval source" \
  -m "Approval-Card: $APPROVAL_CARD_ID"
git worktree add --detach --no-checkout "$TEMP_WORKTREE" "$SOURCE_COMMIT_OID"
git add -- "$SIGNOFF_PATH_1" "$SIGNOFF_PATH_2"
git commit -m "governance: approve acceptance profiles" \
  -m "Approval-Card: $APPROVAL_CARD_ID"
git send-pack --force-with-lease="refs/heads/main:$CARD_REMOTE_OID" \
  git@github.com:luvega/pep-design.git \
  "$FINAL_COMMIT_OID:refs/heads/main"
git fetch-pack git@github.com:luvega/pep-design.git refs/heads/main
```

The implementation compares the NUL-delimited cached path set and canonical
blob hashes to the card manifest before each commit. Transport, staging,
history and checkout materialization run in isolated config-free Git dirs with
replacement refs/grafts excluded. The expected-old lease is used only after a
raw-object fast-forward check and remote confirmation must return
`$FINAL_COMMIT_OID`; unrestricted force push remains forbidden.

Add a `GitBackend` facade that stores `root` and delegates to these functions;
the transaction layer receives this facade through dependency injection rather
than invoking subprocess directly.

- [ ] **Step 5: Implement atomic journal transitions**

```python
class TransactionState(str, Enum):
    PREPARED = "prepared"
    APPROVED = "approved"
    SOURCE_COMMITTED = "source_committed"
    SIGNOFFS_COMMITTED = "signoffs_committed"
    VERIFIED = "verified"
    PUSHED = "pushed"
    INVALIDATED = "invalidated"
    LOCAL_COMMITTED_PUSH_FAILED = "local_committed_push_failed"
```

`transition_journal()` must compare the current state, write to a same-directory temporary file, `fsync`, and `os.replace`. It persists source/signoff/final OIDs, reviewed timestamp, approval event ID, and redacted failure code so retry reuses exact values.

- [ ] **Step 6: Run bare-remote tests**

```bash
pytest -q tests/test_approval_git_backend.py
```

Expected: normal push passes; remote movement, active hooks, dirty index, manifest drift and non-fast-forward fail without changing remote; push failure leaves local commits.

- [ ] **Step 7: Root review and commit exact files**

```bash
git add -- harness/approval/git_backend.py harness/approval/journal.py \
  tests/approval_git_helpers.py tests/test_approval_git_backend.py
git commit -m "feat: add approval git transaction backend"
```

### Task 5: Implement Prepare And Approve Transactions

**Files:**
- Create: `harness/approval/transaction.py`
- Modify: `tests/test_approval_transaction.py`

- [ ] **Step 1: Define injected verifier and transaction result interfaces**

```python
class VerificationRunner(Protocol):
    def prepare(self, root: Path) -> VerificationSnapshot:
        raise NotImplementedError

    def clean_checkout(self, root: Path) -> VerificationSnapshot:
        raise NotImplementedError

    def accepted(self, root: Path) -> VerificationSnapshot:
        raise NotImplementedError


@dataclass(frozen=True)
class VerificationSnapshot:
    evaluation_id: str
    evidence_digest: str
    contract_digest: str
    registry_digest: str
    profile_gate_digests: tuple[tuple[str, str], ...]
```

The production runner invokes pytest, the default validator twice during prepare, `--no-write-report` in clean worktrees, and `evaluate_project()` for both profiles. It rejects non-pass gates and invalid signoffs.

- [ ] **Step 2: Implement `prepare_review()`**

The function must perform Git preflight, run verification, enumerate the full source manifest, build the proposed tree, choose filenames/supersedes, construct fixed rationales, write immutable card/journal, and return both the card and a display model. It must not stage, commit or push.

Filename selection uses `^signoff_(governance|current_phase)_v([0-9]+)\.json$` and
chooses `max(existing version)+1`. `supersedes` is the newest committed signoff
with the same contract/profile/role, or `null` when none exists.

- [ ] **Step 3: Implement `approve_card()` as an ordered transaction**

Use the exact sequence from the approved spec:

```text
validate card/journal/remote/HEAD/index/manifest
transition approved
stage exact source manifest
commit source when non-empty
verify proposed tree and identity
verify temporary clean worktree
write and commit both signoffs
check both profiles accepted
render current_phase canonical report
refetch and compare remote OID
transition verified
push explicit final OID refspec
confirm remote OID
transition pushed
```

If failure occurs after local commits, transition to `local_committed_push_failed`; before commits, transition to `invalidated`. Never reset, amend or delete files.

At the `approved` transition, generate one event ID with
`"approval_event_" + secrets.token_hex(12)` and one
timezone-aware `reviewed_at`; persist both before writing signoffs so every
retry reuses the same values.

- [ ] **Step 4: Implement idempotent `resume_push()`**

Only `local_committed_push_failed` may resume. It must reuse stored final OID, require the same remote baseline, re-run accepted checks, and push without recreating timestamps, filenames, commits or signoffs. For source-only recovery, run verification in the exact clean source checkout. A dirty index is accepted only when its paths, modes and blob SHA-256 values exactly equal the persisted card-derived signoff manifest; every extra/different staged state is rejected without reset or manual cleanup.

- [ ] **Step 5: Run transaction tests**

```bash
pytest -q tests/test_approval_transaction.py
```

Expected: happy path reaches `pushed`; each injected failure stops at the documented state; retry creates no duplicate commit or signoff.

- [ ] **Step 6: Root review and commit exact files**

```bash
git add -- harness/approval/transaction.py tests/test_approval_transaction.py
git commit -m "feat: orchestrate dialog approval transactions"
```

### Task 6: Add CLI Commands And Chinese Approval Card Rendering

**Files:**
- Create: `harness/approval/service.py`
- Create: `harness/approval/render.py`
- Modify: `harness/engine/cli.py`
- Modify: `tests/test_approval_cli.py`

- [ ] **Step 1: Render the exact user-facing approval card**

`render_approval_card()` returns concise Chinese Markdown containing full card/evaluation/evidence digest, profile gate counts, reviewer, both exact rationales, expiry, remote URL/OID/ref, all ahead commits, source file count/diff stat, manifest path, signoff filenames/supersedes, and the no-overclaim boundary. Its final and only action line is:

```text
回复：批准
```

- [ ] **Step 2: Add service functions with injectable dependencies**

Define the return types and expose these concrete call contracts:

```python
@dataclass(frozen=True)
class PreparedReview:
    card_path: str
    card_id: str
    card_sha256: str
    markdown: str


@dataclass(frozen=True)
class ApprovalOutcome:
    card_id: str
    state: str
    source_commit_oid: str | None
    signoff_commit_oid: str | None
    final_commit_oid: str | None
    remote_oid: str | None
```

- `prepare_dialog_review(root, backend=backend, verifier=verifier)` returns a
  `PreparedReview` containing the immutable card path, card SHA-256 and rendered
  Markdown, and performs no stage/commit/push operation.
- `approve_dialog_card(root, card_id=card.card_id,
  expected_card_sha256=card.card_sha256, reviewer_id="project_owner",
  backend=backend, verifier=verifier)` returns an `ApprovalOutcome` containing
  transaction state and all source/signoff/final OIDs.
- `resume_dialog_push(root, card_id=card.card_id, backend=backend,
  verifier=verifier)` accepts only a persisted
  `local_committed_push_failed` journal and reuses its final OID.

Production construction occurs in one factory; tests inject fakes and never access the real remote.

- [ ] **Step 3: Extend the CLI parser without changing `check`/`render`**

Add `prepare-review`, `approve-card`, and `resume-push`. `prepare-review` requires the exact two profile arguments and `origin/main`; `approve-card` requires `--card-id`, 64-hex `--expected-card-sha256`, and `--reviewer-id project_owner`. Do not add a force, skip-verification, alternate role, release or full-project option.

- [ ] **Step 4: Define exit and output contracts**

Successful prepare and completed push return 0. Stale/expired/rejected state returns 1 with a single recovery action. Internal or subprocess failures return 2 with redacted JSON. `check` remains read-only; `render` remains limited to generated acceptance files.

- [ ] **Step 5: Run CLI tests**

```bash
pytest -q tests/test_approval_cli.py tests/test_harness_pipeline.py
```

Expected: existing CLI behavior is unchanged; prepare has no Git mutation; approve invokes the injected transaction exactly once; unsupported profiles and unsafe flags are parser errors.

- [ ] **Step 6: Root review and commit exact files**

```bash
git add -- harness/approval/service.py harness/approval/render.py \
  harness/engine/cli.py tests/test_approval_cli.py
git commit -m "feat: add dialog approval commands"
```

### Task 7: Document The Operator Workflow And Boundaries

**Files:**
- Modify: `harness/signoffs/README.md`
- Modify: `ops/plans/harness_engineering_plan_v1.0.md`
- Modify: `README.md`
- Modify: `index.md`
- Modify: `RELEASE_NOTES.md`
- Modify: `ops/log.md`

- [ ] **Step 1: Document the one-word protocol and trust boundary**

State that `批准` is valid only after a displayed, unexpired card in the same trusted Codex session; it is not cryptographic identity. Explain bundled profiles, append-only signoffs, push authorization, failure recovery and the fact that generated cards/reports are not evidence.

- [ ] **Step 2: Document scientific exclusions**

Repeat that approval does not cover `release_checkpoint`, `full_project`, Benchmark completion, generation, scoring, ranking or biological validation. Preserve v0.33 as the scientific baseline and `VERSION=1.2.21` until the later release-candidate transition.

- [ ] **Step 3: Append the operations log without claiming execution**

Record implementation and verification only. Do not state that a real card was approved, signoffs were created, or push succeeded before the post-implementation transaction occurs.

- [ ] **Step 4: Run documentation validation**

```bash
python scripts/validate_benchmark_kb.py --no-write-report
git diff --check
```

Expected: 0 errors, 0 warnings, and no whitespace errors.

- [ ] **Step 5: Root review and commit exact files**

```bash
git add -- harness/signoffs/README.md ops/plans/harness_engineering_plan_v1.0.md \
  README.md index.md RELEASE_NOTES.md ops/log.md
git commit -m "docs: describe dialog approval workflow"
```

### Task 8: Independent Review And Full Verification

**Files:**
- Review only: all files changed in Tasks 1-7
- Generated only: `ops/validation/wiki_validation_report.md`

- [ ] **Step 1: Dispatch independent spec and security reviewers**

One reviewer checks every section of the approved design against implementation and tests. A separate security reviewer checks card replay, Git config/hooks, exact staging, clean checkout, remote race, supersession, secret redaction and no-force guarantees. Fix every Critical and Important finding before continuing.

- [ ] **Step 2: Run focused suites**

```bash
pytest -q \
  tests/test_harness_path_policy.py \
  tests/test_harness_signoffs.py \
  tests/test_approval_cards.py \
  tests/test_approval_git_backend.py \
  tests/test_approval_transaction.py \
  tests/test_approval_cli.py
```

- [ ] **Step 3: Run the full suite and project validator twice**

```bash
pytest -q
python scripts/validate_benchmark_kb.py
sha256sum ops/validation/wiki_validation_report.md
python scripts/validate_benchmark_kb.py
sha256sum ops/validation/wiki_validation_report.md
git diff --check
git status -sb
```

Expected: all tests pass, both validator runs have 0 errors/0 warnings, report hashes match, diff check passes.

- [ ] **Step 4: Verify unsigned pre-card profiles and full-project boundary**

```bash
python scripts/run_project_acceptance.py check --profile governance
python scripts/run_project_acceptance.py check --profile current_phase
python scripts/run_project_acceptance.py check --profile full_project
```

Governance/current-phase may be pending because existing signoffs are stale, but must be machine-valid with no invalid signoffs. Full project must remain `not_accepted` with method-readiness and target/control blockers.

- [ ] **Step 5: Stop every subagent before preparing the real card**

Confirm no agent is running and no background process can modify the shared worktree. Do not reuse any prior design/spec approval message.

- [ ] **Step 6: Prepare and display the real approval card**

Run:

```bash
python scripts/run_project_acceptance.py prepare-review \
  --profiles governance current_phase \
  --push-target origin/main
```

Present the rendered card verbatim in the conversation and stop. The next valid action requires a new user message whose complete normalized content is exactly `批准`.

### Task 9: Execute The User-Approved Transaction

**Files:**
- Generated path format: `ops/acceptance/dialog_transactions/approval_0123456789abcdef01234567.json`
- Create and commit: next Governance signoff under `harness/signoffs/`
- Create and commit: first Current Phase signoff under `harness/signoffs/`

- [ ] **Step 1: Validate the fresh exact approval message**

Proceed only when the user message immediately following the card normalizes exactly to `批准`. Any other message invalidates the card and requires a new prepare cycle.

- [ ] **Step 2: Execute approve-card with the in-memory full digest**

```bash
python scripts/run_project_acceptance.py approve-card \
  --card-id "$APPROVAL_CARD_ID" \
  --expected-card-sha256 "$APPROVAL_CARD_SHA256" \
  --reviewer-id project_owner
```

Expected: transaction reaches `pushed`, two profile checks are accepted, remote `refs/heads/main` equals the reported final OID, and no release/full-project signoff is created.

- [ ] **Step 3: Report exact audit identifiers**

Report card ID, approval event ID, evaluation ID, evidence digest, source commit OID if created, signoff commit OID, remote OID, signoff filenames, supersedes relationships, test count and validator status. Do not call the scientific Benchmark complete.
