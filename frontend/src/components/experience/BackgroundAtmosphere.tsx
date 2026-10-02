import { useEffect, useRef } from "react";

/** One compositor layer, event-driven: no running animation when the pointer rests. */
export function installAtmosphere(light: HTMLElement) {
  const media = window.matchMedia("(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)");
  let frame = 0;
  let x = 0;
  let y = 0;
  let visible = false;
  const hide = () => {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    visible = false;
    light.style.opacity = "0";
  };
  const move = (event: PointerEvent) => {
    if (!media.matches || document.hidden || event.pointerType === "touch") return;
    x = event.clientX;
    y = event.clientY;
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      light.style.transform = `translate3d(${x - 280}px, ${y - 280}px, 0)`;
      if (!visible) {
        visible = true;
        light.style.opacity = "1";
      }
    });
  };
  const visibility = () => { if (document.hidden) hide(); };
  document.addEventListener("pointermove", move, { passive: true });
  document.documentElement.addEventListener("pointerleave", hide);
  document.addEventListener("visibilitychange", visibility);
  window.addEventListener("blur", hide);
  media.addEventListener("change", hide);
  return () => {
    hide();
    document.removeEventListener("pointermove", move);
    document.documentElement.removeEventListener("pointerleave", hide);
    document.removeEventListener("visibilitychange", visibility);
    window.removeEventListener("blur", hide);
    media.removeEventListener("change", hide);
  };
}

export default function BackgroundAtmosphere() {
  const light = useRef<HTMLDivElement>(null);
  useEffect(() => light.current ? installAtmosphere(light.current) : undefined, []);
  return <div className="background-atmosphere" aria-hidden="true">
    <div className="atmosphere-contours" />
    <div ref={light} className="atmosphere-light" />
  </div>;
}
