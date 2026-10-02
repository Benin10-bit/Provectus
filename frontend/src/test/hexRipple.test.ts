import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { HEX_RADIUS, hexWaveStrength, installHexRipple } from '@/components/experience/hexRipple';

let frames: Map<number, FrameRequestCallback>;
let stop: (() => void) | undefined;
let count = 0;
let time = 0;
function advance(ms = 16) {
  time += ms;
  const callbacks = [...frames.values()]; frames.clear();
  callbacks.forEach(callback => callback(time));
}
function card(left = 80, top = 120) {
  const node = document.createElement('div'); node.className = 'tac-card';
  const button = document.createElement('button'); button.textContent = 'Registrar'; node.append(button);
  node.getBoundingClientRect = () => ({ left, top, width: 360, height: 240, right: left + 360, bottom: top + 240, x: left, y: top, toJSON: () => ({}) });
  document.body.append(node); return node;
}
function move(node: Element, x: number, y: number) {
  node.dispatchEvent(new MouseEvent('pointermove', { bubbles: true, clientX: x, clientY: y }));
}
beforeEach(() => {
  frames = new Map(); time = 0; count = 0;
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => { frames.set(++count, callback); return count; });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => frames.delete(id));
  vi.stubGlobal('matchMedia', (query: string) => ({ matches: !query.includes('reduced-motion'), addEventListener: vi.fn(), removeEventListener: vi.fn() }));
});
afterEach(() => { stop?.(); stop = undefined; document.body.replaceChildren(); vi.unstubAllGlobals(); });

describe('Hex ripple behaviour', () => {
  it('propagates by distance, stays within its radius and returns to zero', () => {
    expect(hexWaveStrength(0, 100)).toBeGreaterThan(0);
    expect(hexWaveStrength(80, 100)).toBe(0);
    expect(hexWaveStrength(80, 300)).toBeGreaterThan(0);
    expect(hexWaveStrength(HEX_RADIUS + 1, 300)).toBe(0);
    expect(hexWaveStrength(0, 800)).toBe(0);
  });
  it('uses local pointer coordinates and reuses the same cells across child controls', () => {
    const host = card(); stop = installHexRipple();
    move(host, 104, 150); advance();
    const layer = host.querySelector('.hex-ripple-clip')!;
    const firstCell = layer.querySelector('.hex-ripple-cell');
    expect((layer.querySelector('.hex-ripple-light') as HTMLElement).style.transform).toBe('translate3d(-101px, -95px, 0)');
    advance(140);
    expect([...host.querySelectorAll<HTMLElement>('.hex-ripple-face')].some(face => Number(face.style.opacity) > .1)).toBe(true);
    const click = vi.fn(); host.querySelector('button')!.addEventListener('click', click);
    for (let i = 0; i < 100; i++) move(host.querySelector('button')!, 120 + i / 10, 170);
    expect(frames.size).toBe(1);
    advance(); host.querySelector('button')!.click();
    expect(click).toHaveBeenCalledOnce();
    expect(host.querySelector('.hex-ripple-cell')).toBe(firstCell);
    expect(host.querySelectorAll('.hex-ripple-cell')).toHaveLength(49);
    expect(document.body.querySelectorAll('.hex-ripple-clip')).toHaveLength(1);
    expect(layer.parentElement).toBe(host);
    expect(layer).toHaveAttribute('aria-hidden', 'true');
  });
  it('settles after leaving, stops scheduling frames and cleans up on unmount', () => {
    const host = card(); stop = installHexRipple(); move(host, 130, 160); advance(); advance(100);
    document.dispatchEvent(new Event('pointerleave'));
    expect(frames.size).toBe(1); // exit does not abruptly destroy the wave
    for (let i = 0; i < 120; i++) advance();
    expect(frames.size).toBe(0);
    expect([...host.querySelectorAll<HTMLElement>('.hex-ripple-face')].every(face => Number(face.style.opacity) === 0)).toBe(true);
    stop(); stop = undefined;
    expect(host.querySelector('.hex-ripple-clip')).toBeNull();
    expect(host.classList.contains('hex-ripple-host')).toBe(false);
  });
  it('bounds retained surfaces and preserves original children', () => {
    const hosts = Array.from({ length: 8 }, () => card()); stop = installHexRipple();
    hosts.forEach(host => { move(host, 140, 180); advance(100); });
    expect(document.querySelectorAll('.hex-ripple-clip')).toHaveLength(3);
    hosts.forEach(host => expect(host.querySelector('button')?.textContent).toBe('Registrar'));
  });
  it('caches bounds during movement and refreshes them after resize', () => {
    const host = card(); const measure = vi.spyOn(host, 'getBoundingClientRect');
    stop = installHexRipple();
    for (let i = 0; i < 90; i++) { move(host, 120 + i, 170); advance(); }
    expect(measure).toHaveBeenCalledTimes(1);
    window.dispatchEvent(new Event('resize')); advance();
    expect(measure).toHaveBeenCalledTimes(2);
  });
  it('does not write styles to a resting surface while another animates', () => {
    const resting = card(), active = card(); stop = installHexRipple();
    move(resting, 140, 180); advance(); document.dispatchEvent(new Event('pointerleave'));
    for (let i = 0; i < 60; i++) advance();
    const observer = new MutationObserver(() => {});
    observer.observe(resting, { subtree: true, attributes: true, attributeFilter: ['style'] });
    for (let i = 0; i < 60; i++) { move(active, 150 + i, 180); advance(); }
    expect(observer.takeRecords()).toHaveLength(0); observer.disconnect();
    expect([...resting.querySelectorAll<HTMLElement>('.hex-ripple-face')].every(face => !face.style.willChange)).toBe(true);
  });
  it('does not create decorative DOM when reduced motion is requested', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
    const host = card(); stop = installHexRipple(); move(host, 120, 160); advance();
    expect(document.querySelector('.hex-ripple-clip')).toBeNull();
    expect(frames.size).toBe(0);
  });
  it('holds the local effect under a stationary pointer without an idle frame loop', () => {
    const host = card(); stop = installHexRipple(); move(host, 140, 180); advance();
    for (let i = 0; i < 120; i++) advance();
    expect(frames.size).toBe(0);
    expect([...host.querySelectorAll<HTMLElement>('.hex-ripple-face')].some(face => Number(face.style.opacity) > .02)).toBe(true);
    document.dispatchEvent(new Event('pointerleave'));
    for (let i = 0; i < 120; i++) advance();
    expect(frames.size).toBe(0);
    expect([...host.querySelectorAll<HTMLElement>('.hex-ripple-face')].every(face => Number(face.style.opacity) === 0)).toBe(true);
  });
  it('sinks during primary press, restores hover on release and preserves clicks', () => {
    const host = card(); stop = installHexRipple(); move(host, 140, 180); advance();
    for (let i = 0; i < 100; i++) advance();
    const button = host.querySelector('button')!; const click = vi.fn(); button.addEventListener('click', click);
    const depth = () => Math.min(...[...host.querySelectorAll<HTMLElement>('.hex-ripple-face')].map(face => Number(face.style.transform.match(/translate3d\(0, [^,]+, ([^p]+)px\)/)?.[1] || 0)));
    button.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true, button: 0, clientX: 140, clientY: 180 }));
    for (let i = 0; i < 60; i++) advance();
    expect(depth()).toBeLessThan(0); expect(frames.size).toBe(0);
    button.dispatchEvent(new MouseEvent('pointerup', { bubbles: true, button: 0 })); button.click();
    for (let i = 0; i < 60; i++) advance();
    expect(depth()).toBeGreaterThanOrEqual(0); expect(click).toHaveBeenCalledOnce(); expect(frames.size).toBe(0);
  });

});
