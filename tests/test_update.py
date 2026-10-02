"""Safety tests for update orchestration. Docker is simulated, never a real database."""
import hashlib,importlib.util,json,sys
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('maintenance',Path(__file__).parents[1]/'scripts/maintenance.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def digest(value):return hashlib.sha256(value.encode()).hexdigest()

@pytest.fixture
def setup(tmp_path,monkeypatch):
    source=tmp_path/'release';target=tmp_path/'installation';source.mkdir();target.mkdir()
    for r,txt in [('api/app/models.py','OLD'),('docker-compose.yml','local-compose'),('.env','LOCAL_TEST_CONFIG')]:
        p=target/r;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(txt)
    p=source/'api/app/models.py';p.parent.mkdir(parents=True);p.write_text('NEW')
    (source/'UPDATE_MANIFEST.json').write_text(json.dumps({'files':{'api/app/models.py':{'old':digest('OLD'),'new':digest('NEW')}},'removed':{}}))
    monkeypatch.setattr(m,'SOURCE',source)
    info={'Id':'database-id','State':{'Running':True,'Health':{'Status':'healthy'}},'Mounts':[{'Destination':'/var/lib/postgresql/data','Type':'volume','Name':'provectus_pgdata'}],
        'Config':{'Labels':{'com.docker.compose.project':'original-project','com.docker.compose.service':'db','com.docker.compose.project.working_dir':str(target),'com.docker.compose.project.config_files':str(target/'docker-compose.yml')}}}
    config={'name':'original-project','services':{'db':{'volumes':[{'type':'volume','source':'pgdata','target':'/var/lib/postgresql/data'}]},'api':{},'frontend':{}},'volumes':{'pgdata':{'name':'pgdata'}}}
    monkeypatch.setattr(m,'inspect_container',lambda name:info)
    calls=[]
    def fake(args,**kwargs):
        calls.append([str(a) for a in args])
        if '--format' in args and 'config' in args:return json.dumps(config)
        if '--help' in args:return '--wait'
        if 'ps' in args:return 'database-id'
        if args[:2]==['docker','exec']:
            if 'pg_dump' in ' '.join(args):kwargs['stdout'].write(b'VALID-TEST-DUMP'*100);return ''
            if 'psql' in ' '.join(args):return '\n'.join(t+'|3' for t in m.TABLES)
            if 'pg_restore' in args:return 'VALID LIST'
        return ''
    monkeypatch.setattr(m,'run',fake)
    return source,target,info,calls,fake

def test_backup_before_copy_and_preserve_identity(setup):
    source,target,info,calls,fake=setup
    m.update(target)
    assert (target/'api/app/models.py').read_text()=='NEW'
    assert (target/'.env').read_text()=='LOCAL_TEST_CONFIG'
    assert (target/'docker-compose.yml').read_text()=='local-compose'
    override=json.loads((target/'compose.provectus-volume.json').read_text())
    assert override['volumes']['pgdata']['name']=='provectus_pgdata'
    assert json.loads((target/'.provectus-install.json').read_text())['project']=='original-project'
    dump=next(i for i,a in enumerate(calls) if 'pg_dump' in ' '.join(a))
    migrate=next(i for i,a in enumerate(calls) if 'app.migrate' in a)
    build=next(i for i,a in enumerate(calls) if 'build' in a)
    assert dump<build<migrate
    assert not any('down' in a or 'prune' in a for a in calls)
    assert not any('up' in a and a[-1]=='db' for a in calls)
    assert list((target.parent/'provectus-backups').glob('*/arquivos.tar.gz'))

def test_failed_dump_stops_before_changes(setup,monkeypatch):
    source,target,info,calls,fake=setup
    def fail(args,**kw):
        if 'pg_dump' in ' '.join(args):raise m.UpdateError('simulated backup failure')
        return fake(args,**kw)
    monkeypatch.setattr(m,'run',fail)
    with pytest.raises(m.UpdateError):m.update(target)
    assert (target/'api/app/models.py').read_text()=='OLD'
    assert not any('app.migrate' in a or 'build' in a for a in calls)
    assert any('start' in a for a in calls)

def test_failed_dump_validation_stops_before_changes(setup,monkeypatch):
    source,target,info,calls,fake=setup
    def fail(args,**kw):
        if 'pg_restore' in args:raise m.UpdateError('invalid archive')
        return fake(args,**kw)
    monkeypatch.setattr(m,'run',fail)
    with pytest.raises(m.UpdateError):m.update(target)
    assert (target/'api/app/models.py').read_text()=='OLD'
    assert not any('app.migrate' in a for a in calls)

def test_failed_migration_does_not_start_new_services(setup,monkeypatch):
    source,target,info,calls,fake=setup
    def fail(args,**kw):
        if 'app.migrate' in args:raise m.UpdateError('migration failed')
        return fake(args,**kw)
    monkeypatch.setattr(m,'run',fail)
    with pytest.raises(m.UpdateError):m.update(target)
    assert not any('up' in a and '--help' not in a for a in calls)
    assert list((target.parent/'provectus-backups').glob('*/banco.dump'))

def test_local_code_conflict_is_not_overwritten(setup):
    source,target,info,calls,fake=setup
    (target/'api/app/models.py').write_text('MY LOCAL CHANGES')
    with pytest.raises(m.UpdateError,match='alterações locais'):m.update(target)
    assert not calls
    assert (target/'api/app/models.py').read_text()=='MY LOCAL CHANGES'

def test_outside_symlink_is_rejected(setup,tmp_path):
    source,target,info,calls,fake=setup
    outside=tmp_path/'important';outside.write_text('PRIVATE')
    p=target/'api/app/models.py';p.unlink();p.symlink_to(outside)
    with pytest.raises(m.UpdateError):m.update(target)
    assert outside.read_text()=='PRIVATE'
    assert not calls

def test_mismatched_project_stops(setup):
    source,target,info,calls,fake=setup
    (target/'.provectus-install.json').write_text(json.dumps({'project':'other','config_files':[str(target/'docker-compose.yml')]}))
    with pytest.raises(m.UpdateError,match='outro projeto'):m.update(target)
    assert (target/'api/app/models.py').read_text()=='OLD'

def test_start_refuses_different_database_project(setup):
    source,target,info,calls,fake=setup
    (target/'.provectus-install.json').write_text(json.dumps({'project':'other','config_files':[str(target/'docker-compose.yml')]}))
    with pytest.raises(m.UpdateError,match='outro projeto'):m.start(target)
    assert not any('start' in a or ('up' in a and '--help' not in a) for a in calls)
