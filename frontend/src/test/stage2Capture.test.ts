import { expect, it } from 'vitest';
import { completionData, type Draft } from '@/lib/study';
const d={id:'key',materia_id:'m',assunto_id:'a',atividade:'TEORIA',data:'2026-09-21T12:00:00Z',total:'10',acertos:'8',proximo:'',acao_id:null,retomar:''} as Draft;
it('old saved drafts produce unknown measures, not difficulty 3 or total session duration',()=>{
 expect(completionData(d,3600).bloco).toEqual({total_questoes:10,total_acertos:8,dificuldade:null,tempo_total_segundos:null});
});
it('keeps an explicitly selected 3 and 10 minutes separate from 60 session minutes',()=>{
 const p=completionData({...d,dificuldade:'3',tempoQuestoes:'10'},3600);
 expect(p.segundos).toBe(3600);expect(p.bloco?.tempo_total_segundos).toBe(600);expect(p.bloco?.dificuldade).toBe(3);
});
it('does not create a question block without questions',()=>{
 expect(completionData({...d,total:''},3600).bloco).toBeNull();
});
