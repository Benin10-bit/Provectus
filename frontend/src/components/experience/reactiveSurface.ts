/** Local canvas membranes: bounded pixel area, shared scheduler, no React pointer state. */
const SURFACES = '[data-reactive-surface], .tac-card, .kpi-card, .form-step, .essay-card, .goal-reading, .subject-group, .report-section, .report-metric, .schedule-day, .topic-card, .focus-workspace, .nav-entry, .rounded-lg.border, .rounded-xl.border';
const PRESSABLE = 'button, a[href], [role="button"], [role="tab"], summary';
const SIZE = 288, RADIUS = 114;
type Node = { x: number; y: number; z: number; velocity: number };
type Bounds = { left: number; top: number; width: number; height: number; sx: number; sy: number; bx: number; by: number };
type Surface = { host: HTMLElement; layer: HTMLElement; canvas: HTMLCanvasElement; ctx: CanvasRenderingContext2D; bounds: Bounds | null; nodes: Node[]; cols: number; rows: number; ox: number; oy: number; x: number; y: number; hover: boolean; press: boolean; amount: number; visible: boolean; tone: string; control: boolean; busy: boolean; step: number };
export function membraneForce(x: number, y: number, px: number, py: number, radius = RADIUS) {
  const d2 = ((x - px) ** 2 + (y - py) ** 2) / (radius * radius);
  if (d2 >= 1) return 0;
  const edge = 1 - d2;
  return edge * edge * edge; // zero value and slope at the influence boundary
}
export function springStep(z: number, velocity: number, target: number, dt: number) {
  const steps = Math.max(1, Math.ceil(dt / .01)), h = dt / steps;
  for (let i = 0; i < steps; i++) { velocity += ((target - z) * 250 - velocity * 27) * h; z += velocity * h; }
  return { z, velocity };
}
function measure(host: HTMLElement): Bounds {
  const r = host.getBoundingClientRect();
  const w = host.offsetWidth || r.width, h = host.offsetHeight || r.height;
  return { left: r.left, top: r.top, width: w, height: h, sx: r.width / w || 1, sy: r.height / h || 1, bx: host.clientLeft, by: host.clientTop };
}
export function installReactiveSurfaces(doc: Document = document) {
  const hoverMedia = matchMedia('(any-hover: hover) and (any-pointer: fine)');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const surfaces: Surface[] = [];
  let raf = 0, last = 0, stopped = false;
  let input: { host: HTMLElement; x: number; y: number; control: boolean; hover: boolean; press: boolean; id: number } | null = null;
  let dirty = false;
  let pointerId: number | null = null;
  const queue = () => { if (!raf && !stopped && !doc.hidden) raf = requestAnimationFrame(tick); };
  const resize = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => invalidate());
  const intersection = typeof IntersectionObserver === 'undefined' ? null : new IntersectionObserver(entries => {
    for (const e of entries) {
      const s = surfaces.find(item => item.host === e.target); if (!s) continue;
      s.visible = e.isIntersecting;
      if (!s.visible) { s.hover = s.press = s.busy = false; s.amount = 0; s.nodes.forEach(n => { n.z = n.velocity = 0; }); s.ctx.clearRect(0, 0, SIZE, SIZE); if (input?.host === s.host) input = null; }
    }
  });
  function readTone(host: HTMLElement) {
    const style = getComputedStyle(host);
    return style.getPropertyValue('--surface-tone').trim() || style.getPropertyValue('--olive-light').trim() || '85 57% 70%';
  }
  // Status updates recolor even a settled surface under a stationary pointer.
  const tones = new MutationObserver(() => {
    for (const s of surfaces) {
      const tone = readTone(s.host);
      if (tone !== s.tone) { s.tone = tone; s.busy = true; queue(); }
    }
  });
  tones.observe(doc.documentElement, { subtree: true, attributes: true, attributeFilter: ['data-tone'] });
  function remove(s: Surface) {
    resize?.unobserve(s.host); intersection?.unobserve(s.host); s.layer.remove();
    s.host.classList.remove('reactive-host', 'reactive-positioned'); surfaces.splice(surfaces.indexOf(s), 1);
  }
  function create(host: HTMLElement, bounds: Bounds, control: boolean): Surface | null {
    const canvas = document.createElement('canvas');
    let ctx: CanvasRenderingContext2D | null = null;
    try { ctx = canvas.getContext('2d', { alpha: true }); } catch { return null; }
    if (!ctx) return null;
    const style = getComputedStyle(host);
    const layer = document.createElement('provectus-surface'); layer.className = 'reactive-clip'; layer.setAttribute('aria-hidden', 'true');
    canvas.className = 'reactive-mesh'; layer.append(canvas);
    const ratio = Math.min(devicePixelRatio || 1, 1.25);
    canvas.width = canvas.height = Math.ceil(SIZE * ratio); ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    if (style.position === 'static') host.classList.add('reactive-positioned');
    host.classList.add('reactive-host'); host.append(layer);
    const variant = host.dataset.reactiveSurface;
    const s: Surface = { host, layer, canvas, ctx, bounds, nodes: [], cols: 0, rows: 0, ox: NaN, oy: NaN, x: 0, y: 0, hover: false, press: false, amount: 0, visible: true, tone: readTone(host), control, busy: true, step: control || variant === 'subtle' ? 30 : 24 };
    surfaces.push(s); resize?.observe(host); intersection?.observe(host); return s;
  }
  function grid(s: Surface) {
    const b = s.bounds!;
    const ox = Math.min(Math.max(0, Math.ceil((b.width - SIZE) / s.step) * s.step), Math.max(0, Math.floor((s.x - SIZE / 2) / s.step) * s.step));
    const oy = Math.min(Math.max(0, Math.ceil((b.height - SIZE) / s.step) * s.step), Math.max(0, Math.floor((s.y - SIZE / 2) / s.step) * s.step));
    if (s.ox === ox && s.oy === oy && s.nodes.length) return;
    const old = new Map(s.nodes.map(n => [`${n.x}:${n.y}`, n]));
    s.ox = ox; s.oy = oy; s.cols = s.rows = Math.ceil(SIZE / s.step) + 1; s.nodes = [];
    for (let row = 0; row < s.rows; row++) for (let col = 0; col < s.cols; col++) {
      const x = ox + col * s.step, y = oy + row * s.step;
      s.nodes.push(old.get(`${x}:${y}`) || { x, y, z: 0, velocity: 0 });
    }
    s.canvas.style.transform = `translate3d(${ox}px,${oy}px,0)`;
  }
  function draw(s: Surface, dt: number) {
    const b = s.bounds!, ctx = s.ctx;
    grid(s);
    const presence = s.hover || s.press ? 1 : 0;
    s.amount += (presence - s.amount) * (1 - Math.exp(-dt / .06));
    if (Math.abs(presence - s.amount) < .002) s.amount = presence;
    const depth = reduced.matches ? 0 : s.press ? -9 : s.hover ? (s.control ? 3 : 5) : 0;
    let moving = s.amount !== presence;
    const positions: { x: number; y: number; alpha: number }[] = [];
    for (const n of s.nodes) {
      const influence = membraneForce(n.x, n.y, s.x, s.y);
      const anchor = Math.max(0, Math.min(1, n.x / 20, n.y / 20, (b.width - n.x) / 20, (b.height - n.y) / 20));
      const target = depth * influence * anchor;
      if (reduced.matches) { n.z = n.velocity = 0; }
      else {
        const next = springStep(n.z, n.velocity, target, dt); n.z = next.z; n.velocity = next.velocity;
        if (Math.abs(n.z - target) < .015 && Math.abs(n.velocity) < .025) { n.z = target; n.velocity = 0; }
        else moving = true;
      }
      positions.push({ x: n.x - s.ox + (n.x - s.x) / RADIUS * n.z * 1.8, y: n.y - s.oy + (n.y - s.y) / RADIUS * n.z * 1.8 - n.z * .6, alpha: influence });
    }
    ctx.clearRect(0, 0, SIZE, SIZE);
    if (s.amount > 0 || moving) {
      // A bounded shared light, not one filter or shadow per vertex.
      const glow = ctx.createRadialGradient(s.x - s.ox, s.y - s.oy, 0, s.x - s.ox, s.y - s.oy, RADIUS);
      glow.addColorStop(0, s.press ? `rgba(0,0,0,${.28 * s.amount})` : `hsl(${s.tone} / ${.055 * s.amount})`);
      glow.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = glow; ctx.fillRect(0, 0, SIZE, SIZE);
      ctx.lineWidth = .65;
      for (let row = 0; row < s.rows; row++) for (let col = 0; col < s.cols; col++) {
        const i = row * s.cols + col, point = positions[i];
        for (const j of [col + 1 < s.cols ? i + 1 : -1, row + 1 < s.rows ? i + s.cols : -1]) {
          if (j < 0) continue;
          const other = positions[j], alpha = (point.alpha + other.alpha) * .5 * s.amount;
          if (alpha < .008) continue;
          ctx.strokeStyle = `hsl(${s.tone} / ${alpha * (s.control ? .28 : .34)})`;
          ctx.beginPath(); ctx.moveTo(point.x, point.y); ctx.lineTo(other.x, other.y); ctx.stroke();
        }
      }
    }
    s.busy = moving;
  }
  function tick(now: number) {
    raf = 0; const dt = last ? Math.min(.032, (now - last) / 1000) : 1 / 60; last = now;
    if (dirty && input) {
      dirty = false;
      if (!input.host.isConnected) leave();
      else {
        let s = surfaces.find(item => item.host === input!.host);
        const b = s?.bounds || measure(input.host);
        if (b.width > 0 && b.height > 0) {
          if (!s) { if (surfaces.length === 2) remove(surfaces.find(item => !item.busy) || surfaces[0]); s = create(input.host, b, input.control) || undefined; }
          if (s) { s.bounds = b; s.x = (input.x - b.left) / b.sx - b.bx; s.y = (input.y - b.top) / b.sy - b.by; s.hover = input.hover; s.press = input.press; s.busy = true; }
        }
      }
    }
    let running = false;
    for (const s of [...surfaces]) {
      if (!s.host.isConnected) { remove(s); continue; }
      if (!s.busy || !s.visible) continue;
      if (!s.bounds) s.bounds = measure(s.host);
      draw(s, dt); running ||= s.busy;
    }
    if (running || dirty) queue(); else last = 0;
  }
  function resolve(event: PointerEvent, pressing: boolean) {
    if (!(event.target instanceof Element)) return null;
    const control = event.target.closest<HTMLElement>(PRESSABLE);
    const host = control || event.target.closest<HTMLElement>(SURFACES);
    if (!host || host.matches(':disabled, [aria-disabled="true"]') || host.closest('[data-reactive-disabled]')) return null;
    if (!pressing && (!hoverMedia.matches || event.pointerType === 'touch' || reduced.matches)) return null;
    return { host, x: event.clientX, y: event.clientY, control: Boolean(control), hover: hoverMedia.matches && event.pointerType !== 'touch' && !reduced.matches, press: pressing, id: event.pointerId };
  }
  function setInput(next: typeof input) {
    for (const s of surfaces) if (s.host !== next?.host) { s.hover = s.press = false; s.busy = true; }
    if (next && next.host !== input?.host) { const s = surfaces.find(item => item.host === next.host); if (s) s.bounds = null; }
    input = next; dirty = Boolean(next); queue();
  }
  const move = (e: PointerEvent) => {
    if (pointerId !== null) return; // pressure stays at its physical contact point until release
    setInput(resolve(e, false));
  };
  const down = (e: PointerEvent) => { if (e.button !== 0) return; const next = resolve(e, true); if (!next) return; pointerId = e.pointerId; setInput(next); };
  const up = (e: PointerEvent) => { if (pointerId !== null && e.pointerId !== pointerId) return; pointerId = null; setInput(resolve(e, false)); };
  function leave() { pointerId = null; setInput(null); }
  const keyboard = (e: KeyboardEvent) => {
    if (e.type === 'keyup' && (e.key === ' ' || e.key === 'Enter') && input?.id === -1) { leave(); return; }
    if (e.repeat || (e.key !== ' ' && e.key !== 'Enter') || !(e.target instanceof HTMLElement) || !e.target.matches(PRESSABLE) || e.target.matches(':disabled, [aria-disabled="true"]')) return;
    const b = measure(e.target);
    if (e.type === 'keydown') setInput({ host: e.target, x: b.left + b.width * b.sx / 2, y: b.top + b.height * b.sy / 2, control: true, hover: false, press: true, id: -1 });
    else leave();
  };
  function invalidate() { surfaces.forEach(s => { s.bounds = null; }); if (input) { dirty = true; queue(); } }
  const transition = (e: Event) => { if (!(e.target instanceof Element) || !e.target.closest('.reactive-clip')) invalidate(); };
  const scroll = () => { leave(); invalidate(); };
  const clear = () => { input = null; pointerId = null; dirty = false; cancelAnimationFrame(raf); raf = 0; last = 0; [...surfaces].forEach(remove); };
  const visibility = () => { if (doc.hidden) clear(); };
  doc.addEventListener('pointermove', move, { passive: true }); doc.addEventListener('pointerdown', down, true);
  doc.addEventListener('pointerup', up, true); doc.addEventListener('pointercancel', leave, true); doc.addEventListener('pointerleave', leave);
  doc.addEventListener('keydown', keyboard, true); doc.addEventListener('keyup', keyboard, true);
  doc.addEventListener('scroll', scroll, true); doc.addEventListener('toggle', transition, true); doc.addEventListener('transitionend', transition, true);
  doc.addEventListener('visibilitychange', visibility); window.addEventListener('blur', leave); window.addEventListener('resize', invalidate);
  reduced.addEventListener('change', clear); hoverMedia.addEventListener('change', clear);
  return () => {
    stopped = true; clear(); tones.disconnect(); resize?.disconnect(); intersection?.disconnect();
    doc.removeEventListener('pointermove', move); doc.removeEventListener('pointerdown', down, true); doc.removeEventListener('pointerup', up, true);
    doc.removeEventListener('pointercancel', leave, true); doc.removeEventListener('pointerleave', leave);
    doc.removeEventListener('keydown', keyboard, true); doc.removeEventListener('keyup', keyboard, true);
    doc.removeEventListener('scroll', scroll, true); doc.removeEventListener('toggle', transition, true); doc.removeEventListener('transitionend', transition, true);
    doc.removeEventListener('visibilitychange', visibility); window.removeEventListener('blur', leave); window.removeEventListener('resize', invalidate);
    reduced.removeEventListener('change', clear); hoverMedia.removeEventListener('change', clear);
  };
}
