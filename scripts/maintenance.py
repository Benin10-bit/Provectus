#!/usr/bin/env python3
"""Provectus update: stdlib only, same Compose project, same DB container and volume."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime

SOURCE = Path(__file__).resolve().parents[1]
PROTECTED = {'.env','docker-compose.yml','docker-compose.yaml','compose.yml','compose.yaml',
    'docker-compose.override.yml','docker-compose.override.yaml','compose.override.yml','compose.override.yaml',
    'compose.provectus-volume.json','.provectus-install.json'}
TABLES = ['tb_materia','tb_assunto','tb_sessao_estudo','tb_bloco_questoes','tb_simulado_semanal','tb_redacoes','tb_erro_questao']

class UpdateError(RuntimeError): pass

def run(args, cwd=None, capture=False, stdin=None, stdout=None):
    kwargs=dict(cwd=cwd,check=True,stdin=stdin,stdout=subprocess.PIPE if capture else stdout)
    # Never print rendered Compose configuration or container environment (may hold secrets).
    try:
        result=subprocess.run([str(a) for a in args],**kwargs)
        return result.stdout.decode() if capture else ''
    except (subprocess.CalledProcessError,OSError) as e:
        raise UpdateError(f'Etapa falhou: {args[0]} {args[1] if len(args)>1 else ""}. Execução interrompida.') from e

def inspect_container(name):
    p=subprocess.run(['docker','inspect',name],capture_output=True,text=True)
    if p.returncode:return None
    return json.loads(p.stdout)[0]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def safe_path(root,rel):
    p=root/rel
    if Path(rel).is_absolute() or '..' in Path(rel).parts or not p.resolve().is_relative_to(root.resolve()):
        raise UpdateError('Caminho de atualização inválido ou link para fora do projeto: '+rel)
    if p.is_symlink():raise UpdateError('Arquivo gerenciado é um link simbólico: '+rel)
    return p

def discover_target(argument):
    if argument:return Path(argument).expanduser().resolve()
    info=inspect_container('postgres_db')
    work=(info or {}).get('Config',{}).get('Labels',{}).get('com.docker.compose.project.working_dir')
    if work and Path(work).is_dir():return Path(work).resolve()
    known=Path.home()/'EsPCEx'/'provectus'
    if known.is_dir():return known.resolve()
    raise UpdateError('Pasta atual não localizada. Execute: bash atualizar.sh /caminho/da/sua/pasta/provectus')

def compose_config(target,info=None):
    statefile=target/'.provectus-install.json'
    if statefile.exists():
        state=json.loads(statefile.read_text());project=state['project'];files=[Path(p) for p in state['config_files']]
    else:
        labels=(info or {}).get('Config',{}).get('Labels',{})
        project=labels.get('com.docker.compose.project')
        raw=labels.get('com.docker.compose.project.config_files')
        if raw:files=[Path(f) for f in raw.split(',')]
        else:
            files=[target/'docker-compose.yml']
            if (target/'docker-compose.override.yml').exists():files.append(target/'docker-compose.override.yml')
    if not files or any(not p.is_file() for p in files):raise UpdateError('Arquivo Compose da instalação não localizado; nenhuma substituição foi feita.')
    args=['docker','compose','--project-directory',str(target)]
    if project:args+=['-p',project]
    for f in files:args+=['-f',str(f)]
    config=json.loads(run(args+['config','--format','json'],cwd=target,capture=True))
    project=project or config['name']
    if not {'db','api','frontend'} <= set(config.get('services',{})):raise UpdateError('São necessários os serviços db, api e frontend.')
    return args,config,project,files

def db_counts(info):
    sql=' UNION ALL '.join(f"SELECT '{t}', count(*) FROM {t}" for t in TABLES)
    data=run(['docker','exec',info['Id'],'sh','-ec','psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "$1"','sh',sql],capture=True)
    return dict(line.split('|',1) for line in data.strip().splitlines())

def db_backup(info,folder):
    dump=folder/'banco.dump'
    with dump.open('wb') as f:
        run(['docker','exec',info['Id'],'sh','-ec','pg_dump --format=custom --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],stdout=f)
    if dump.stat().st_size<100:raise UpdateError('Backup do banco vazio/incompleto.')
    with dump.open('rb') as f:
        run(['docker','exec','-i',info['Id'],'pg_restore','--list'],stdin=f,capture=True)
    return dump

def check_services(args,target):
    run(args+['up','-d','--no-deps','--wait','--wait-timeout','180','api','frontend'],cwd=target)
    for service in ['api','frontend']:
        id=run(args+['ps','-q',service],cwd=target,capture=True).strip()
        if not id or inspect_container(id)['State'].get('Health',{}).get('Status')!='healthy':raise UpdateError('Serviço não saudável: '+service)
    # Exercise the public proxy paths, not only the static index page.
    run(args+['exec','-T','frontend','curl','-fsS','--max-time','20','http://localhost/api/api/v1/performance/dashboard?periodo=total'],cwd=target,capture=True)
    run(args+['exec','-T','frontend','curl','-fsS','--max-time','20','http://localhost/api/configuracoes/materias'],cwd=target,capture=True)
    run(args+['exec','-T','frontend','curl','-fsS','--max-time','20','http://localhost/api/api/v1/estudos/agora'],cwd=target,capture=True)
    run(args+['exec','-T','frontend','curl','-fsS','--max-time','20','http://localhost/api/api/v1/metas/semana'],cwd=target,capture=True)

def plan_update(target,manifest):
    changes=[];conflicts=[];preserved=[]
    for rel,item in manifest['files'].items():
        src=safe_path(SOURCE,rel);dst=safe_path(target,rel)
        if rel in PROTECTED or rel.startswith('.env') and not rel.endswith('.example'):
            preserved.append(rel);continue
        if not src.is_file() or sha(src)!=item['new']:raise UpdateError('Pacote incompleto ou alterado: '+rel)
        if dst.is_file():
            digest=sha(dst)
            if digest==item['new']:continue
            if digest not in [item.get('old'),*item.get('compatible_old',[])]:
                # Explicit local settings are retained, not silently overwritten.
                if rel in {'frontend/nginx.conf','frontend/vite.config.ts','frontend/src/lib/cronograma.ts','provectus-monitor.sh','provectus-health.sh','start-provectus.sh','provectus-shutdown.sh'}:
                    preserved.append(rel);continue
                conflicts.append(rel);continue
        changes.append(rel)
    if conflicts:raise UpdateError('Arquivos autorais com alterações locais foram preservados. Atualização parada antes de modificar arquivos: '+', '.join(conflicts))
    removed=[]
    for rel,oldhash in manifest.get('removed',{}).items():
        p=safe_path(target,rel)
        if p.exists() and sha(p)==oldhash:removed.append(rel)
    return changes,removed,preserved

def update(target):
    if target==SOURCE:raise UpdateError('Extraia o pacote em outra pasta; a atualização precisa preservar a instalação atual.')
    if not (target/'.env').is_file() or not (target/'api/app/models.py').is_file():raise UpdateError('A pasta não é a instalação existente do Provectus com .env.')
    manifest=json.loads((SOURCE/'UPDATE_MANIFEST.json').read_text())
    changes,removed,preserved=plan_update(target,manifest)
    info=inspect_container('postgres_db')
    if not info or not info['State']['Running']:raise UpdateError('O banco existente postgres_db precisa estar em execução. Não criaremos um banco vazio em seu lugar.')
    args,config,project,files=compose_config(target,info)
    labels=info.get('Config',{}).get('Labels',{})
    if labels.get('com.docker.compose.project')!=project or labels.get('com.docker.compose.service')!='db':raise UpdateError('O banco pertence a outro projeto Compose. Atualização parada.')
    dbid=run(args+['ps','-q','db'],cwd=target,capture=True).strip()
    if not dbid or inspect_container(dbid)['Id']!=info['Id']:raise UpdateError('Não foi possível confirmar o banco da instalação selecionada.')
    mounts=[m for m in info['Mounts'] if m['Destination']=='/var/lib/postgresql/data']
    if len(mounts)!=1:raise UpdateError('Persistência do PostgreSQL não reconhecida.')
    mount=mounts[0]
    # Validate the CLI before stopping services.
    if '--wait' not in run(args+['up','--help'],capture=True):raise UpdateError('Atualize o plugin Docker Compose para uma versão com up --wait.')
    before=db_counts(info)
    backup=target.parent/'provectus-backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True,mode=0o700)
    # Back up all overwritten files plus local configuration. Never package this archive in the release.
    saved=set(changes+removed+['.env','.provectus-install.json','compose.provectus-volume.json'])
    saved.update(str(f.relative_to(target)) for f in files if f.is_relative_to(target))
    existing=[]
    with tarfile.open(backup/'arquivos.tar.gz','w:gz') as tar:
        for rel in sorted(saved):
            p=safe_path(target,rel)
            if p.is_file():tar.add(p,arcname=rel,recursive=False);existing.append(rel)
    with tarfile.open(backup/'arquivos.tar.gz','r:gz') as tar:
        for item in tar:
            if item.isfile():
                stream=tar.extractfile(item)
                while stream.read(1024*1024):pass
    state=dict(project=project,config_files=[str(f) for f in files],target=str(target),db_container_id=info['Id'],mount=mount,
        changed=changes,removed=removed,previously_existing=existing,preserved=preserved,counts=before)
    (backup/'estado.json').write_text(json.dumps(state,indent=2))
    print('Backup de arquivos:',backup,flush=True)
    stopped=False;applied=False
    try:
        run(args+['stop','frontend','api'],cwd=target);stopped=True
        # With application writers stopped, pg_dump has a consistent recoverable snapshot.
        before=db_counts(info);state['counts']=before
        db_backup(info,backup)
        (backup/'estado.json').write_text(json.dumps(state,indent=2))
        print('Backup do banco validado. Aplicando arquivos.',flush=True)
        applied=True
        for rel in changes:
            src=safe_path(SOURCE,rel);dst=safe_path(target,rel);dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)
        for rel in removed:safe_path(target,rel).unlink()
        # Pin only the real existing volume if the old config points to a different name.
        if mount['Type']=='volume':
            declared=[v for v in config['services']['db'].get('volumes',[]) if v.get('target')=='/var/lib/postgresql/data']
            if len(declared)!=1 or declared[0]['type']!='volume':raise UpdateError('Tipo de persistência do Compose difere do contêiner existente.')
            key=declared[0]['source'];configured=config.get('volumes',{}).get(key,{}).get('name',key)
            if configured!=mount['Name']:
                override=target/'compose.provectus-volume.json'
                override.write_text(json.dumps({'volumes':{key:{'external':True,'name':mount['Name']}}},indent=2))
                if override not in files:files.append(override);args+=['-f',str(override)]
                print('Persistência fixada no mesmo volume já montado:',mount['Name'],flush=True)
        install=dict(project=project,config_files=[str(f) for f in files])
        (target/'.provectus-install.json').write_text(json.dumps(install,indent=2))
        run(args+['build','api','frontend'],cwd=target)
        run(args+['run','--rm','--no-deps','api','python','-m','app.migrate'],cwd=target)
        if db_counts(info)!=before:raise UpdateError('Contagens de dados mudaram durante a migração; aplicação mantida parada para conferência.')
        check_services(args,target)
        after=inspect_container('postgres_db')
        if not after or after['Id']!=info['Id'] or after['Mounts']!=info['Mounts']:raise UpdateError('Identidade/persistência do banco mudou inesperadamente.')
        print('Provectus atualizado e verificado. Abra http://localhost .')
        print('Backup:',backup)
        if preserved:print('Configurações locais preservadas:',', '.join(preserved))
    except Exception:
        if stopped and not applied:
            print('Nenhum arquivo de aplicação foi substituído; tentando retomar os contêineres anteriores.',file=sys.stderr)
            try:run(args+['start','api','frontend'],cwd=target)
            except UpdateError:print('Retomada automática falhou; os backups continuam disponíveis.',file=sys.stderr)
        else:
            print('Falha após aplicar arquivos. Não houve exclusão de volume nem restauração automática de dados. Backup: '+str(backup),file=sys.stderr)
            print('Após corrigir a causa, execute o atualizador novamente. Consulte COMO_ATUALIZAR.md para voltar aos arquivos anteriores.',file=sys.stderr)
        raise

def start(target):
    info=inspect_container('postgres_db');args,config,project,files=compose_config(target,info)
    # Start an existing database only; never select a fresh volume during an ordinary launch.
    if not info:raise UpdateError('Banco existente não encontrado. Use instalar.sh somente para instalação nova.')
    labels=info.get('Config',{}).get('Labels',{})
    if labels.get('com.docker.compose.project')!=project or labels.get('com.docker.compose.service')!='db':raise UpdateError('Banco pertence a outro projeto; inicialização cancelada.')
    if not info['State']['Running']:run(['docker','start',info['Id']])
    check_services(args,target)
    print('Provectus pronto em http://localhost')
    if shutil.which('xdg-open'):subprocess.Popen(['xdg-open','http://localhost'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def install():
    target=SOURCE
    marker=target/'.provectus-new-install.json'
    if not marker.exists():
        if inspect_container('postgres_db'):raise UpdateError('Já existe postgres_db. Use atualizar.sh para preservar essa instalação.')
        if (target/'.env').exists():raise UpdateError('Já existe .env. Instalação nova cancelada; use atualizar.sh para instalação existente.')
        probe=subprocess.run(['docker','volume','inspect','pgdata'],capture_output=True)
        if probe.returncode==0:raise UpdateError('O volume pgdata já existe. Não será tratado como vazio.')
        marker.write_text(json.dumps({'target':str(target)}))
        (target/'.env').write_text('DB_USER=provectususer\nDB_NAME=provectusdb\nDB_PASSWORD='+secrets.token_hex(24)+'\n')
    if json.loads(marker.read_text()).get('target')!=str(target) or not (target/'.env').is_file():
        raise UpdateError('Estado de instalação incompleto ou de outra pasta. Nenhum banco foi alterado.')
    args,config,project,files=compose_config(target)
    info=inspect_container('postgres_db')
    if info:
        labels=info.get('Config',{}).get('Labels',{})
        if labels.get('com.docker.compose.project')!=project or labels.get('com.docker.compose.project.working_dir')!=str(target):
            raise UpdateError('O banco existente pertence a outra instalação.')
    volume_probe=subprocess.run(['docker','volume','inspect','pgdata'],capture_output=True,text=True)
    if volume_probe.returncode==0:
        volume=json.loads(volume_probe.stdout)[0]
        if (volume.get('Labels') or {}).get('provectus.install-path')!=str(target):raise UpdateError('Volume pgdata não pertence a esta instalação nova; retomada cancelada.')
    run(['docker','volume','create','--label','provectus.install-path='+str(target),'pgdata'])
    run(args+['up','-d','--wait','--wait-timeout','120','db'],cwd=target)
    run(args+['build','api','frontend'],cwd=target)
    run(args+['run','--rm','--no-deps','api','python','-m','app.migrate'],cwd=target)
    (target/'.provectus-install.json').write_text(json.dumps(dict(project=project,config_files=[str(f) for f in files]),indent=2))
    check_services(args,target)
    marker.unlink()
    print('Instalação criada em http://localhost . Cadastre suas matérias em Conteúdos e as cotas em Estudar agora.')

def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['update','start','install']);parser.add_argument('target',nargs='?');args=parser.parse_args()
    if not shutil.which('docker'):raise UpdateError('Docker não encontrado. Instale/inicie o Docker antes de continuar.')
    run(['docker','info'],capture=True);run(['docker','compose','version'],capture=True)
    if args.mode=='install':install()
    elif args.mode=='start':start(Path(args.target).resolve() if args.target else SOURCE)
    else:update(discover_target(args.target))

if __name__=='__main__':
    try:main()
    except (UpdateError,OSError,ValueError) as e:
        print('ERRO: '+str(e),file=sys.stderr);sys.exit(1)
