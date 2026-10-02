/** One retained underline per tab group. Updates only when selection or dimensions change. */
export function installMovingIndicators(root: HTMLElement) {
  const selector = '.history-tabs, .timer-mode-tabs, [role="tablist"]';
  const indicators = new Map<HTMLElement, HTMLElement>();
  let frame = 0;
  const refresh = () => {
    frame = 0;
    for (const [list, marker] of indicators) if (!list.isConnected) { marker.remove(); indicators.delete(list); resize?.unobserve(list); }
    root.querySelectorAll<HTMLElement>(selector).forEach(list => {
      const selected = list.querySelector<HTMLElement>('[aria-selected="true"], [aria-pressed="true"], [data-state="active"], button.border-accent');
      if (!selected) return;
      let marker = indicators.get(list);
      if (!marker) { marker = document.createElement('i'); marker.className = 'moving-tab-indicator'; marker.setAttribute('aria-hidden', 'true'); list.classList.add('moving-tabs'); list.append(marker); indicators.set(list, marker); resize?.observe(list); }
      const a = list.getBoundingClientRect(), b = selected.getBoundingClientRect();
      if (!b.width) return;
      const transform = `translateX(${b.left - a.left + list.scrollLeft}px) scaleX(${b.width})`;
      if (marker.style.transform !== transform) marker.style.transform = transform;
    });
  };
  const queue = () => { if (!frame) frame = requestAnimationFrame(refresh); };
  const resize = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(queue);
  const observer = new MutationObserver(records => {
    if (records.some(r => r.type === 'attributes' ? (r.target instanceof Element && r.target.matches('button, [role="tab"]')) : [...r.addedNodes, ...r.removedNodes].some(n => n instanceof Element && (n.matches(selector) || Boolean(n.querySelector(selector)))))) queue();
  });
  observer.observe(root, { subtree: true, childList: true, attributes: true, attributeFilter: ['aria-selected', 'aria-pressed', 'data-state', 'class'] });
  window.addEventListener('resize', queue); queue();
  return () => { observer.disconnect(); resize?.disconnect(); cancelAnimationFrame(frame); window.removeEventListener('resize', queue); indicators.forEach((marker, list) => { marker.remove(); list.classList.remove('moving-tabs'); }); };
}
