import subprocess
from media.tools.doctor import doctor
from media.tools.rebuild import rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo

def test_doctor_builds_sqlite_only_in_temp(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); assert not (root/'media/generated/database.sqlite').exists(); report=doctor(root); assert report.ok; assert not (root/'media/generated/database.sqlite').exists()
def test_doctor_reports_tracked_database_sqlite_when_git_available(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); db=root/'media/generated/database.sqlite'; db.write_bytes(b'not sqlite'); subprocess.run(['git','init'],cwd=root,check=True,capture_output=True); subprocess.run(['git','add','-f','media/generated/database.sqlite'],cwd=root,check=True,capture_output=True); report=doctor(root); check=next(item for item in report.checks if item.code=='runtime_database_untracked'); assert not check.ok
