from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from media.domain.changeset import MutationPlan, OperationResult
from media.domain.commands import AddWorkCommand, RecordViewingFeedbackCommand, SetInterestCommand
from media.domain.errors import CommandValidationError, TransactionValidationError
from media.repository.yaml_repo import YamlRepository
from media.service.mutate import plan_record_viewing_feedback, plan_set_interest
from media.service.enrich import plan_add_work
from media.service.path_policy import verify_changed_paths
from media.tools.build_index import write_index
from media.tools.build_profiles import write_profiles
from media.tools.common import dump_yaml
from media.tools.validate import validate_repository

MutableCommand = RecordViewingFeedbackCommand | SetInterestCommand | AddWorkCommand

def _receipt_path(repo_root:Path,operation_id:str)->Path: return repo_root/".media"/"operations"/f"{operation_id}.json"
def _load_receipt(path:Path)->OperationResult:
    data=json.loads(path.read_text(encoding="utf-8")); return OperationResult("already_applied",data["operation_id"],data["operation"],tuple(data.get("changed_entities") or ()),tuple(data.get("changed_files") or ()))
def _plan(repo:YamlRepository,command:MutableCommand,now:datetime|None,provider:Any=None)->MutationPlan:
    if isinstance(command,RecordViewingFeedbackCommand): return plan_record_viewing_feedback(repo,command,now=now)
    if isinstance(command,SetInterestCommand): return plan_set_interest(repo,command,now=now)
    if isinstance(command,AddWorkCommand): return plan_add_work(repo,command,provider,now=now)
    raise CommandValidationError("unsupported mutable command")
def preview_command(repo_root:Path,command:MutableCommand,*,now:datetime|None=None,provider:Any=None)->OperationResult:
    repo_root=Path(repo_root); receipt=_receipt_path(repo_root,command.operation_id)
    if receipt.exists(): return _load_receipt(receipt)
    plan=_plan(YamlRepository(repo_root/"media"),command,now,provider); return OperationResult("planned" if plan.changed_entities else "no_change",plan.operation_id,plan.operation,plan.changed_entities,tuple(sorted(plan.documents)))
def _file_map(root:Path)->dict[str,bytes]:
    media=root/"media"; result={}
    if not media.exists(): return result
    for path in sorted(media.rglob("*")):
        if path.is_file(): result[str(path.relative_to(root)).replace("\\","/")]=path.read_bytes()
    return result
def _changed_paths(original:Path,temporary:Path)->list[str]:
    before=_file_map(original); after=_file_map(temporary); return sorted(path for path in set(before)|set(after) if before.get(path)!=after.get(path))
def _sync_with_rollback(original:Path,temporary:Path,paths:list[str])->None:
    backups={}
    try:
        for rel in paths:
            dst=original/rel; src=temporary/rel; backups[rel]=dst.read_bytes() if dst.exists() else None
            if src.exists(): dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
            elif dst.exists(): dst.unlink()
    except Exception:
        for rel,content in backups.items():
            dst=original/rel
            if content is None:
                if dst.exists(): dst.unlink()
            else: dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(content)
        raise
def execute_command(repo_root:Path,command:MutableCommand,*,now:datetime|None=None,provider:Any=None)->OperationResult:
    repo_root=Path(repo_root); receipt=_receipt_path(repo_root,command.operation_id)
    if receipt.exists(): return _load_receipt(receipt)
    with tempfile.TemporaryDirectory(prefix="media-op-") as tmpdir:
        temp_root=Path(tmpdir)/"repo"; temp_root.mkdir(parents=True); shutil.copytree(repo_root/"media",temp_root/"media"); plan=_plan(YamlRepository(temp_root/"media"),command,now,provider)
        for rel,document in plan.documents.items(): dump_yaml(temp_root/rel,document)
        if plan.changed_entities:
            issues=validate_repository(temp_root)
            if issues: raise TransactionValidationError("; ".join(f"{issue.code}: {issue.message}" for issue in issues[:10]))
            write_index(temp_root/"media"); write_profiles(temp_root/"media")
        paths=_changed_paths(repo_root,temp_root) if plan.changed_entities else []; verify_changed_paths(plan.operation,paths); _sync_with_rollback(repo_root,temp_root,paths)
    status="applied" if plan.changed_entities else "no_change"; receipt_rel=str(receipt.relative_to(repo_root)).replace("\\","/"); changed_files=tuple(paths+[receipt_rel]); receipt.parent.mkdir(parents=True,exist_ok=True); applied_at=(now or datetime.now(timezone.utc)).isoformat(); receipt.write_text(json.dumps({"operation_id":plan.operation_id,"operation":plan.operation,"status":status,"changed_entities":list(plan.changed_entities),"changed_files":list(changed_files),"applied_at":applied_at},ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8"); return OperationResult(status,plan.operation_id,plan.operation,plan.changed_entities,changed_files)
