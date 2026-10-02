#!/usr/bin/env python3
"""Recuperação explícita: arquivos anteriores ou cópia do banco, sem apagar dados."""
import argparse,json,os,shutil,sys,tarfile
from datetime import datetime
from pathlib import Path
from maintenance import run,inspect_container,compose_config,safe_path,PROTECTED,UpdateError

def recover(mode,backup):
    state=json.loads((backup/'estado.json').read_text())
    target=Path(state['target']).resolve()
    info=inspect_container('postgres_db')
    if not info or info['Id']!=state['db_container_id'] or not info['State']['Running']:
        raise UpdateError('Banco original não localizado/em execução. Recuperação automática cancelada.')
    if mode=='banco-copia':
        dump=backup/'banco.dump'
        with dump.open('rb') as f:run(['docker','exec','-i',info['Id'],'pg_restore','--list'],stdin=f,capture=True)
        name='provectus_recuperado_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        run(['docker','exec',info['Id'],'sh','-ec','createdb -U "$POSTGRES_USER" "$1"','sh',name])
        with dump.open('rb') as f:
            run(['docker','exec','-i',info['Id'],'sh','-ec','pg_restore --exit-on-error --single-transaction --no-owner --no-acl -U "$POSTGRES_USER" -d "$1"','sh',name],stdin=f)
        print('Backup restaurado e validado na base separada: '+name)
        print('A base em uso e o .env permanecem intactos. Para recuperação definitiva, confirme os registros nessa cópia antes de mudar DB_NAME no .env e reconstruir a API.')
        return
    args,config,project,files=compose_config(target,info)
    if project!=state['project']:raise UpdateError('Projeto Compose difere do backup.')
    archive=backup/'arquivos.tar.gz'
    # Validate every member before stopping or writing. Never extract links or configuration.
    with tarfile.open(archive,'r:gz') as tar:
        members=[]
        for item in tar:
            safe_path(target,item.name)
            if not item.isfile():raise UpdateError('Backup contém item não regular.')
            if item.name in PROTECTED or item.name.startswith('.env'):continue
            members.append((item.name,tar.extractfile(item).read(),item.mode))
    current=backup/('antes-da-recuperacao-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.tar.gz')
    with tarfile.open(current,'w:gz') as tar:
        for name,data,mode in members:
            path=safe_path(target,name)
            if path.is_file():tar.add(path,arcname=name,recursive=False)
    run(args+['stop','frontend','api'],cwd=target)
    for name,data,mode in members:
        path=safe_path(target,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);path.chmod(mode&0o777)
    run(args+['build','api','frontend'],cwd=target)
    run(args+['up','-d','--no-deps','--wait','--wait-timeout','180','api','frontend'],cwd=target)
    print('Arquivos anteriores restaurados. Banco e configuração local preservados; migração aditiva não foi desfeita. Abra http://localhost e confira seus registros.')

if __name__=='__main__':
    os.umask(0o077)
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['arquivos','banco-copia']);parser.add_argument('backup');args=parser.parse_args()
    try:recover(args.mode,Path(args.backup).expanduser().resolve())
    except (UpdateError,OSError,ValueError,tarfile.TarError) as e:print('ERRO: '+str(e),file=sys.stderr);sys.exit(1)
