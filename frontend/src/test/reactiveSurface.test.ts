import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { installReactiveSurfaces, membraneForce, springStep } from '@/components/experience/reactiveSurface';
let frames: Map<number, FrameRequestCallback>, id = 0, time = 0, stop: (() => void) | undefined;
let ctx: Record<string, any>;
const oldContext = HTMLCanvasElement.prototype.getContext;
function step(n = 1) { for (let i = 0; i < n; i++) { time += 16.67; const fs = [...frames.values()]; frames.clear(); fs.forEach(f => f(time)); } }
function surface(tag = 'div') { const el = document.createElement(tag); el.className = 'tac-card'; el.textContent = 'Conteúdo'; el.getBoundingClientRect = vi.fn(() => ({ x: 20, y: 40, left: 20, top: 40, right: 380, bottom: 240, width: 360, height: 200, toJSON() {} })); document.body.append(el); return el; }
function pointer(el: Element, type: string, x = 100, y = 120, pointerType = 'mouse') { const e = new MouseEvent(type, { bubbles: true, clientX: x, clientY: y, button: 0 }); Object.defineProperties(e, { pointerId: {value: 1}, pointerType: { value: pointerType } }); el.dispatchEvent(e); }
beforeEach(() => {
 frames = new Map(); id = time = 0;
 vi.stubGlobal('requestAnimationFrame', (f: FrameRequestCallback) => { frames.set(++id, f); return id; }); vi.stubGlobal('cancelAnimationFrame', (i: number) => frames.delete(i));
 vi.stubGlobal('matchMedia', (q: string) => ({matches: !q.includes('reduced-motion'), addEventListener: vi.fn(), removeEventListener: vi.fn()}));
 ctx = { setTransform: vi.fn(), clearRect: vi.fn(), fillRect: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn(), createRadialGradient: vi.fn(() => ({addColorStop: vi.fn()})) };
 HTMLCanvasElement.prototype.getContext = vi.fn(() => ctx) as any;
});
afterEach(() => { stop?.(); stop = undefined; document.body.replaceChildren(); HTMLCanvasElement.prototype.getContext = oldContext; vi.unstubAllGlobals(); });
it('has smooth local influence and a damped spring that settles', () => {
 expect(membraneForce(0,0,0,0)).toBe(1); expect(membraneForce(114,0,0,0)).toBe(0); expect(membraneForce(113,0,0,0)).toBeLessThan(.001);
 let z = 0, velocity = 0; for (let i = 0; i < 300; i++) ({ z, velocity } = springStep(z, velocity, -9, 1 / 120)); expect(z).toBeCloseTo(-9, 3); expect(Math.abs(velocity)).toBeLessThan(.001);
});
it('uses one bounded canvas, preserves content and rests while hovered', () => {
 const el = surface(); stop = installReactiveSurfaces(); for(let i=0;i<100;i++) pointer(el,'pointermove'); expect(frames.size).toBe(1); step(150);
 expect(el.textContent).toBe('Conteúdo'); expect(el.querySelectorAll('canvas')).toHaveLength(1); expect(el.querySelectorAll('.reactive-clip *')).toHaveLength(1); expect(frames.size).toBe(0);
 expect(ctx.createRadialGradient.mock.calls[0].slice(0,2)).toEqual([80,80]);
 const draws = ctx.stroke.mock.calls.length; step(30); expect(ctx.stroke).toHaveBeenCalledTimes(draws);
 document.dispatchEvent(new Event('pointerleave')); step(150); expect(frames.size).toBe(0);
});
it('presses the actual button at the local contact point and preserves click', () => {
 const panel = surface(), button = surface('button'); panel.append(button); const click = vi.fn(); button.onclick = click;
 stop = installReactiveSurfaces(); pointer(button, 'pointerdown', 60, 100); step(120);
 expect(button.querySelector('.reactive-clip')).not.toBeNull(); expect(ctx.createRadialGradient.mock.calls[0].slice(0,2)).toEqual([40,60]); expect(frames.size).toBe(0);
 pointer(document.body,'pointerup', 700,700); button.click(); step(150); expect(click).toHaveBeenCalledOnce(); expect(frames.size).toBe(0);
});
it('supports central keyboard press and reduced-motion feedback', () => {
 vi.stubGlobal('matchMedia', (q:string) => ({ matches:q.includes('reduced-motion'), addEventListener:vi.fn(),removeEventListener:vi.fn()}));
 const button=surface('button'); stop=installReactiveSurfaces(); pointer(button,'pointermove'); step(); expect(button.querySelector('canvas')).toBeNull();
 button.dispatchEvent(new KeyboardEvent('keydown',{bubbles:true,key:' '})); step(100); expect(button.querySelector('canvas')).not.toBeNull(); expect(frames.size).toBe(0);
 button.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true,key:' '})); step(100); expect(frames.size).toBe(0);
});
it('handles touch cancel and quick transitions with bounded DOM and cleanup', () => {
 const els=Array.from({length:10},()=>surface('button')); stop=installReactiveSurfaces();
 els.forEach(el=>{pointer(el,'pointerdown',100,120,'touch');step();pointer(el,'pointercancel',100,120,'touch');step();});
 expect(document.querySelectorAll('canvas').length).toBeLessThanOrEqual(2); step(150); expect(frames.size).toBe(0);
 stop();stop=undefined;expect(document.querySelectorAll('.reactive-clip')).toHaveLength(0);expect(frames.size).toBe(0);
});
it('caches layout reads until invalidation', () => {
 const el=surface();stop=installReactiveSurfaces();for(let i=0;i<30;i++){pointer(el,'pointermove',100+i,120);step();}
 expect(el.getBoundingClientRect).toHaveBeenCalledTimes(1);window.dispatchEvent(new Event('resize'));step();expect(el.getBoundingClientRect).toHaveBeenCalledTimes(2);
});
it('uses the semantic color and updates a resting hovered surface after status changes', async () => {
 const el=surface(); el.style.setProperty('--surface-tone','6 48% 66%');
 stop=installReactiveSurfaces();pointer(el,'pointermove');step(150);
 expect(ctx.strokeStyle).toContain('6 48% 66%');expect(frames.size).toBe(0);
 el.style.setProperty('--surface-tone','112 38% 64%');el.dataset.tone='success';
 await Promise.resolve();step(2);
 expect(ctx.strokeStyle).toContain('112 38% 64%');expect(frames.size).toBe(0);
});
