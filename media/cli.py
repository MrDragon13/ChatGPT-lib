from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from media.commands.schema import load_command
from media.domain.commands import AddWorkCommand, AssessCandidateRequest, MediaEntryContextRequest, RecommendContextRequest, RecordMediaEntryCommand, RefreshMetadataCommand, RefreshWorkMetadataCommand, TasteContextRequest
from media.domain.errors import (
    AmbiguousIdentityError,
    CommandValidationError,
    MetadataRefreshPreflightError,
    NotFoundError,
    PathPolicyError,
    ProviderUnavailableError,
    TransactionValidationError,
    UnknownTargetError,
)
from media.providers.tmdb import TMDBProvider
from media.repository.yaml_repo import YamlRepository
from media.service.assessment import build_candidate_assessment_context
from media.service.media_entry_context import build_media_entry_context
from media.service.query import search_works, show_work
from media.service.recommend import build_recommend_context
from media.service.taste_context import build_taste_context
from media.service.transaction import execute_command, preview_command
from media.service.web_export import write_web_manifest
from media.tools.doctor import doctor
from media.tools.rebuild import check_generated, rebuild_generated


def _emit(value: Any, output_format: str = "human") -> None:
    if output_format == "json":
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return
    if isinstance(value, str): print(value)
    else: print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def _operation_result(result: Any) -> dict[str, Any]:
    value={"status":result.status,"operation_id":result.operation_id,"operation":result.operation,"changed_entities":list(result.changed_entities),"changed_files":list(result.changed_files)}
    if result.details: value["details"]=dict(result.details)
    return value


def _doctor_result(report: Any) -> dict[str, Any]:
    return {"status":"ok" if report.ok else "failed","checks":[asdict(check) for check in report.checks]}


def _parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(prog="media",description="Personal media library tooling"); sub=parser.add_subparsers(dest="command",required=True)
    entry_context=sub.add_parser("media-entry-context"); entry_context.add_argument("--request",required=True); entry_context.add_argument("--format",choices=("human","json"),default="human")
    search=sub.add_parser("search"); search.add_argument("query"); search.add_argument("--limit",type=int,default=20); search.add_argument("--format",choices=("human","json"),default="human")
    show=sub.add_parser("show"); show.add_argument("work_ref"); show.add_argument("--format",choices=("human","json"),default="human")
    recommend=sub.add_parser("recommend-context"); recommend.add_argument("--request",required=True); recommend.add_argument("--format",choices=("human","json"),default="human")
    taste=sub.add_parser("taste-context"); taste.add_argument("--request",required=True); taste.add_argument("--format",choices=("human","json"),default="human")
    assess=sub.add_parser("assess-candidate"); assess.add_argument("--request",required=True); assess.add_argument("--format",choices=("human","json"),default="human")
    apply=sub.add_parser("apply-command"); apply.add_argument("request"); apply.add_argument("--dry-run",action="store_true"); apply.add_argument("--format",choices=("human","json"),default="human")
    doctor_cmd=sub.add_parser("doctor"); doctor_cmd.add_argument("--format",choices=("human","json"),default="human")
    rebuild=sub.add_parser("rebuild"); rebuild.add_argument("--check",action="store_true")
    web_export=sub.add_parser("web-export"); web_export.add_argument("--output",required=True); web_export.add_argument("--format",choices=("human","json"),default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    args=_parser().parse_args(argv); repo_root=Path.cwd(); media_root=repo_root/"media"; output_format=getattr(args,"format","human")
    try:
        if args.command=="media-entry-context":
            request=load_command(Path(args.request))
            if not isinstance(request,MediaEntryContextRequest): raise CommandValidationError("media-entry-context request must use operation=media_entry_context")
            _emit(build_media_entry_context(media_root,request),output_format); return 0
        if args.command=="search": _emit(search_works(media_root,args.query,limit=args.limit),output_format); return 0
        if args.command=="show": _emit(show_work(media_root,args.work_ref),output_format); return 0
        if args.command=="recommend-context":
            request=load_command(Path(args.request))
            if not isinstance(request,RecommendContextRequest): raise CommandValidationError("recommend-context request must use operation=recommend_context")
            _emit(build_recommend_context(media_root,request),output_format); return 0
        if args.command=="taste-context":
            request=load_command(Path(args.request))
            if not isinstance(request,TasteContextRequest): raise CommandValidationError("taste-context request must use operation=taste_context")
            _emit(build_taste_context(media_root,request),output_format); return 0
        if args.command=="assess-candidate":
            request=load_command(Path(args.request))
            if not isinstance(request,AssessCandidateRequest): raise CommandValidationError("assess-candidate request must use operation=assess_candidate")
            _emit(build_candidate_assessment_context(media_root,request),output_format); return 0
        if args.command=="apply-command":
            command=load_command(Path(args.request))
            if isinstance(command,(MediaEntryContextRequest,RecommendContextRequest,TasteContextRequest,AssessCandidateRequest)): raise CommandValidationError(f"{command.__class__.__name__} is read-only and cannot be applied")
            provider=None
            needs_provider=isinstance(command,(AddWorkCommand,RefreshMetadataCommand,RefreshWorkMetadataCommand)) or (isinstance(command,RecordMediaEntryCommand) and command.create_if_missing)
            if needs_provider:
                token=os.environ.get("TMDB_READ_TOKEN")
                if token: provider=TMDBProvider(token)
            result=preview_command(repo_root,command,provider=provider) if args.dry_run else execute_command(repo_root,command,provider=provider); _emit(_operation_result(result),output_format); return 0
        if args.command=="doctor":
            report=doctor(repo_root); _emit(_doctor_result(report),output_format); return 0 if report.ok else 3
        if args.command=="rebuild":
            if args.check:
                stale=check_generated(media_root)
                if stale: _emit({"status":"stale","files":stale},"json"); return 3
                _emit({"status":"ok","files":[]},"json"); return 0
            paths=rebuild_generated(media_root); _emit({"status":"rebuilt","files":[str(path.relative_to(repo_root)) for path in paths]},"json"); return 0
        if args.command=="web-export":
            output=write_web_manifest(media_root,Path(args.output)); manifest=json.loads(output.read_text(encoding="utf-8")); _emit({"status":"ok","output":str(output),"works":len(manifest["works"]),"bytes":output.stat().st_size},output_format); return 0
    except MetadataRefreshPreflightError as exc:
        _emit({"status":"needs_input","reason":"metadata_refresh_preflight","blockers":[dict(item) for item in exc.blockers]},output_format); return 2
    except AmbiguousIdentityError as exc:
        _emit({"status":"needs_input","reason":"ambiguous_identity","candidates":[asdict(candidate) if hasattr(candidate,"__dataclass_fields__") else str(candidate) for candidate in exc.candidates]},output_format); return 2
    except (CommandValidationError,NotFoundError,UnknownTargetError) as exc:
        _emit({"status":"error","reason":exc.__class__.__name__,"message":str(exc)},output_format); return 2
    except ProviderUnavailableError as exc:
        _emit({"status":"error","reason":"provider_unavailable","message":str(exc)},output_format); return 4
    except (TransactionValidationError,PathPolicyError) as exc:
        _emit({"status":"error","reason":exc.__class__.__name__,"message":str(exc)},output_format); return 3
    return 3


if __name__=="__main__": raise SystemExit(main())
