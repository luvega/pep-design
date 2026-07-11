from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from harness.approval.git_backend import (
    GitExecutionError,
    redact_git_error,
)
from harness.approval.journal import TransactionState, load_journal
from harness.approval.models import ApprovalError
from harness.approval.service import (
    VerificationExecutionError,
    approve_dialog_card,
    prepare_dialog_review,
    resume_dialog_push,
)

from .evaluator import exit_code_for
from .report import evaluate_project, evaluation_dict, render_outputs


PROFILE_IDS = ("governance", "current_phase", "release_checkpoint", "full_project")
APPROVAL_PROFILES = ("governance", "current_phase")
_CARD_ID_RE = re.compile(r"approval_[0-9a-f]{24}")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")


class _ExactApprovalProfiles(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Sequence[str],
        option_string: str | None = None,
    ) -> None:
        if tuple(values) != APPROVAL_PROFILES:
            parser.error(
                "--profiles must be exactly: governance current_phase"
            )
        setattr(namespace, self.dest, tuple(values))


def _canonical_card_id(value: str) -> str:
    if _CARD_ID_RE.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("card ID must use approval_<24 lowercase hex>")
    return value


def _canonical_digest(value: str) -> str:
    if _DIGEST_RE.fullmatch(value) is None:
        raise argparse.ArgumentTypeError(
            "expected card SHA-256 must be 64 lowercase hex characters"
        )
    return value


def _add_hidden_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=None, help=argparse.SUPPRESS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate the Pep Design project acceptance contract."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "render"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--profile", choices=PROFILE_IDS, required=True)
        _add_hidden_root(subparser)

    prepare = subparsers.add_parser("prepare-review")
    prepare.add_argument(
        "--profiles",
        nargs=2,
        required=True,
        action=_ExactApprovalProfiles,
    )
    prepare.add_argument("--push-target", choices=("origin/main",), required=True)
    _add_hidden_root(prepare)

    approve = subparsers.add_parser("approve-card")
    approve.add_argument("--card-id", type=_canonical_card_id, required=True)
    approve.add_argument(
        "--expected-card-sha256",
        type=_canonical_digest,
        required=True,
    )
    approve.add_argument(
        "--reviewer-id",
        choices=("project_owner",),
        required=True,
    )
    _add_hidden_root(approve)

    resume = subparsers.add_parser("resume-push")
    resume.add_argument("--card-id", type=_canonical_card_id, required=True)
    _add_hidden_root(resume)
    return parser


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _run_dialog_command(args: argparse.Namespace, root: Path) -> int:
    if args.command == "prepare-review":
        prepared = prepare_dialog_review(root)
        print(prepared.markdown)
        return 0
    if args.command == "approve-card":
        outcome = approve_dialog_card(
            root,
            card_id=args.card_id,
            expected_card_sha256=args.expected_card_sha256,
            reviewer_id=args.reviewer_id,
        )
    else:
        outcome = resume_dialog_push(root, card_id=args.card_id)
    _print_json(asdict(outcome))
    return 0


def _run_evaluation_command(args: argparse.Namespace, root: Path) -> int:
    result = evaluate_project(
        root,
        args.profile,
        require_fresh_generated=args.command == "check",
    )
    if args.command == "render":
        render_outputs(root, result)
    _print_json(evaluation_dict(result))
    return exit_code_for(result.profile)


def _durable_dialog_state(
    args: argparse.Namespace, root: Path
) -> TransactionState | None:
    if args.command not in {"approve-card", "resume-push"}:
        return None
    try:
        canonical = root.resolve(strict=True)
        journal = load_journal(
            canonical
            / "ops/acceptance/dialog_transactions"
            / f"{args.card_id}.json"
        )
    except (OSError, ApprovalError):
        return None
    if journal.card_id != args.card_id:
        return None
    return journal.state


def _recovery_action(args: argparse.Namespace, root: Path) -> str:
    state = _durable_dialog_state(args, root)
    if state in {
        TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
        TransactionState.VERIFIED,
    }:
        return f"重新运行 resume-push --card-id {args.card_id}。"
    return "重新运行 prepare-review 生成新的审批卡。"


def _operational_code(exc: BaseException) -> str:
    if isinstance(exc, VerificationExecutionError):
        return f"verification_{exc.code}"
    if isinstance(exc, GitExecutionError):
        return "git_operation_failed"
    if isinstance(exc, subprocess.SubprocessError):
        return "subprocess_operation_failed"
    if isinstance(exc, OSError):
        return "os_operation_failed"
    return "internal_operation_failed"


def _dialog_error(
    args: argparse.Namespace,
    root: Path,
    *,
    status: str,
    reason_code: str,
    message: str,
) -> None:
    _print_json(
        {
            "command": args.command,
            "status": status,
            "reason_code": reason_code,
            "message": message,
            "recovery_action": _recovery_action(args, root),
        }
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root or Path(__file__).resolve().parents[2]
    if args.command in {"prepare-review", "approve-card", "resume-push"}:
        try:
            return _run_dialog_command(args, root)
        except (
            GitExecutionError,
            VerificationExecutionError,
            subprocess.SubprocessError,
            OSError,
        ) as exc:
            code = _operational_code(exc)
            _dialog_error(
                args,
                root,
                status="error",
                reason_code=code,
                message=code,
            )
            return 2
        except ApprovalError as exc:
            durable = _durable_dialog_state(args, root) in {
                TransactionState.LOCAL_COMMITTED_PUSH_FAILED,
                TransactionState.VERIFIED,
            }
            _dialog_error(
                args,
                root,
                status="error" if durable else "rejected",
                reason_code=(
                    "durable_transaction_requires_resume"
                    if durable
                    else "approval_rejected"
                ),
                message=(
                    "durable_transaction_requires_resume"
                    if durable
                    else redact_git_error(str(exc))
                ),
            )
            return 2 if durable else 1
        except Exception:
            _dialog_error(
                args,
                root,
                status="error",
                reason_code="internal_operation_failed",
                message="internal_operation_failed",
            )
            return 2
    try:
        return _run_evaluation_command(args, root)
    except Exception:
        _print_json(
            {
                "profile_id": args.profile,
                "harness_status": "error",
                "project_status": "not_accepted",
                "reason_codes": ["harness_evaluation_error"],
                "message": "harness_evaluation_error",
            }
        )
        return 2
