import { expect, it, vi } from 'vitest';
import { installMovingIndicators } from '@/components/experience/movingIndicators';
it('moves the same marker when selection changes and cleans up', async () => {
 const root=document.createElement('div'); root.innerHTML='<div role="tablist"><button aria-selected="true">A</button><button aria-selected="false">B</button></div>';document.body.append(root);
 const list=root.firstElementChild as HTMLElement, buttons=list.querySelectorAll('button');
 const rect=(left:number,width:number)=>({left,top:0,width,height:40,right:left+width,bottom:40,x:left,y:0,toJSON(){}});
 list.getBoundingClientRect=()=>rect(20,200); buttons[0].getBoundingClientRect=()=>rect(20,80);buttons[1].getBoundingClientRect=()=>rect(100,120);
 let callback:FrameRequestCallback|null=null;
 vi.stubGlobal('requestAnimationFrame',(fn:FrameRequestCallback)=>{callback=fn;return 1;});vi.stubGlobal('cancelAnimationFrame',vi.fn());
 const cleanup=installMovingIndicators(root);
 callback?.(0);const marker=list.querySelector<HTMLElement>('.moving-tab-indicator')!;expect(marker.style.transform).toBe('translateX(0px) scaleX(80)');
 buttons[0].setAttribute('aria-selected','false');buttons[1].setAttribute('aria-selected','true');await Promise.resolve();callback?.(16);
 expect(list.querySelector('.moving-tab-indicator')).toBe(marker);expect(marker.style.transform).toBe('translateX(80px) scaleX(120)');
 cleanup();expect(list.querySelector('.moving-tab-indicator')).toBeNull();root.remove();vi.unstubAllGlobals();
});
