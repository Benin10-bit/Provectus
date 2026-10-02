/** Sparse travelling waves. Geometry and arrival times are computed at emission, not per frame. */
export const HEX_RADIUS = 100;
const SPEED = .55;
const PULSE = 320;
const STEP_X = 34;
const STEP_Y = 39.26;
const POOL_SIZE = 49;
const SELECTOR = '[data-hex-surface], .tac-card, .kpi-card, .form-step, .essay-card, .goal-reading, .subject-group, .report-section, .report-metric, .schedule-day, .review-card, .topic-card, .focus-workspace, .active-study, .nav-entry, .rounded-lg.border, .rounded-xl.border, [role="dialog"], [role="menu"], [role="tab"], button, a';
export type HexWave = { x: number; y: number; time: number };
const smooth = (x: number) => x * x * (3 - 2 * x);
function envelope(phase: number) {
  if (phase <= 0 || phase >= 1) return 0;
  return phase < .38 ? smooth(phase / .38) : smooth((1 - phase) / .62);
}
function falloff(distance: number) {
  const value = smooth(Math.max(0, 1 - distance / HEX_RADIUS));
  return value * value;
}
export function hexWaveStrength(distance: number, age: number) {
  return distance < 0 || distance >= HEX_RADIUS ? 0 : envelope((age - distance / SPEED) / PULSE) * falloff(distance);
}
type Pulse = { start: number; strength: number };
type Cell = { node: HTMLElement; face: HTMLElement; shadow: HTMLElement; key: string; pulses: Pulse[]; painted: number; hold: number; active: boolean };
type Geometry = { left: number; top: number; scaleX: number; scaleY: number; borderX: number; borderY: number; width: number; height: number };
type Surface = { host: HTMLElement; layer: HTMLElement; scene: HTMLElement; light: HTMLElement; cells: Cell[]; mapped: Map<string, Cell>; active: Set<Cell>; last: HexWave | null; glow: number; geometry: Geometry | null; pressed: boolean };

function measure(host: HTMLElement): Geometry {
  const rect = host.getBoundingClientRect();
  return { left: rect.left, top: rect.top, scaleX: rect.width / (host.offsetWidth || rect.width), scaleY: rect.height / (host.offsetHeight || rect.height), borderX: host.clientLeft, borderY: host.clientTop, width: rect.width, height: rect.height };
}
function createSurface(host: HTMLElement, geometry: Geometry): Surface {
  const positioned = getComputedStyle(host).position === 'static';
  const layer = document.createElement('provectus-hex-layer'); layer.className = 'hex-ripple-clip'; layer.setAttribute('aria-hidden', 'true');
  const scene = document.createElement('span'); scene.className = 'hex-ripple-scene';
  const light = document.createElement('span'); light.className = 'hex-ripple-light'; layer.append(scene, light);
  const cells: Cell[] = [];
  for (let i = 0; i < POOL_SIZE; i++) {
    const node = document.createElement('span'); node.className = 'hex-ripple-cell';
    const face = document.createElement('span'); face.className = 'hex-ripple-face';
    const shadow = document.createElement('span'); shadow.className = 'hex-ripple-shadow';
    node.append(shadow, face); scene.append(node);
    cells.push({ node, face, shadow, key: '', pulses: [], painted: 0, hold: 0, active: false });
  }
  if (positioned) host.classList.add('hex-ripple-positioned');
  host.classList.add('hex-ripple-host'); host.append(layer);
  return { host, layer, scene, light, cells, mapped: new Map(), active: new Set(), last: null, glow: 0, geometry, pressed: false };
}
function dispose(s: Surface) { s.layer.remove(); s.host.classList.remove('hex-ripple-host', 'hex-ripple-positioned'); }
function emit(s: Surface, x: number, y: number, now: number) {
  s.last = { x, y, time: now };
  s.active.forEach(cell => { cell.hold = 0; });
  // Only the spatial neighbourhood is considered. Distances/delays are cached in pulses.
  for (let col = Math.floor((x - HEX_RADIUS) / STEP_X); col <= Math.ceil((x + HEX_RADIUS) / STEP_X); col++) {
    const cx = col * STEP_X, offset = ((col % 2 + 2) % 2) * STEP_Y / 2;
    for (let row = Math.floor((y - HEX_RADIUS - offset) / STEP_Y); row <= Math.ceil((y + HEX_RADIUS - offset) / STEP_Y); row++) {
      const cy = row * STEP_Y + offset;
      const squared = (cx - x) ** 2 + (cy - y) ** 2;
      if (squared >= HEX_RADIUS ** 2 || cx < -20 || cy < -18) continue;
      const distance = Math.sqrt(squared), strength = falloff(distance);
      if (strength < .008) continue;
      const key = `${col}:${row}`;
      let cell = s.mapped.get(key);
      if (!cell) {
        cell = s.cells.find(candidate => !candidate.active);
        if (!cell) continue; // live plates are never teleported or abruptly recycled
        s.mapped.delete(cell.key); cell.key = key; s.mapped.set(key, cell);
        cell.node.style.left = `${cx - 20}px`; cell.node.style.top = `${cy - 17.32}px`;
      }
      if (!cell.active) { cell.active = true; s.active.add(cell); }
      cell.hold = strength * .35;
      cell.pulses.push({ start: now + distance / SPEED, strength });
      if (cell.pulses.length > 5) cell.pulses.shift();
    }
  }
  // Stable perspective avoids invalidating the entire 3D scene on every pointer frame.
  s.light.style.transform = `translate3d(${x - 125}px, ${y - 125}px, 0)`;
}
function paint(cell: Cell, strength: number) {
  // Quantization avoids redundant style writes while preserving subpixel movement.
  const value = Math.round(strength * 250) / 250;
  if (value === cell.painted) return;
  if (cell.painted === 0 && value !== 0) cell.face.style.willChange = 'transform, opacity';
  cell.painted = value;
  cell.face.style.opacity = `${Math.abs(value) * .38}`;
  cell.shadow.style.opacity = `${Math.abs(value) * .22}`;
  cell.face.style.transform = `translate3d(0, ${-value * 1.2}px, ${value * 6}px) rotateX(${value * 4}deg) rotateY(${-value * 3}deg) scale(${1 + value * .018})`;
  if (value === 0) cell.face.style.willChange = '';
}
export function installHexRipple(doc: Document = document) {
  const media = window.matchMedia('(any-hover: hover) and (any-pointer: fine)');
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let enabled = media.matches && !motion.matches;
  let frame = 0, dirty = false;
  let previousTime = 0;
  let pressedTarget: HTMLElement | null = null;
  let pointer: { target: HTMLElement; x: number; y: number } | null = null;
  const surfaces: Surface[] = [];
  const queue = () => { if (!frame) frame = requestAnimationFrame(tick); };
  const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(entries => {
    for (const entry of entries) { const s = surfaces.find(item => item.host === entry.target); if (s) s.geometry = null; }
    if (pointer) { dirty = true; queue(); }
  }) : null;
  function remove(s: Surface) { observer?.unobserve(s.host); dispose(s); surfaces.splice(surfaces.indexOf(s), 1); }
  function tick(now: number) {
    frame = 0;
    const dt = previousTime ? Math.min(40, now - previousTime) : 16;
    previousTime = now;
    const follow = 1 - Math.exp(-dt / 48);
    if (pointer && !pointer.target.isConnected) leave();
    if (dirty && pointer) {
      dirty = false;
      let s = surfaces.find(item => item.host === pointer!.target);
      const geometry = s?.geometry || measure(pointer.target);
      if (geometry.width < 60 || geometry.height < 32) leave();
      else {
        if (!s) {
          if (surfaces.length === 3) remove(surfaces.find(item => item.active.size === 0) || surfaces[0]);
          s = createSurface(pointer.target, geometry); surfaces.push(s); observer?.observe(s.host);
        }
        s.geometry = geometry;
        s.pressed = pressedTarget === s.host;
        const x = (pointer.x - geometry.left) / geometry.scaleX - geometry.borderX;
        const y = (pointer.y - geometry.top) / geometry.scaleY - geometry.borderY;
        const moved = !s.last || (x - s.last.x) ** 2 + (y - s.last.y) ** 2 >= 64;
        if (moved && (!s.last || now - s.last.time >= 110)) emit(s, x, y, now);
        else if (moved) dirty = true;
      }
    }
    let running = dirty;
    for (const s of surfaces) {
      if (!s.active.size) continue; // dormant surfaces do no geometry, pulse or style work
      if (!s.host.isConnected) { remove(s); continue; }
      let peak = 0;
      let settling = false;
      for (const cell of s.active) {
        let target = 0;
        for (let i = cell.pulses.length - 1; i >= 0; i--) {
          const pulse = cell.pulses[i], age = now - pulse.start;
          if (age >= PULSE) { cell.pulses.splice(i, 1); continue; }
          if (age > 0) target = Math.max(target, envelope(age / PULSE) * pulse.strength);
        }
        target = s.pressed ? -cell.hold * 1.4 : Math.max(target, cell.hold);
        const next = Math.abs(target - cell.painted) < .009 ? target : cell.painted + (target - cell.painted) * follow;
        paint(cell, next); peak = Math.max(peak, Math.abs(next));
        if (cell.pulses.length || Math.abs(target - cell.painted) >= .004) settling = true;
        if (!cell.pulses.length && cell.hold === 0 && cell.painted === 0) { cell.active = false; s.active.delete(cell); }
      }
      const glow = Math.round(peak * 50) / 50;
      if (glow !== s.glow) { s.light.style.opacity = `${glow * .2}`; s.glow = glow; }
      if (settling) running = true;
    }
    if (running) queue(); else previousTime = 0;
  }
  const move = (event: PointerEvent) => {
    if (!enabled || event.pointerType === 'touch' || doc.hidden) return;
    let target = event.target instanceof Element ? event.target.closest<HTMLElement>(SELECTOR) : null;
    if (target?.matches('button, a, [role="tab"]')) target = target.parentElement?.closest<HTMLElement>(SELECTOR) || target;
    if (!target || target.matches(':disabled') || target.closest('[data-hex-disabled]')) { leave(); return; }
    if (pointer?.target !== target) {
      surfaces.forEach(s => { if (s.host !== target) { s.active.forEach(cell => { cell.hold = 0; }); s.pressed = false; } });
      pressedTarget = null;
      const s = surfaces.find(item => item.host === target); if (s) { s.geometry = null; s.last = null; }
    }
    pointer = { target, x: event.clientX, y: event.clientY }; dirty = true; queue();
  };
  function leave() {
    pointer = null; dirty = false; pressedTarget = null;
    surfaces.forEach(s => { s.pressed = false; s.active.forEach(cell => { cell.hold = 0; }); });
    if (surfaces.some(s => s.active.size)) queue();
  }
  const down = (event: PointerEvent) => {
    if (event.button !== 0 || !enabled || event.pointerType === 'touch') return;
    move(event); pressedTarget = pointer?.target ?? null;
    surfaces.forEach(s => { s.pressed = s.host === pressedTarget; });
    if (pointer) queue();
  };
  const up = () => {
    pressedTarget = null; surfaces.forEach(s => { s.pressed = false; });
    if (surfaces.some(s => s.active.size)) queue();
  };
  const invalidate = () => { surfaces.forEach(s => { s.geometry = null; }); if (pointer) { dirty = true; queue(); } };
  const scroll = () => { leave(); invalidate(); };
  const clear = () => { leave(); cancelAnimationFrame(frame); frame = 0; [...surfaces].forEach(remove); };
  const visibility = () => { if (doc.hidden) clear(); };
  const policy = () => { enabled = media.matches && !motion.matches; if (!enabled) clear(); };
  doc.addEventListener('pointerdown', down, true);
  doc.addEventListener('pointerup', up, true);
  doc.addEventListener('pointercancel', leave, true);
  doc.addEventListener('pointermove', move, { passive: true }); doc.addEventListener('pointerleave', leave);
  doc.addEventListener('scroll', scroll, true); doc.addEventListener('toggle', invalidate, true);
  doc.addEventListener('transitionend', invalidate, true); doc.addEventListener('animationend', invalidate, true);
  doc.addEventListener('visibilitychange', visibility);
  window.addEventListener('resize', invalidate); window.addEventListener('blur', leave);
  media.addEventListener('change', policy); motion.addEventListener('change', policy);
  return () => {
    clear(); observer?.disconnect();
    doc.removeEventListener('pointerdown', down, true);
    doc.removeEventListener('pointerup', up, true);
    doc.removeEventListener('pointercancel', leave, true);
    doc.removeEventListener('pointermove', move); doc.removeEventListener('pointerleave', leave);
    doc.removeEventListener('scroll', scroll, true); doc.removeEventListener('toggle', invalidate, true);
    doc.removeEventListener('transitionend', invalidate, true); doc.removeEventListener('animationend', invalidate, true);
    doc.removeEventListener('visibilitychange', visibility);
    window.removeEventListener('resize', invalidate); window.removeEventListener('blur', leave);
    media.removeEventListener('change', policy); motion.removeEventListener('change', policy);
  };
}
