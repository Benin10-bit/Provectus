import { type LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";

interface KpiCardProps {
  title: string;
  value: string | number;
  meta?: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: "default" | "success" | "warning" | "critical";
}

const variantBorder = {
  default: "border-border hover:border-accent/40",
  success: "border-success/40 hover:border-success/70",
  warning: "border-warning/40 hover:border-warning/70",
  critical: "border-critical/40 hover:border-critical/70",
};

const variantGlow = {
  default: "hover:shadow-[0_0_24px_-6px_hsl(var(--olive)/0.35)]",
  success: "hover:shadow-[0_0_24px_-5px_hsl(var(--success)/0.4)]",
  warning: "hover:shadow-[0_0_24px_-5px_hsl(var(--warning)/0.4)]",
  critical: "hover:shadow-[0_0_24px_-5px_hsl(var(--critical)/0.4)]",
};

const iconVariantStyles = {
  default: "text-accent",
  success: "text-success",
  warning: "text-warning",
  critical: "text-critical",
};

const variantBgIcon = {
  default: "bg-accent/10",
  success: "bg-success/10",
  warning: "bg-warning/10",
  critical: "bg-critical/10",
};

const variantBracket = {
  default: "before:border-accent/50 after:border-accent/50",
  success: "before:border-success/60 after:border-success/60",
  warning: "before:border-warning/60 after:border-warning/60",
  critical: "before:border-critical/60 after:border-critical/60",
};

// Subtle counter animation for numeric values
function useCountUp(target: number, duration = 900) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let raf: number;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(target * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
      else setVal(target);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return val;
}

function AnimatedValue({ value }: { value: string | number }) {
  // Try to detect numeric prefix like "12h" / "78%" / "312"
  const str = String(value);
  const match = str.match(/^([\d.,]+)(.*)$/);
  if (!match) return <>{value}</>;
  const num = parseFloat(match[1].replace(",", "."));
  const suffix = match[2];
  if (Number.isNaN(num)) return <>{value}</>;
  const animated = useCountUp(num);
  const display = num % 1 === 0 ? Math.round(animated) : animated.toFixed(1);
  return <>{display}{suffix}</>;
}

export default function KpiCard({ title, value, meta, subtitle, icon: Icon, variant = "default" }: KpiCardProps) {
  return (
    <div
      className={`group relative rounded-lg border bg-card p-4 sm:p-5 transition-all duration-300 overflow-hidden hover-rise
                  ${variantBorder[variant]} ${variantGlow[variant]}
                  before:content-[''] before:absolute before:top-1.5 before:left-1.5 before:w-2.5 before:h-2.5 before:border-l before:border-t ${variantBracket[variant]}
                  after:content-[''] after:absolute after:bottom-1.5 after:right-1.5 after:w-2.5 after:h-2.5 after:border-r after:border-b ${variantBracket[variant]}
      `}
    >
      {/* glow corner overlay */}
      <div className={`absolute -top-12 -right-12 w-28 h-28 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-2xl
        ${variant === "success" ? "bg-success/30" : variant === "warning" ? "bg-warning/30" : variant === "critical" ? "bg-critical/30" : "bg-accent/20"}`}
      />

      <div className="relative flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] sm:text-xs font-medium tracking-wider text-muted-foreground uppercase truncate">
            {title}
          </p>
          <div className="mt-1.5 sm:mt-2 flex items-baseline gap-1 flex-wrap">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground font-mono tabular-nums">
              <AnimatedValue value={value} />
            </span>
            {meta !== undefined && (
              <span className="text-xs sm:text-sm font-medium text-muted-foreground/50 font-mono">
                / {meta}
              </span>
            )}
          </div>
          {subtitle && (
            <p className={`mt-1 text-[10px] sm:text-xs font-medium tracking-wide ${iconVariantStyles[variant]}`}>
              {subtitle}
            </p>
          )}
        </div>

        <div className={`relative p-2 rounded-lg ${variantBgIcon[variant]} ${iconVariantStyles[variant]}
                         group-hover:scale-110 transition-transform duration-300`}>
          <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
        </div>
      </div>
    </div>
  );
}
