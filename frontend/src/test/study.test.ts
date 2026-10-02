import { describe, it, expect, beforeEach } from 'vitest';
import { elapsedMs, loadDraft, DRAFT_KEY, type Draft } from '../lib/study';
const draft = {id:'test-session',elapsed:25000,runningSince:null} as Draft;
describe('retomada da sessão',()=>{
 beforeEach(()=>localStorage.clear());
 it('mantém o tempo pausado após recarregar',()=>{localStorage.setItem(DRAFT_KEY,JSON.stringify(draft));expect(elapsedMs(loadDraft()!,100000)).toBe(25000);});
 it('conta o intervalo em execução sem perder os segundos anteriores',()=>expect(elapsedMs({...draft,runningSince:100000},160000)).toBe(85000));
 it('não produz duração negativa se o relógio retroceder',()=>expect(elapsedMs({...draft,elapsed:0,runningSince:100000},90000)).toBe(0));
 it('tolera armazenamento corrompido',()=>{localStorage.setItem(DRAFT_KEY,'{');expect(loadDraft()).toBeNull();});
 it('ignora rascunho sem duração válida',()=>{localStorage.setItem(DRAFT_KEY,JSON.stringify({id:'x',elapsed:'erro'}));expect(loadDraft()).toBeNull();});
});
