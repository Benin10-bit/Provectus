"""Recovery fail-stop tests with simulated Docker; no user database."""
import importlib.util,json,sys,tarfile,io
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import recuperar as r

def fixture(tmp_path,monkeypatch):
    target=tmp_path/'installation';target.mkdir();backup=tmp_path/'backup';backup.mkdir()
    (backup/'estado.json').write_text(json.dumps({'target':str(target),'project':'original','db_container_id':'id'}))
    info={'Id':'id','State':{'Running':True}}
    monkeypatch.setattr(r,'inspect_container',lambda name:info)
    monkeypatch.setattr(r,'compose_config',lambda *a:(['docker','compose'],{},'original',[]))
    calls=[]
    monkeypatch.setattr(r,'run',lambda args,**kw:calls.append(args))
    return target,backup,info,calls

def test_refuses_other_database(tmp_path,monkeypatch):
    target,backup,info,calls=fixture(tmp_path,monkeypatch);info['Id']='different'
    with pytest.raises(r.UpdateError):r.recover('banco-copia',backup)
    assert not calls

def test_archive_traversal_stops_before_services(tmp_path,monkeypatch):
    target,backup,info,calls=fixture(tmp_path,monkeypatch)
    with tarfile.open(backup/'arquivos.tar.gz','w:gz') as tar:
        item=tarfile.TarInfo('../private');item.size=3;tar.addfile(item,io.BytesIO(b'bad'))
    with pytest.raises(r.UpdateError):r.recover('arquivos',backup)
    assert not calls

def test_database_restore_uses_new_database_and_transaction(tmp_path,monkeypatch):
    target,backup,info,calls=fixture(tmp_path,monkeypatch);(backup/'banco.dump').write_bytes(b'test archive')
    r.recover('banco-copia',backup)
    commands=[' '.join(a) for a in calls]
    assert any('createdb' in a and 'provectus_recuperado_' in a for a in commands)
    assert any('--single-transaction' in a and '--exit-on-error' in a for a in commands)
    assert not any('dropdb' in a or '--clean' in a or 'down' in a for a in commands)
