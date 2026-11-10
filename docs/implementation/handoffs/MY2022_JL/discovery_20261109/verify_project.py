"""Required project checks with isolated databases and media; no development DB access."""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
os.environ['RIGARCHIVE_TEST_DB_PATH']=':memory:'
original=sqlite3.connect
def isolated(database,*args,**kwargs):
    name=str(database)
    temporary_file = not name.startswith('file:') and Path(name).is_absolute() and Path(name).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
    if name != ':memory:' and not (name.startswith('file:memorydb_') and 'mode=memory' in name) and not temporary_file:
        raise RuntimeError('Verification rejected non-isolated SQLite connection')
    return original(database,*args,**kwargs)
sqlite3.connect=isolated
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
with tempfile.TemporaryDirectory(prefix='rigarchive-my22-verification-') as tmp:
    settings.MEDIA_ROOT=Path(tmp)/'media'
    settings.DATABASES['default']['TEST']['NAME']=':memory:'
    action=sys.argv[1]
    if action=='check':call_command('check')
    elif action=='migrations':call_command('makemigrations',check=True,dry_run=True)
    elif action=='test':call_command('test',interactive=False,verbosity=1)
    else:raise ValueError(action)
