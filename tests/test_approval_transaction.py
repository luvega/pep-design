from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import pytest

import harness.approval.git_backend as git_backend_module
from harness.approval import transaction as transaction_module
from harness.approval.git_backend import GitBackend, RemoteSnapshot, SourceManifestEntry
from harness.approval.journal import TransactionState
from harness.approval.models import ApprovalError
from harness.approval.transaction import (
    VerificationSnapshot,
    approve_card,
    prepare_review,
    resume_push,
)
from harness.engine.signoffs import SignoffContext, validate_signoff_directory
from tests.approval_git_helpers import (
    ApprovalGitFixture,
    git_stdout,
    init_repo_with_bare_remote,
    install_sanitized_git_environment,
    nul_paths,
    run_git,
)


PREPARED_AT = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
REVIEWED_AT = datetime(2026, 7, 10, 12, 15, 0, tzinfo=timezone.utc)
EXPIRED_AT = PREPARED_AT + timedelta(minutes=61)
NONCE = b"0" * 16
EVENT_ID = "approval_event_" + "a" * 24
EXPECTED_REMOTE_URL = "git@github.com:luvega/pep-design.git"
EXPECTED_REMOTE_REF = "refs/heads/main"
CONTRACT_ID = "pep_design_project_acceptance"
HEAD_OID = "1" * 40
REMOTE_OID = "2" * 40
TREE_OID = "3" * 40
SOURCE_OID = "4" * 40
SIGNOFF_OID = "5" * 40


@dataclass(frozen=True)
class RecordedCall:
    name: str
    args: tuple[object, ...]
    kwargs: tuple[tuple[str, object], ...]


def verification_snapshot() -> VerificationSnapshot:
    return VerificationSnapshot(
        evaluation_id="evaluation_" + "c" * 24,
        evidence_digest="d" * 64,
        contract_digest="a" * 64,
        registry_digest="b" * 64,
        profile_gate_digests=(
            ("governance", "6" * 64),
            ("current_phase", "7" * 64),
        ),
    )


class FakeVerifier:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.snapshot = verification_snapshot()
        self.prepare_results: list[VerificationSnapshot] = []
        self.prepare_error: ApprovalError | None = None
        self.prepare_roots: list[Path] = []
        self.clean_snapshot: VerificationSnapshot | None = None
        self.clean_error: ApprovalError | None = None
        self.accepted_snapshot: VerificationSnapshot | None = None
        self.accepted_error: ApprovalError | None = None
        self.clean_roots: list[Path] = []
        self.rendered_roots: list[Path] = []

    def prepare(self, root: Path) -> VerificationSnapshot:
        self.calls.append("verify.prepare")
        self.prepare_roots.append(root)
        if self.prepare_error is not None:
            raise self.prepare_error
        if self.prepare_results:
            return self.prepare_results.pop(0)
        return self.snapshot

    def clean_checkout(self, root: Path) -> VerificationSnapshot:
        self.calls.append("verify.clean_checkout")
        self.clean_roots.append(root)
        if self.clean_error is not None:
            raise self.clean_error
        return self.clean_snapshot or self.snapshot

    def accepted(self, root: Path) -> VerificationSnapshot:
        self.calls.append("verify.accepted")
        if self.accepted_error is not None:
            raise self.accepted_error
        return self.accepted_snapshot or self.snapshot

    def render_current_phase(self, root: Path) -> None:
        self.calls.append("verify.render_current_phase")
        self.rendered_roots.append(root)


class SignoffValidatingVerifier(FakeVerifier):
    """Use real role/supersession semantics while keeping Git I/O bounded."""

    def __init__(self, calls: list[str], *, production: bool = False) -> None:
        super().__init__(calls)
        self.production = production

    def accepted(self, root: Path) -> VerificationSnapshot:
        snapshot = super().accepted(root)
        for profile_id in ("governance", "current_phase"):
            result = validate_signoff_directory(
                root / "harness/signoffs",
                SignoffContext(
                    contract_id=CONTRACT_ID,
                    contract_version="1.0.0",
                    contract_digest=snapshot.contract_digest,
                    profile_id=profile_id,
                    evaluation_id=snapshot.evaluation_id,
                    evidence_digest=snapshot.evidence_digest,
                    required_roles=("governance_owner",),
                    repository_root=str(root) if self.production else None,
                ),
            )
            if not result.is_complete:
                raise ApprovalError(
                    f"{profile_id} signoff validation failed: "
                    f"duplicates={result.duplicate_roles}, "
                    f"missing={result.missing_roles}"
                )
        return snapshot


class FakeBackend:
    """Precise in-memory double for the GitBackend transaction facade."""

    def __init__(self, root: Path, calls: list[str]) -> None:
        self.root = root
        self.calls = calls
        self.records: list[RecordedCall] = []
        self.remote = RemoteSnapshot(
            name="origin",
            fetch_url=EXPECTED_REMOTE_URL,
            push_url=EXPECTED_REMOTE_URL,
            ref=EXPECTED_REMOTE_REF,
            oid=REMOTE_OID,
            head_oid=HEAD_OID,
            ahead_commits=("0" * 40,),
        )
        self.manifest = (
            SourceManifestEntry(
                path="README.md",
                status="modified",
                mode="100644",
                sha256="8" * 64,
            ),
        )
        self.latest_by_context: dict[tuple[str, str, str], tuple[str, ...]] = {}
        self.require_error: ApprovalError | None = None
        self.customization_error: ApprovalError | None = None
        self.commits: list[str] = []
        self.signoff_commit_calls = 0
        self.push_attempts: list[str] = []
        self.fail_push = False
        self.pushed_oid: str | None = None
        self.head_after_clean: str | None = None
        self.raise_source_after_publish = False
        self.raise_signoff_after_publish = False
        self.source_cas_loser = False
        self.signoff_cas_loser = False
        self.reconcile_failures = 0

    def _record(self, name: str, *args: object, **kwargs: object) -> None:
        self.calls.append(name)
        self.records.append(
            RecordedCall(name, args, tuple(sorted(kwargs.items())))
        )

    def named(self, name: str) -> list[RecordedCall]:
        return [record for record in self.records if record.name == name]

    def require_main_with_clean_index(self) -> None:
        self._record("git.require_main_with_clean_index")
        if self.require_error is not None:
            raise self.require_error

    def require_main_with_clean_or_exact_signoff_index(
        self, expected_manifest: tuple[SourceManifestEntry, ...]
    ) -> bool:
        self._record(
            "git.require_main_with_clean_or_exact_signoff_index",
            expected_manifest,
        )
        if self.require_error is not None:
            raise self.require_error
        return False

    def reject_active_git_customization(self) -> None:
        self._record("git.reject_active_git_customization")
        if self.customization_error is not None:
            raise self.customization_error

    def fetch_remote_snapshot(
        self,
        *,
        remote_name: str,
        expected_url: str,
        ref: str,
    ) -> RemoteSnapshot:
        self._record(
            "git.fetch_remote_snapshot",
            remote_name=remote_name,
            expected_url=expected_url,
            ref=ref,
        )
        return self.remote

    def collect_source_manifest(self) -> tuple[SourceManifestEntry, ...]:
        self._record("git.collect_source_manifest")
        return self.manifest

    def build_proposed_tree(
        self, manifest: tuple[SourceManifestEntry, ...]
    ) -> str:
        self._record("git.build_proposed_tree", manifest)
        return TREE_OID

    def diff_stat(self, manifest: tuple[SourceManifestEntry, ...]) -> str:
        self._record("git.diff_stat", manifest)
        if not manifest:
            return "no source changes"
        return "1 file changed, 1 insertion(+)"

    def latest_committed_signoffs(
        self,
        *,
        contract_id: str,
        contract_version: str,
        contract_digest: str,
        profile_id: str,
        evaluation_id: str,
        evidence_digest: str,
        role: str,
    ) -> tuple[str, ...]:
        self._record(
            "git.latest_committed_signoffs",
            contract_id=contract_id,
            contract_version=contract_version,
            contract_digest=contract_digest,
            profile_id=profile_id,
            evaluation_id=evaluation_id,
            evidence_digest=evidence_digest,
            role=role,
        )
        return self.latest_by_context.get(
            (contract_id, profile_id, role), ()
        )

    def stage_exact_manifest(
        self, manifest: tuple[SourceManifestEntry, ...]
    ) -> None:
        self._record("git.stage_exact_manifest", manifest)

    def commit_source(
        self,
        manifest: tuple[SourceManifestEntry, ...],
        card_id: str,
        expected_parent_oid: str | None = None,
    ) -> str:
        self._record(
            "git.commit_source",
            manifest,
            card_id,
            expected_parent_oid=expected_parent_oid,
        )
        if expected_parent_oid != self.remote.head_oid:
            raise ApprovalError("source parent moved")
        if self.source_cas_loser:
            self.remote = replace(self.remote, head_oid="9" * 40)
            raise ApprovalError("source CAS lost to another commit")
        self.commits.append(SOURCE_OID)
        self.remote = replace(self.remote, head_oid=SOURCE_OID)
        if self.raise_source_after_publish:
            raise ApprovalError("ambiguous source commit result")
        return SOURCE_OID

    def commit_tree_oid(self, commit_oid: str) -> str:
        self._record("git.commit_tree_oid", commit_oid)
        return TREE_OID

    def current_head_oid(self) -> str:
        self._record("git.current_head_oid")
        return self.remote.head_oid

    def reconcile_card_commit(
        self,
        expected_parent_oid: str,
        card_id: str,
        expected_paths: tuple[str, ...],
        *,
        expected_tree_oid: str | None = None,
        expected_manifest: tuple[SourceManifestEntry, ...] | None = None,
    ) -> str | None:
        self._record(
            "git.reconcile_card_commit",
            expected_parent_oid,
            card_id,
            expected_paths,
            expected_tree_oid=expected_tree_oid,
            expected_manifest=expected_manifest,
        )
        if self.reconcile_failures:
            self.reconcile_failures -= 1
            raise ApprovalError("transient commit reconciliation failure")
        if self.remote.head_oid == expected_parent_oid:
            return None
        if (
            self.remote.head_oid == SOURCE_OID
            and expected_parent_oid == HEAD_OID
            and tuple(entry.path for entry in self.manifest) == expected_paths
            and expected_tree_oid == TREE_OID
            and expected_manifest == self.manifest
        ):
            return SOURCE_OID
        if (
            self.remote.head_oid == SIGNOFF_OID
            and expected_parent_oid in {HEAD_OID, SOURCE_OID}
            and expected_manifest is not None
            and tuple(sorted(expected_paths))
            == tuple(entry.path for entry in expected_manifest)
        ):
            return SIGNOFF_OID
        raise ApprovalError("ambiguous commit could not be reconciled")

    def temporary_clean_worktree(
        self,
        source_oid: str,
        callback: Callable[[Path], VerificationSnapshot],
    ) -> VerificationSnapshot:
        self._record("git.temporary_clean_worktree", source_oid, callback)
        clean_root = self.root / ".fake-clean-checkout"
        clean_root.mkdir(parents=True, exist_ok=True)
        self.calls.append("git.clean_worktree.enter")
        try:
            return callback(clean_root)
        finally:
            self.calls.append("git.clean_worktree.exit")
            if self.head_after_clean is not None:
                self.remote = replace(
                    self.remote, head_oid=self.head_after_clean
                )

    def commit_signoffs(
        self,
        signoff_paths: tuple[str, ...],
        card_id: str,
        expected_parent_oid: str | None = None,
        expected_manifest: tuple[SourceManifestEntry, ...] | None = None,
        *,
        allow_exact_prestaged: bool = False,
    ) -> str:
        self._record(
            "git.commit_signoffs",
            signoff_paths,
            card_id,
            expected_parent_oid=expected_parent_oid,
            expected_manifest=expected_manifest,
            allow_exact_prestaged=allow_exact_prestaged,
        )
        if expected_parent_oid != self.remote.head_oid:
            raise ApprovalError("signoff parent moved")
        if self.signoff_cas_loser:
            self.remote = replace(self.remote, head_oid="9" * 40)
            raise ApprovalError("signoff CAS lost to another commit")
        self.signoff_commit_calls += 1
        self.commits.append(SIGNOFF_OID)
        self.remote = replace(self.remote, head_oid=SIGNOFF_OID)
        if self.raise_signoff_after_publish:
            raise ApprovalError("ambiguous signoff commit result")
        return SIGNOFF_OID

    def push_exact(
        self, final_oid: str, expected_remote: RemoteSnapshot
    ) -> str:
        self._record("git.push_exact", final_oid, expected_remote)
        self.push_attempts.append(final_oid)
        if self.fail_push:
            raise ApprovalError("push failed")
        self.pushed_oid = final_oid
        self.remote = replace(self.remote, oid=final_oid, head_oid=final_oid)
        return final_oid


def write_minimal_contract(root: Path) -> None:
    contract = root / "harness/contracts/project_acceptance_v1.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        json.dumps(
            {
                "contract_id": CONTRACT_ID,
                "contract_version": "1.0.0",
                "evaluator_version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )
    (root / "harness/signoffs").mkdir(parents=True, exist_ok=True)


def prepare(
    root: Path,
    backend: FakeBackend,
    verifier: FakeVerifier,
):
    write_minimal_contract(root)
    return prepare_review(
        root,
        backend=backend,
        verifier=verifier,
        now=PREPARED_AT,
        nonce=NONCE,
    )


def prepared_card(value: object) -> object:
    card = getattr(value, "card", None)
    if card is not None:
        return card
    if isinstance(value, tuple) and value:
        return value[0]
    raise AssertionError("prepare_review must return the prepared card")


def journal_path(root: Path, card_id: str) -> Path:
    return root / "ops/acceptance/dialog_transactions" / f"{card_id}.json"


def card_path(root: Path, card_id: str) -> Path:
    return root / "ops/acceptance/dialog_cards" / f"{card_id}.json"


def profile_map(card: object) -> dict[str, object]:
    return {
        profile.profile_id: profile
        for profile in getattr(card, "profiles")
    }


def signoff_paths(root: Path, card: object) -> tuple[Path, Path]:
    profiles = profile_map(card)
    return (
        root / "harness/signoffs" / profiles["governance"].signoff_filename,
        root
        / "harness/signoffs"
        / profiles["current_phase"].signoff_filename,
    )


def read_state(root: Path, card_id: str) -> str:
    return json.loads(journal_path(root, card_id).read_text(encoding="utf-8"))[
        "state"
    ]


def assert_order(calls: list[str], expected: tuple[str, ...]) -> None:
    cursor = 0
    for item in expected:
        try:
            cursor = calls.index(item, cursor) + 1
        except ValueError as exc:
            raise AssertionError(
                f"missing ordered call {item!r} after position {cursor}: {calls}"
            ) from exc


def one_shot_event_id() -> tuple[Callable[[], str], list[int]]:
    calls: list[int] = []

    def factory() -> str:
        calls.append(1)
        if len(calls) > 1:
            raise AssertionError("approval event ID generated more than once")
        return EVENT_ID

    return factory, calls


def approve(
    root: Path,
    card: object,
    backend: FakeBackend,
    verifier: FakeVerifier,
    *,
    now: datetime = REVIEWED_AT,
    expected_digest: str | None = None,
    event_id_factory: Callable[[], str] | None = None,
):
    digest = expected_digest or getattr(card, "card_sha256")
    factory = event_id_factory or (lambda: EVENT_ID)
    return approve_card(
        root,
        card_id=getattr(card, "card_id"),
        expected_card_sha256=digest,
        reviewer_id="project_owner",
        backend=backend,
        verifier=verifier,
        now=now,
        event_id_factory=factory,
    )


def assert_no_git_or_signoff_side_effects(
    root: Path, backend: FakeBackend, calls: list[str]
) -> None:
    assert "git.stage_exact_manifest" not in calls
    assert "git.commit_source" not in calls
    assert "git.commit_signoffs" not in calls
    assert "git.push_exact" not in calls
    assert backend.commits == []
    assert backend.signoff_commit_calls == 0
    assert backend.push_attempts == []
    signoff_root = root / "harness/signoffs"
    generated = (
        tuple(signoff_root.glob("signoff_governance_v*.json"))
        + tuple(signoff_root.glob("signoff_current_phase_v*.json"))
    )
    assert generated == ()


def test_prepare_review_is_read_only_and_records_exact_backend_arguments(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)

    prepared = prepare(tmp_path, backend, verifier)
    card = prepared_card(prepared)

    assert card_path(tmp_path, card.card_id).is_file()
    assert journal_path(tmp_path, card.card_id).is_file()
    assert read_state(tmp_path, card.card_id) == "prepared"
    assert backend.commits == []
    assert backend.push_attempts == []
    assert "git.stage_exact_manifest" not in calls
    assert backend.named("git.fetch_remote_snapshot") == [
        RecordedCall(
            "git.fetch_remote_snapshot",
            (),
            (
                ("expected_url", EXPECTED_REMOTE_URL),
                ("ref", EXPECTED_REMOTE_REF),
                ("remote_name", "origin"),
            ),
        )
    ]
    assert backend.named("git.build_proposed_tree")[0].args == (
        backend.manifest,
    )
    assert backend.named("git.diff_stat")[0].args == (backend.manifest,)
    assert_order(
        calls,
        (
            "git.require_main_with_clean_index",
            "git.reject_active_git_customization",
            "git.fetch_remote_snapshot",
            "verify.prepare",
            "git.collect_source_manifest",
            "git.build_proposed_tree",
        ),
    )


def test_prepare_uses_max_plus_one_and_only_newest_committed_same_context(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    write_minimal_contract(tmp_path)
    signoff_root = tmp_path / "harness/signoffs"
    for filename in (
        "signoff_governance_v1.json",
        "signoff_governance_v2.json",
        "signoff_governance_v3.json",
        "signoff_current_phase_v1.json",
        "signoff_current_phase_v7.json",
        "signoff_governance_vnot-a-number.json",
    ):
        (signoff_root / filename).write_text("{}\n", encoding="utf-8")
    (signoff_root / "signoff_governance_v2.json").write_text(
        json.dumps(
            {
                "contract_id": CONTRACT_ID,
                "profile_id": "governance",
                "role": "governance_owner",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    backend.latest_by_context[(CONTRACT_ID, "governance", "governance_owner")] = (
        "signoff_governance_v2.json",
        "signoff_governance_v1.json",
    )
    backend.latest_by_context[(CONTRACT_ID, "current_phase", "governance_owner")] = (
        "signoff_current_phase_v7.json",
        "signoff_current_phase_v1.json",
    )

    card = prepared_card(
        prepare_review(
            tmp_path,
            backend=backend,
            verifier=verifier,
            now=PREPARED_AT,
            nonce=NONCE,
        )
    )
    profiles = profile_map(card)

    assert profiles["governance"].signoff_filename == "signoff_governance_v4.json"
    assert profiles["governance"].supersedes == "signoff_governance_v2.json"
    assert (signoff_root / profiles["governance"].supersedes).is_file()
    assert "signoff_governance_v3.json" not in backend.latest_by_context[
        (CONTRACT_ID, "governance", "governance_owner")
    ]
    assert profiles["current_phase"].signoff_filename == "signoff_current_phase_v8.json"
    assert profiles["current_phase"].supersedes == "signoff_current_phase_v7.json"
    assert backend.named("git.latest_committed_signoffs") == [
        RecordedCall(
            "git.latest_committed_signoffs",
            (),
            (
                ("contract_digest", "a" * 64),
                ("contract_id", CONTRACT_ID),
                ("contract_version", "1.0.0"),
                ("evaluation_id", "evaluation_" + "c" * 24),
                ("evidence_digest", "d" * 64),
                ("profile_id", "governance"),
                ("role", "governance_owner"),
            ),
        ),
        RecordedCall(
            "git.latest_committed_signoffs",
            (),
            (
                ("contract_digest", "a" * 64),
                ("contract_id", CONTRACT_ID),
                ("contract_version", "1.0.0"),
                ("evaluation_id", "evaluation_" + "c" * 24),
                ("evidence_digest", "d" * 64),
                ("profile_id", "current_phase"),
                ("role", "governance_owner"),
            ),
        ),
    ]


def test_second_cycle_rejects_untrusted_newer_stale_dialog_signoff(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    backend.manifest = ()
    verifier = SignoffValidatingVerifier(calls)
    write_minimal_contract(tmp_path)

    first = prepared_card(
        prepare_review(
            tmp_path,
            backend=backend,
            verifier=verifier,
            now=PREPARED_AT,
            nonce=b"0" * 16,
        )
    )
    first_result = approve(
        tmp_path,
        first,
        backend,
        verifier,
        now=REVIEWED_AT,
        event_id_factory=lambda: "approval_event_" + "1" * 24,
    )
    assert first_result.state is TransactionState.PUSHED

    first_profiles = profile_map(first)
    backend.latest_by_context[
        (CONTRACT_ID, "governance", "governance_owner")
    ] = (first_profiles["governance"].signoff_filename,)

    stale_current_filename = "signoff_current_phase_v2.json"
    first_current_path = (
        tmp_path
        / "harness/signoffs"
        / first_profiles["current_phase"].signoff_filename
    )
    stale_current = json.loads(first_current_path.read_text(encoding="utf-8"))
    stale_current["evaluation_id"] = "evaluation_" + "e" * 24
    stale_current["evidence_digest"] = "f" * 64
    (tmp_path / "harness/signoffs" / stale_current_filename).write_text(
        json.dumps(stale_current) + "\n",
        encoding="utf-8",
    )
    backend.latest_by_context[
        (CONTRACT_ID, "current_phase", "governance_owner")
    ] = (
        first_profiles["current_phase"].signoff_filename,
        stale_current_filename,
    )

    second = prepared_card(
        prepare_review(
            tmp_path,
            backend=backend,
            verifier=verifier,
            now=PREPARED_AT + timedelta(minutes=20),
            nonce=b"1" * 16,
        )
    )
    second_profiles = profile_map(second)

    assert second_profiles["governance"].supersedes == (
        first_profiles["governance"].signoff_filename
    )
    assert second_profiles["current_phase"].supersedes == (
        first_profiles["current_phase"].signoff_filename
    )
    assert second_profiles["current_phase"].signoff_filename == (
        "signoff_current_phase_v3.json"
    )

    with pytest.raises(ApprovalError, match="signoff validation failed"):
        approve(
            tmp_path,
            second,
            backend,
            verifier,
            now=REVIEWED_AT + timedelta(minutes=20),
            event_id_factory=lambda: "approval_event_" + "2" * 24,
        )

    validation = validate_signoff_directory(
        tmp_path / "harness/signoffs",
        SignoffContext(
            contract_id=CONTRACT_ID,
            contract_version="1.0.0",
            contract_digest=verifier.snapshot.contract_digest,
            profile_id="current_phase",
            evaluation_id=verifier.snapshot.evaluation_id,
            evidence_digest=verifier.snapshot.evidence_digest,
            required_roles=("governance_owner",),
        ),
    )
    assert [
        issue.reason_code
        for issue in validation.invalid_signoffs
        if issue.path == stale_current_filename
    ] == ["signoff_approval_binding_invalid"]


def test_approve_card_uses_callback_clean_checkout_and_renders_after_accepted(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    calls.clear()
    backend.records.clear()
    event_id_factory, event_calls = one_shot_event_id()

    result = approve(
        tmp_path,
        card,
        backend,
        verifier,
        event_id_factory=event_id_factory,
    )

    result_state = getattr(result, "state")
    assert getattr(result_state, "value", result_state) == "pushed"
    assert read_state(tmp_path, card.card_id) == "pushed"
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.push_attempts == [SIGNOFF_OID]
    assert event_calls == [1]
    assert verifier.clean_roots == [tmp_path / ".fake-clean-checkout"]
    assert verifier.clean_roots[0] != tmp_path
    assert verifier.rendered_roots == [tmp_path]
    clean_call = backend.named("git.temporary_clean_worktree")
    assert len(clean_call) == 1
    assert clean_call[0].args[0] == SOURCE_OID
    assert callable(clean_call[0].args[1])
    assert backend.named("git.stage_exact_manifest")[0].args == (
        backend.manifest,
    )
    assert backend.named("git.commit_source")[0].args == (
        backend.manifest,
        card.card_id,
    )
    assert dict(backend.named("git.commit_source")[0].kwargs) == {
        "expected_parent_oid": HEAD_OID
    }
    signoff_call = backend.named("git.commit_signoffs")[0]
    assert signoff_call.args[1] == card.card_id
    assert signoff_call.args[0] == tuple(
        path.relative_to(tmp_path).as_posix()
        for path in signoff_paths(tmp_path, card)
    )
    signoff_kwargs = dict(signoff_call.kwargs)
    assert signoff_kwargs["expected_parent_oid"] == SOURCE_OID
    expected_signoff_manifest = transaction_module._expected_signoff_manifest(
        card, reviewed_at=REVIEWED_AT.isoformat(), event_id=EVENT_ID
    )
    assert signoff_kwargs["expected_manifest"] == expected_signoff_manifest
    assert tuple(entry.path for entry in expected_signoff_manifest) == tuple(
        sorted(path.relative_to(tmp_path).as_posix() for path in signoff_paths(tmp_path, card))
    )
    for entry in expected_signoff_manifest:
        assert entry.status == "untracked"
        assert entry.mode == "100644"
        assert entry.sha256 is not None and len(entry.sha256) == 64
    assert backend.named("git.push_exact")[0].args == (
        SIGNOFF_OID,
        card_remote_snapshot(card),
    )
    assert_order(
        calls,
        (
            "git.require_main_with_clean_index",
            "git.reject_active_git_customization",
            "git.fetch_remote_snapshot",
            "verify.prepare",
            "git.collect_source_manifest",
            "git.build_proposed_tree",
            "git.stage_exact_manifest",
            "git.commit_source",
            "git.commit_tree_oid",
            "verify.prepare",
            "git.clean_worktree.enter",
            "verify.clean_checkout",
            "git.clean_worktree.exit",
            "git.commit_signoffs",
            "verify.accepted",
            "verify.render_current_phase",
            "git.fetch_remote_snapshot",
            "git.push_exact",
        ),
    )


def card_remote_snapshot(card: object) -> RemoteSnapshot:
    return RemoteSnapshot(
        name=getattr(card, "remote_name"),
        fetch_url=getattr(card, "remote_url"),
        push_url=getattr(card, "remote_url"),
        ref=getattr(card, "remote_ref"),
        oid=getattr(card, "remote_oid"),
        head_oid=getattr(card, "head_oid"),
        ahead_commits=tuple(getattr(card, "ahead_commits")),
    )


def test_empty_source_manifest_uses_existing_head_without_source_commit(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    backend.manifest = ()
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    calls.clear()
    backend.records.clear()

    result = approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "pushed"
    assert getattr(result, "source_commit_oid") is None
    assert backend.commits == [SIGNOFF_OID]
    assert backend.named("git.stage_exact_manifest") == []
    assert backend.named("git.commit_source") == []
    assert backend.named("git.temporary_clean_worktree")[0].args[0] == HEAD_OID
    tree_calls = backend.named("git.commit_tree_oid")
    if tree_calls:
        assert tree_calls[0].args == (HEAD_OID,)
    assert verifier.clean_roots == [tmp_path / ".fake-clean-checkout"]
    assert backend.named("git.commit_signoffs")[0].args[1] == card.card_id
    assert backend.named("git.push_exact")[0].args == (
        SIGNOFF_OID,
        card_remote_snapshot(card),
    )


def test_absent_card_has_no_git_or_signoff_side_effects(tmp_path: Path) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    write_minimal_contract(tmp_path)

    with pytest.raises(ApprovalError, match="card|missing|not found"):
        approve_card(
            tmp_path,
            card_id="approval_" + "f" * 24,
            expected_card_sha256="e" * 64,
            reviewer_id="project_owner",
            backend=backend,
            verifier=verifier,
            now=REVIEWED_AT,
            event_id_factory=lambda: EVENT_ID,
        )

    assert calls == []
    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


def test_wrong_expected_digest_has_no_git_or_signoff_side_effects(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    calls.clear()

    with pytest.raises(ApprovalError, match="digest|sha|card"):
        approve(
            tmp_path,
            card,
            backend,
            verifier,
            expected_digest="f" * 64,
        )

    assert read_state(tmp_path, card.card_id) in {"prepared", "invalidated"}
    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


def test_tampered_card_has_no_git_or_signoff_side_effects(tmp_path: Path) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    path = card_path(tmp_path, card.card_id)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["reviewer_id"] = "tampered-reviewer"
    path.write_text(json.dumps(raw), encoding="utf-8")
    calls.clear()

    with pytest.raises(ApprovalError, match="tamper|digest|integrity|card"):
        approve(tmp_path, card, backend, verifier)

    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


def test_expired_card_has_no_git_or_signoff_side_effects(tmp_path: Path) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    calls.clear()

    with pytest.raises(ApprovalError, match="expired|expiry|card"):
        approve(tmp_path, card, backend, verifier, now=EXPIRED_AT)

    assert read_state(tmp_path, card.card_id) in {"prepared", "invalidated"}
    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


def test_dirty_index_has_no_git_or_signoff_side_effects(tmp_path: Path) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.require_error = ApprovalError("dirty index")
    calls.clear()

    with pytest.raises(ApprovalError, match="index"):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "invalidated"
    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


@pytest.mark.parametrize(
    ("field", "replacement", "match"),
    [
        ("head_oid", "9" * 40, "HEAD|head"),
        ("fetch_url", "git@example.test:other/repo.git", "url|remote"),
        ("push_url", "git@example.test:other/repo.git", "url|remote"),
        ("oid", "9" * 40, "oid|remote|moved"),
        ("ref", "refs/heads/other", "ref|remote"),
    ],
)
def test_head_or_remote_binding_drift_has_no_git_or_signoff_side_effects(
    tmp_path: Path, field: str, replacement: str, match: str
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.remote = replace(backend.remote, **{field: replacement})
    calls.clear()

    with pytest.raises(ApprovalError, match=match):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "invalidated"
    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("evaluation_id", "evaluation_" + "e" * 24),
        ("evidence_digest", "e" * 64),
        ("contract_digest", "e" * 64),
        ("registry_digest", "e" * 64),
        (
            "profile_gate_digests",
            (("governance", "e" * 64), ("current_phase", "7" * 64)),
        ),
    ],
)
def test_verification_identity_drift_is_detected_before_git_mutation(
    tmp_path: Path, field: str, replacement: object
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    verifier.snapshot = replace(verifier.snapshot, **{field: replacement})
    calls.clear()

    with pytest.raises(
        ApprovalError, match="evaluation|evidence|contract|registry|gate|identity|drift"
    ):
        approve(tmp_path, card, backend, verifier)

    assert "verify.prepare" in calls
    assert read_state(tmp_path, card.card_id) == "invalidated"
    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


def test_failed_machine_gate_is_rejected_before_git_mutation(tmp_path: Path) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    verifier.prepare_error = ApprovalError("governance gate did not pass")
    calls.clear()

    with pytest.raises(ApprovalError, match="gate|pass"):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "invalidated"
    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


def test_manifest_drift_invalidates_before_stage_commit_or_push(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.manifest = (
        SourceManifestEntry(
            path="README.md",
            status="modified",
            mode="100644",
            sha256="9" * 64,
        ),
    )
    calls.clear()

    with pytest.raises(ApprovalError, match="manifest|drift|card|source"):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "invalidated"
    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


def test_post_source_identity_drift_stops_before_signoff_and_push(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    verifier.prepare_results = [
        verifier.snapshot,
        replace(
            verifier.snapshot,
            evaluation_id="evaluation_" + "e" * 24,
        ),
    ]
    calls.clear()

    with pytest.raises(ApprovalError, match="evaluation|identity|drift"):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    assert backend.commits == [SOURCE_OID]
    assert backend.signoff_commit_calls == 0
    assert backend.push_attempts == []
    assert "git.commit_signoffs" not in calls
    assert "git.push_exact" not in calls
    assert all(not path.exists() for path in signoff_paths(tmp_path, card))


@pytest.mark.parametrize("failure_kind", ["identity-mismatch", "runner-failure"])
def test_clean_checkout_failure_stops_before_signoff_and_push(
    tmp_path: Path, failure_kind: str
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    if failure_kind == "identity-mismatch":
        verifier.clean_snapshot = replace(
            verifier.snapshot,
            evidence_digest="e" * 64,
        )
    else:
        verifier.clean_error = ApprovalError("clean checkout verification failed")
    calls.clear()

    with pytest.raises(
        ApprovalError,
        match="clean|checkout|evidence|identity|verification|drift",
    ):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    assert backend.commits == [SOURCE_OID]
    assert backend.signoff_commit_calls == 0
    assert backend.push_attempts == []
    assert "verify.clean_checkout" in calls
    assert "git.commit_signoffs" not in calls
    assert "git.push_exact" not in calls
    assert all(not path.exists() for path in signoff_paths(tmp_path, card))


@pytest.mark.parametrize("failure_kind", ["identity-mismatch", "runner-failure"])
def test_accepted_failure_preserves_one_signoff_commit_and_resume_reuses_it(
    tmp_path: Path, failure_kind: str
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    if failure_kind == "identity-mismatch":
        verifier.accepted_snapshot = replace(
            verifier.snapshot,
            profile_gate_digests=(
                ("governance", "e" * 64),
                ("current_phase", "7" * 64),
            ),
        )
    else:
        verifier.accepted_error = ApprovalError("accepted profile check failed")
    calls.clear()

    with pytest.raises(
        ApprovalError,
        match="accepted|profile|gate|identity|verification|drift|check",
    ):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1
    assert backend.push_attempts == []
    paths = signoff_paths(tmp_path, card)
    before = tuple(path.read_bytes() for path in paths)
    assert len(before) == 2
    assert "verify.render_current_phase" not in calls
    assert "git.push_exact" not in calls

    verifier.accepted_snapshot = None
    verifier.accepted_error = None
    calls.clear()
    resume_push(
        tmp_path,
        card_id=card.card_id,
        backend=backend,
        verifier=verifier,
    )

    assert read_state(tmp_path, card.card_id) == "pushed"
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1
    assert tuple(path.read_bytes() for path in paths) == before
    assert backend.push_attempts == [SIGNOFF_OID]
    assert "git.commit_source" not in calls
    assert "git.commit_signoffs" not in calls


def test_push_failure_preserves_commits_and_resume_creates_no_duplicates(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.fail_push = True
    event_id_factory, event_calls = one_shot_event_id()

    with pytest.raises(ApprovalError, match="push"):
        approve(
            tmp_path,
            card,
            backend,
            verifier,
            event_id_factory=event_id_factory,
        )

    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1
    assert event_calls == [1]
    paths = signoff_paths(tmp_path, card)
    assert all(path.is_file() for path in paths)
    before = tuple(path.read_bytes() for path in paths)
    journal_before = json.loads(
        journal_path(tmp_path, card.card_id).read_text(encoding="utf-8")
    )
    assert journal_before["approval_event_id"] == EVENT_ID
    assert journal_before["reviewed_at"] == REVIEWED_AT.isoformat()
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    assert {payload["approval_event_id"] for payload in payloads} == {EVENT_ID}
    assert {payload["reviewed_at"] for payload in payloads} == {
        REVIEWED_AT.isoformat()
    }

    backend.fail_push = False
    calls.clear()
    resumed = resume_push(
        tmp_path,
        card_id=card.card_id,
        backend=backend,
        verifier=verifier,
    )

    resumed_state = getattr(resumed, "state")
    assert getattr(resumed_state, "value", resumed_state) == "pushed"
    assert read_state(tmp_path, card.card_id) == "pushed"
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1
    assert tuple(path.read_bytes() for path in paths) == before
    assert backend.push_attempts == [SIGNOFF_OID, SIGNOFF_OID]
    assert "git.commit_source" not in calls
    assert "git.commit_signoffs" not in calls
    assert_order(
        calls,
        (
            "verify.accepted",
            "git.fetch_remote_snapshot",
            "git.push_exact",
        ),
    )

    with pytest.raises(ApprovalError, match="state|pushed|resume"):
        resume_push(
            tmp_path,
            card_id=card.card_id,
            backend=backend,
            verifier=verifier,
        )
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1
    assert tuple(path.read_bytes() for path in paths) == before
    assert backend.push_attempts == [SIGNOFF_OID, SIGNOFF_OID]


def test_resume_remote_movement_does_not_push_or_duplicate_signoffs(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.fail_push = True

    with pytest.raises(ApprovalError, match="push"):
        approve(tmp_path, card, backend, verifier)

    paths = signoff_paths(tmp_path, card)
    before = tuple(path.read_bytes() for path in paths)
    commits_before = tuple(backend.commits)
    attempts_before = tuple(backend.push_attempts)
    backend.fail_push = False
    backend.remote = replace(backend.remote, oid="9" * 40)
    calls.clear()

    with pytest.raises(ApprovalError, match="remote|moved|oid"):
        resume_push(
            tmp_path,
            card_id=card.card_id,
            backend=backend,
            verifier=verifier,
        )

    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    assert tuple(backend.commits) == commits_before
    assert backend.signoff_commit_calls == 1
    assert tuple(path.read_bytes() for path in paths) == before
    assert tuple(backend.push_attempts) == attempts_before
    assert "git.commit_source" not in calls
    assert "git.commit_signoffs" not in calls
    assert "git.push_exact" not in calls


@pytest.mark.parametrize(
    ("target_state", "timing"),
    [
        (TransactionState.SOURCE_COMMITTED, "before"),
        (TransactionState.SOURCE_COMMITTED, "after"),
        (TransactionState.SIGNOFFS_COMMITTED, "before"),
        (TransactionState.SIGNOFFS_COMMITTED, "after"),
    ],
)
def test_commit_to_journal_failure_is_reconciled_without_duplicate_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_state: TransactionState,
    timing: str,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    real_transition = transaction_module.transition_journal
    injected = False

    def flaky_transition(*args: object, **kwargs: object):
        nonlocal injected
        if kwargs.get("new_state") is target_state and not injected:
            injected = True
            if timing == "after":
                real_transition(*args, **kwargs)
            raise ApprovalError(f"injected {timing}-replace journal failure")
        return real_transition(*args, **kwargs)

    monkeypatch.setattr(transaction_module, "transition_journal", flaky_transition)

    result = approve(tmp_path, card, backend, verifier)

    assert result.state is TransactionState.PUSHED
    assert injected is True
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1
    assert backend.push_attempts == [SIGNOFF_OID]


@pytest.mark.parametrize(
    "target_state",
    [TransactionState.SOURCE_COMMITTED, TransactionState.SIGNOFFS_COMMITTED],
)
def test_repeated_commit_journal_failures_persist_oid_for_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_state: TransactionState,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    real_transition = transaction_module.transition_journal
    attempts = 0

    def twice_failing_transition(*args: object, **kwargs: object):
        nonlocal attempts
        if kwargs.get("new_state") is target_state and attempts < 2:
            attempts += 1
            raise ApprovalError("injected durable journal failure")
        return real_transition(*args, **kwargs)

    monkeypatch.setattr(
        transaction_module, "transition_journal", twice_failing_transition
    )
    with pytest.raises(ApprovalError, match="journal|resume"):
        approve(tmp_path, card, backend, verifier)

    raw = json.loads(journal_path(tmp_path, card.card_id).read_text(encoding="utf-8"))
    assert raw["state"] == "local_committed_push_failed"
    assert raw["source_commit_oid"] == SOURCE_OID
    if target_state is TransactionState.SIGNOFFS_COMMITTED:
        assert raw["final_commit_oid"] == SIGNOFF_OID
        assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    else:
        assert raw["final_commit_oid"] is None
        assert backend.commits == [SOURCE_OID]

    resumed = resume_push(
        tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
    )

    assert resumed.state is TransactionState.PUSHED
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1


@pytest.mark.parametrize("ambiguous_commit", ["source", "signoff"])
def test_ambiguous_commit_exception_reconciles_exact_card_commit(
    tmp_path: Path, ambiguous_commit: str
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    if ambiguous_commit == "source":
        backend.raise_source_after_publish = True
    else:
        backend.raise_signoff_after_publish = True

    result = approve(tmp_path, card, backend, verifier)

    assert result.state is TransactionState.PUSHED
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1
    reconcile_calls = backend.named("git.reconcile_card_commit")
    assert len(reconcile_calls) == 1
    reconciliation = reconcile_calls[0]
    if ambiguous_commit == "source":
        assert reconciliation.args == (
            HEAD_OID,
            card.card_id,
            tuple(entry.path for entry in backend.manifest),
        )
        assert dict(reconciliation.kwargs) == {
            "expected_manifest": backend.manifest,
            "expected_tree_oid": TREE_OID,
        }
    else:
        assert reconciliation.args[0] == SOURCE_OID
        assert reconciliation.args[1] == card.card_id
        assert reconciliation.args[2] == tuple(
            path.relative_to(tmp_path).as_posix()
            for path in signoff_paths(tmp_path, card)
        )
        kwargs = dict(reconciliation.kwargs)
        assert kwargs["expected_tree_oid"] is None
        assert kwargs["expected_manifest"] == transaction_module._expected_signoff_manifest(
            card, reviewed_at=REVIEWED_AT.isoformat(), event_id=EVENT_ID
        )


@pytest.mark.parametrize("ambiguous_commit", ["source", "signoff"])
def test_transient_reconcile_failure_persists_observed_oid_then_resumes(
    tmp_path: Path, ambiguous_commit: str
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.reconcile_failures = 1
    if ambiguous_commit == "source":
        backend.raise_source_after_publish = True
        expected_observed_oid = SOURCE_OID
    else:
        backend.raise_signoff_after_publish = True
        expected_observed_oid = SIGNOFF_OID

    with pytest.raises(ApprovalError, match="ambiguous|reconciliation"):
        approve(tmp_path, card, backend, verifier)

    raw = json.loads(journal_path(tmp_path, card.card_id).read_text(encoding="utf-8"))
    assert raw["state"] == "local_committed_push_failed"
    if ambiguous_commit == "source":
        assert raw["source_commit_oid"] == expected_observed_oid
        assert raw["final_commit_oid"] is None
    else:
        assert raw["final_commit_oid"] == expected_observed_oid

    if ambiguous_commit == "source":
        backend.raise_source_after_publish = False
    else:
        backend.raise_signoff_after_publish = False
    resumed = resume_push(
        tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
    )

    assert resumed.state is TransactionState.PUSHED
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1


@pytest.mark.parametrize("cas_loser", ["source", "signoff"])
def test_cas_loser_with_unverifiable_head_stays_fail_closed_on_resume(
    tmp_path: Path, cas_loser: str
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    if cas_loser == "source":
        backend.source_cas_loser = True
    else:
        backend.signoff_cas_loser = True

    with pytest.raises(ApprovalError, match="ambiguous|reconciliation"):
        approve(tmp_path, card, backend, verifier)

    raw = json.loads(journal_path(tmp_path, card.card_id).read_text(encoding="utf-8"))
    assert raw["state"] == "local_committed_push_failed"
    observed_field = (
        "source_commit_oid" if cas_loser == "source" else "final_commit_oid"
    )
    assert raw[observed_field] == "9" * 40
    calls_before = tuple(backend.commits)

    with pytest.raises(ApprovalError, match="reconcil|exact|commit"):
        resume_push(
            tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
        )

    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    assert tuple(backend.commits) == calls_before
    assert backend.push_attempts == []


def test_after_replace_invalidation_transition_is_reconciled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.require_error = ApprovalError("dirty index")
    real_transition = transaction_module.transition_journal
    injected = False

    def after_replace_failure(*args: object, **kwargs: object):
        nonlocal injected
        result = real_transition(*args, **kwargs)
        if kwargs.get("new_state") is TransactionState.INVALIDATED and not injected:
            injected = True
            raise ApprovalError("injected after-replace invalidation failure")
        return result

    monkeypatch.setattr(
        transaction_module, "transition_journal", after_replace_failure
    )

    with pytest.raises(ApprovalError, match="dirty index"):
        approve(tmp_path, card, backend, verifier)

    assert injected is True
    assert read_state(tmp_path, card.card_id) == "invalidated"


def test_push_succeeded_but_final_journal_failed_resumes_without_second_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    real_transition = transaction_module.transition_journal

    def fail_pushed_transition(*args: object, **kwargs: object):
        if kwargs.get("new_state") is TransactionState.PUSHED:
            raise ApprovalError("injected final journal failure")
        return real_transition(*args, **kwargs)

    monkeypatch.setattr(
        transaction_module, "transition_journal", fail_pushed_transition
    )
    with pytest.raises(ApprovalError, match="journal"):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "verified"
    assert backend.remote.oid == SIGNOFF_OID
    assert backend.push_attempts == [SIGNOFF_OID]

    monkeypatch.setattr(transaction_module, "transition_journal", real_transition)
    resumed = resume_push(
        tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
    )

    assert resumed.state is TransactionState.PUSHED
    assert backend.push_attempts == [SIGNOFF_OID]


@pytest.mark.parametrize("operation", ["approve", "resume"])
def test_malicious_card_id_is_rejected_before_path_or_backend_use(
    tmp_path: Path, operation: str
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)

    with pytest.raises(ApprovalError, match="card ID|canonical"):
        if operation == "approve":
            approve_card(
                tmp_path,
                card_id="../../approval_" + "a" * 24,
                expected_card_sha256="b" * 64,
                reviewer_id="project_owner",
                backend=backend,
                verifier=verifier,
                now=REVIEWED_AT,
            )
        else:
            resume_push(
                tmp_path,
                card_id="../approval_" + "a" * 24,
                backend=backend,
                verifier=verifier,
            )

    assert calls == []


def test_concurrent_head_change_after_clean_check_stops_before_signoffs(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.head_after_clean = "9" * 40

    with pytest.raises(ApprovalError, match="HEAD|signoff"):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    assert backend.commits == [SOURCE_OID]
    assert backend.signoff_commit_calls == 0
    assert backend.push_attempts == []


def test_resume_rejects_git_customization_without_mutating_recovery(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.fail_push = True
    with pytest.raises(ApprovalError, match="push"):
        approve(tmp_path, card, backend, verifier)
    attempts = tuple(backend.push_attempts)
    backend.fail_push = False
    backend.customization_error = ApprovalError("active Git customization")
    calls.clear()

    with pytest.raises(ApprovalError, match="customization"):
        resume_push(
            tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
        )

    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    assert tuple(backend.push_attempts) == attempts
    assert "verify.accepted" not in calls


def test_approve_customization_recheck_invalidates_trusted_card(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.customization_error = ApprovalError("active Git customization")
    calls.clear()

    with pytest.raises(ApprovalError, match="customization"):
        approve(tmp_path, card, backend, verifier)

    assert read_state(tmp_path, card.card_id) == "invalidated"
    assert_no_git_or_signoff_side_effects(tmp_path, backend, calls)


def test_partial_signoff_set_is_reused_during_source_only_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    real_write = transaction_module._write_signoffs
    injected = False

    def partial_write(
        root: Path,
        value: object,
        *,
        reviewed_at: str,
        event_id: str,
    ) -> tuple[str, ...]:
        nonlocal injected
        if not injected:
            injected = True
            first_profile_only = replace(
                value, profiles=(getattr(value, "profiles")[0],)
            )
            real_write(
                root,
                first_profile_only,
                reviewed_at=reviewed_at,
                event_id=event_id,
            )
            raise ApprovalError("injected partial signoff set failure")
        return real_write(
            root, value, reviewed_at=reviewed_at, event_id=event_id
        )

    monkeypatch.setattr(transaction_module, "_write_signoffs", partial_write)
    with pytest.raises(ApprovalError, match="partial signoff"):
        approve(tmp_path, card, backend, verifier)

    paths = signoff_paths(tmp_path, card)
    assert paths[0].is_file()
    assert not paths[1].exists()
    first_bytes = paths[0].read_bytes()
    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    assert backend.commits == [SOURCE_OID]

    resumed = resume_push(
        tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
    )

    assert resumed.state is TransactionState.PUSHED
    assert paths[0].read_bytes() == first_bytes
    assert paths[1].is_file()
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1


def test_clean_failure_resumes_from_source_without_repeating_source_commit(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    verifier.clean_error = ApprovalError("clean checkout verification failed")
    with pytest.raises(ApprovalError, match="clean checkout"):
        approve(tmp_path, card, backend, verifier)
    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"
    verifier.clean_error = None
    calls.clear()

    resumed = resume_push(
        tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
    )

    assert resumed.state is TransactionState.PUSHED
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1
    assert "git.commit_source" not in calls


def test_interrupted_temp_signoff_write_leaves_no_partial_final_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    real_write_all = transaction_module._write_all
    injected = False

    def interrupted_write(descriptor: int, payload: bytes) -> None:
        nonlocal injected
        if not injected:
            injected = True
            transaction_module.os.write(descriptor, payload[:17])
            raise ApprovalError("injected interrupted signoff write")
        real_write_all(descriptor, payload)

    monkeypatch.setattr(transaction_module, "_write_all", interrupted_write)
    with pytest.raises(ApprovalError, match="interrupted signoff"):
        approve(tmp_path, card, backend, verifier)

    paths = signoff_paths(tmp_path, card)
    assert all(not path.exists() for path in paths)
    assert not tuple((tmp_path / "harness/signoffs").glob(".*.tmp"))
    assert read_state(tmp_path, card.card_id) == "local_committed_push_failed"

    resumed = resume_push(
        tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
    )

    assert resumed.state is TransactionState.PUSHED
    assert all(path.is_file() for path in paths)
    assert backend.commits == [SOURCE_OID, SIGNOFF_OID]


def test_empty_manifest_push_recovery_reports_no_source_commit(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    backend.manifest = ()
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    backend.fail_push = True
    with pytest.raises(ApprovalError, match="push"):
        approve(tmp_path, card, backend, verifier)
    backend.fail_push = False

    resumed = resume_push(
        tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
    )

    assert resumed.state is TransactionState.PUSHED
    assert resumed.source_commit_oid is None
    assert backend.commits == [SIGNOFF_OID]
    assert backend.signoff_commit_calls == 1


class LocalTransportBackend:
    """Use the real Git backend while mapping transport to a local bare remote."""

    def __init__(self, fixture: ApprovalGitFixture) -> None:
        self.root = fixture.work
        self._fixture = fixture
        self._backend = GitBackend(fixture.work)

    def __getattr__(self, name: str) -> object:
        return getattr(self._backend, name)

    def fetch_remote_snapshot(
        self,
        *,
        remote_name: str,
        expected_url: str,
        ref: str,
    ) -> RemoteSnapshot:
        snapshot = git_backend_module.fetch_remote_snapshot(
            self.root,
            remote_name=remote_name,
            expected_url=str(self._fixture.remote),
            ref=ref,
        )
        return replace(
            snapshot,
            fetch_url=expected_url,
            push_url=expected_url,
        )

    def push_exact(
        self, final_commit_oid: str, expected: RemoteSnapshot
    ) -> str:
        local_expected = replace(
            expected,
            fetch_url=str(self._fixture.remote),
            push_url=str(self._fixture.remote),
        )
        return git_backend_module.push_exact(
            self.root, final_commit_oid, local_expected
        )


def test_real_second_cycle_supersedes_dialog_history_after_evaluation_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = init_repo_with_bare_remote(tmp_path)
    install_sanitized_git_environment(monkeypatch, fixture.environment)
    write_minimal_contract(fixture.work)
    calls: list[str] = []
    verifier = SignoffValidatingVerifier(calls, production=True)
    backend = LocalTransportBackend(fixture)

    first = prepared_card(
        prepare_review(
            fixture.work,
            backend=backend,
            verifier=verifier,
            now=PREPARED_AT,
            nonce=b"0" * 16,
        )
    )
    first_result = approve(
        fixture.work,
        first,
        backend,
        verifier,
        now=REVIEWED_AT,
        event_id_factory=lambda: "approval_event_" + "1" * 24,
    )
    assert first_result.state is TransactionState.PUSHED

    verifier.snapshot = replace(
        verifier.snapshot,
        evaluation_id="evaluation_" + "e" * 24,
        evidence_digest="f" * 64,
    )
    second = prepared_card(
        prepare_review(
            fixture.work,
            backend=backend,
            verifier=verifier,
            now=PREPARED_AT + timedelta(minutes=20),
            nonce=b"1" * 16,
        )
    )
    first_profiles = profile_map(first)
    second_profiles = profile_map(second)
    for profile_id in ("governance", "current_phase"):
        assert second_profiles[profile_id].supersedes == (
            first_profiles[profile_id].signoff_filename
        )

    second_result = approve(
        fixture.work,
        second,
        backend,
        verifier,
        now=REVIEWED_AT + timedelta(minutes=20),
        event_id_factory=lambda: "approval_event_" + "2" * 24,
    )

    assert second_result.state is TransactionState.PUSHED
    for profile_id in ("governance", "current_phase"):
        validation = validate_signoff_directory(
            fixture.work / "harness/signoffs",
            SignoffContext(
                contract_id=CONTRACT_ID,
                contract_version="1.0.0",
                contract_digest=verifier.snapshot.contract_digest,
                profile_id=profile_id,
                evaluation_id=verifier.snapshot.evaluation_id,
                evidence_digest=verifier.snapshot.evidence_digest,
                required_roles=("governance_owner",),
                repository_root=str(fixture.work),
            ),
        )
        assert validation.valid_roles == ("governance_owner",)
        assert validation.invalid_signoffs == ()
        assert first_profiles[profile_id].signoff_filename in {
            issue.path for issue in validation.stale_signoffs
        }


def prepare_real_staged_signoff_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    ApprovalGitFixture,
    LocalTransportBackend,
    FakeVerifier,
    object,
    str,
    tuple[str, ...],
]:
    fixture = init_repo_with_bare_remote(tmp_path)
    install_sanitized_git_environment(monkeypatch, fixture.environment)
    write_minimal_contract(fixture.work)
    (fixture.work / "README.md").write_text(
        "reviewed source change\n", encoding="utf-8"
    )
    calls: list[str] = []
    verifier = FakeVerifier(calls)
    backend = LocalTransportBackend(fixture)
    card = prepared_card(
        prepare_review(
            fixture.work,
            backend=backend,
            verifier=verifier,
            now=PREPARED_AT,
            nonce=NONCE,
        )
    )
    real_commit_object = git_backend_module._commit_object
    injected = True

    def fail_signoff_commit_object(
        root: Path,
        *,
        tree_oid: str,
        parent_oid: str,
        subject: str,
        card_id: str,
    ) -> str:
        nonlocal injected
        if subject == "governance: approve acceptance profiles" and injected:
            injected = False
            raise ApprovalError("injected failure after signoff staging")
        return real_commit_object(
            root,
            tree_oid=tree_oid,
            parent_oid=parent_oid,
            subject=subject,
            card_id=card_id,
        )

    monkeypatch.setattr(
        git_backend_module, "_commit_object", fail_signoff_commit_object
    )
    with pytest.raises(ApprovalError, match="after signoff staging"):
        approve_card(
            fixture.work,
            card_id=getattr(card, "card_id"),
            expected_card_sha256=getattr(card, "card_sha256"),
            reviewer_id="project_owner",
            backend=backend,
            verifier=verifier,
            now=REVIEWED_AT,
            event_id_factory=lambda: EVENT_ID,
        )

    source_oid = git_stdout(
        fixture.work, fixture.environment, "rev-parse", "HEAD"
    )
    expected_paths = tuple(
        sorted(
            f"harness/signoffs/{profile.signoff_filename}"
            for profile in getattr(card, "profiles")
        )
    )
    journal = json.loads(
        journal_path(fixture.work, getattr(card, "card_id")).read_text(
            encoding="utf-8"
        )
    )
    assert journal["state"] == "local_committed_push_failed"
    assert journal["source_commit_oid"] == source_oid
    assert journal["final_commit_oid"] is None
    assert nul_paths(
        fixture.work,
        fixture.environment,
        "diff",
        "--cached",
        "--name-only",
        "-z",
    ) == expected_paths
    return fixture, backend, verifier, card, source_oid, expected_paths


def test_source_only_resume_reuses_exact_real_staged_signoffs_and_pushes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture, backend, verifier, card, source_oid, expected_paths = (
        prepare_real_staged_signoff_failure(tmp_path, monkeypatch)
    )
    verifier.prepare_roots.clear()
    before_bytes = tuple((fixture.work / path).read_bytes() for path in expected_paths)

    resumed = resume_push(
        fixture.work,
        card_id=getattr(card, "card_id"),
        backend=backend,
        verifier=verifier,
    )

    assert resumed.state is TransactionState.PUSHED
    assert resumed.source_commit_oid == source_oid
    assert resumed.final_commit_oid is not None
    assert git_stdout(
        fixture.remote, fixture.environment, "rev-parse", "refs/heads/main"
    ) == resumed.final_commit_oid
    assert nul_paths(
        fixture.work,
        fixture.environment,
        "diff",
        "--cached",
        "--name-only",
        "-z",
    ) == ()
    assert tuple((fixture.work / path).read_bytes() for path in expected_paths) == (
        before_bytes
    )
    assert git_stdout(
        fixture.work,
        fixture.environment,
        "rev-list",
        "--count",
        f"{getattr(card, 'head_oid')}..HEAD",
    ) == "2"


@pytest.mark.parametrize("staged_drift", ["extra", "different"])
def test_source_only_resume_rejects_any_nonexact_real_staged_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    staged_drift: str,
) -> None:
    fixture, backend, verifier, card, source_oid, expected_paths = (
        prepare_real_staged_signoff_failure(tmp_path, monkeypatch)
    )
    verifier.prepare_roots.clear()
    if staged_drift == "extra":
        extra = fixture.work / "extra-staged.txt"
        extra.write_text("not reviewed\n", encoding="utf-8")
        run_git(
            fixture.work,
            "add",
            "--",
            extra.name,
            environment=fixture.environment,
        )
    else:
        changed = fixture.work / expected_paths[0]
        changed.write_text('{"different":true}\n', encoding="utf-8")
        run_git(
            fixture.work,
            "add",
            "--",
            expected_paths[0],
            environment=fixture.environment,
        )

    with pytest.raises(ApprovalError, match="exact|recoverable signoff index"):
        resume_push(
            fixture.work,
            card_id=getattr(card, "card_id"),
            backend=backend,
            verifier=verifier,
        )

    assert read_state(fixture.work, getattr(card, "card_id")) == (
        "local_committed_push_failed"
    )
    assert git_stdout(
        fixture.work, fixture.environment, "rev-parse", "HEAD"
    ) == source_oid
    assert git_stdout(
        fixture.remote, fixture.environment, "rev-parse", "refs/heads/main"
    ) == getattr(card, "remote_oid")
    assert verifier.prepare_roots == []


def test_source_only_resume_runs_both_verifiers_in_clean_source_checkout(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    backend = FakeBackend(tmp_path, calls)
    verifier = FakeVerifier(calls)
    card = prepared_card(prepare(tmp_path, backend, verifier))
    verifier.clean_error = ApprovalError("injected clean checkout failure")
    with pytest.raises(ApprovalError, match="clean checkout"):
        approve(tmp_path, card, backend, verifier)
    verifier.clean_error = None
    verifier.prepare_roots.clear()
    verifier.clean_roots.clear()

    resumed = resume_push(
        tmp_path, card_id=card.card_id, backend=backend, verifier=verifier
    )

    assert resumed.state is TransactionState.PUSHED
    assert verifier.prepare_roots == verifier.clean_roots
    assert verifier.prepare_roots == [tmp_path / ".fake-clean-checkout"]
