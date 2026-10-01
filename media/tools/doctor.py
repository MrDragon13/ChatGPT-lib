from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .build_db import build_database
from .rebuild import check_generated
from .validate import validate_repository


@dataclass(frozen=True)
class DoctorCheck:
    code: str
    ok: bool
    message: str


@dataclass(frozen=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]
    @property
    def ok(self)->bool: return all(check.ok for check in self.checks)


def doctor(repo_root:Path)->DoctorReport:
    repo_root=Path(repo_root); media_root=repo_root/'media'; checks=[]; issues=validate_repository(repo_root); checks.append(DoctorCheck('canonical_validation',not issues,'canonical data valid' if not issues else f'{len(issues)} validation issue(s)')); stale=check_generated(media_root); checks.append(DoctorCheck('generated_current',not stale,'generated artifacts current' if not stale else f"stale: {', '.join(stale)}"))
    try:
        with tempfile.TemporaryDirectory(prefix='media-doctor-') as tmpdir: build_database(media_root,Path(tmpdir)/'database.sqlite')
        checks.append(DoctorCheck('sqlite_rebuildable',True,'SQLite rebuild succeeded'))
    except Exception as exc: checks.append(DoctorCheck('sqlite_rebuildable',False,f'SQLite rebuild failed: {exc}'))
    tracked=False
    if (repo_root/'.git').exists():
        result=subprocess.run(['git','-C',str(repo_root),'ls-files','--error-unmatch','media/generated/database.sqlite'],capture_output=True,text=True,check=False); tracked=result.returncode==0
    checks.append(DoctorCheck('runtime_database_untracked',not tracked,'database.sqlite is not tracked' if not tracked else 'media/generated/database.sqlite is tracked')); return DoctorReport(tuple(checks))
