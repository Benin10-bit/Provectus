import { installReactiveSurfaces } from "./reactiveSurface";
import { installMovingIndicators } from "./movingIndicators";
import { useEffect, useRef, useState, type ReactNode, type CSSProperties } from "react";
import { Check, ArrowUpRight } from "lucide-react";
import { useReducedMotion } from "@/hooks/useReducedMotion";

export function SectionHeading({ title, action }: { number?: string; title: string; description?: string; action?: ReactNode }) {
  return <header className="section-intro"><div className="section-intro-copy"><div><h2>{title}</h2></div></div>{action}</header>;
}

/** A visual grouping only: fields remain mounted and keep their original handlers. */
export function FormSection({ number, title, description, complete = false, children }: { number: string; title: string; description?: string; complete?: boolean; children: ReactNode }) {
  return <section className="form-step" data-complete={complete}><header><span className="form-step-index" aria-hidden>{complete ? <Check size={15} /> : number}</span><div><h2>{title}</h2>{description && <p>{description}</p>}</div></header><div className="form-step-fields">{children}</div></section>;
}

/** Animated paint for an existing percentage. No changes to the underlying value. */
export function ProgressRing({ value, label, caption }: { value: number; label: string; caption: string }) {
  const reduced = useReducedMotion();
  const [entered, setEntered] = useState(false);
  useEffect(() => { const id = requestAnimationFrame(() => setEntered(true)); return () => cancelAnimationFrame(id); }, []);
  const percent = Math.min(100, Math.max(0, Number.isFinite(value) ? value : 0));
  return <div className="progress-orbit" role="img" aria-label={`${label}: ${Math.round(percent)}%`} style={{ "--progress": `${(entered || reduced) ? percent : 0}` } as CSSProperties}>
    <svg viewBox="0 0 120 120" aria-hidden><circle className="orbit-track" cx="60" cy="60" r="51" /><circle className="orbit-value" cx="60" cy="60" r="51" pathLength="100" strokeDasharray="100" strokeDashoffset={100 - ((entered || reduced) ? percent : 0)} /></svg>
    <div><strong>{Math.round(percent)}<small>%</small></strong><span>{caption}</span></div>
  </div>;
}

export function ValueChange({ children, value }: { children: ReactNode; value: string | number }) {
  return <span key={value} className="value-change">{children}</span>;
}

export function ActionArrow() { return <ArrowUpRight className="action-arrow" size={17} aria-hidden />; }

/** Shared interaction renderer; no pointer-driven React state. */
export function useSurfaceResponse() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const surfaceCleanup = installReactiveSurfaces();
    const indicatorCleanup = installMovingIndicators(document.body);
    return () => { surfaceCleanup(); indicatorCleanup(); };
  }, []);
  return ref;
}
