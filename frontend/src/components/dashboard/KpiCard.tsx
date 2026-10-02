import { type LucideIcon } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string | number;
  meta?: string | number;
  subtitle?: string;
  detail?: string;
  reference?: string;
  icon: LucideIcon;
  variant?: "default" | "success" | "warning" | "critical";
}

const iconVariantStyles = {
  default: "text-accent", success: "text-success", warning: "text-warning", critical: "text-critical",
};

// Preserve the exact formatted value; animate the change, not a parsed approximation.
function AnimatedValue({ value }: { value: string | number }) {
  return <span key={String(value)} className="value-change">{value}</span>;
}

export default function KpiCard({ title, value, meta, subtitle, detail, reference, icon: Icon, variant = "default" }: KpiCardProps) {
  return (
    <div className={`kpi-card kpi-${variant}`} data-tone={variant}>
      <div className="flex items-start justify-between gap-2">
        <p className="kpi-label">{title}</p>
        <span className={`kpi-icon ${iconVariantStyles[variant]}`}><Icon size={17} strokeWidth={1.6} /></span>
      </div>
      <div className="kpi-reading">
        <span className={/^[\d.,]/.test(String(value)) ? "kpi-value" : "kpi-value kpi-value-status"}>
          <AnimatedValue value={value} />
        </span>
        {meta !== undefined && <span className="kpi-target">/ {meta}</span>}
      </div>
      {reference && <p className="kpi-caption text-muted-foreground">{reference}</p>}
      {detail && <details className="text-xs text-muted-foreground mt-2"><summary className="cursor-pointer">Entender comparação</summary><p className="mt-2 leading-relaxed">{detail}</p></details>}
      {subtitle && <p className={`kpi-caption ${iconVariantStyles[variant]}`}>{subtitle}</p>}
    </div>
  );
}
