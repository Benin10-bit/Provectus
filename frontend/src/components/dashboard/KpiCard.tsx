import { type LucideIcon } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string | number;
  meta?: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: "default" | "success" | "warning" | "critical";
}

const variantBorder = {
  default: "border-border hover:border-border/80",
  success: "border-success/40 hover:border-success/60",
  warning: "border-warning/40 hover:border-warning/60",
  critical: "border-critical/40 hover:border-critical/60",
};

const variantGlow = {
  default: "",
  success: "hover:shadow-[0_0_20px_-5px_hsl(var(--success)/0.25)]",
  warning: "hover:shadow-[0_0_20px_-5px_hsl(var(--warning)/0.25)]",
  critical: "hover:shadow-[0_0_20px_-5px_hsl(var(--critical)/0.25)]",
};

const iconVariantStyles = {
  default: "text-accent",
  success: "text-success",
  warning: "text-warning",
  critical: "text-critical",
};

export default function KpiCard({ title, value, meta, subtitle, icon: Icon, variant = "default" }: KpiCardProps) {
  return (
    <div
      className={`rounded-lg border bg-card p-4 sm:p-5 transition-all duration-300 ${variantBorder[variant]} ${variantGlow[variant]}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] sm:text-xs font-medium tracking-wider text-muted-foreground uppercase truncate">
            {title}
          </p>
          <div className="mt-1.5 sm:mt-2 flex items-baseline gap-1 flex-wrap">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground font-mono">
              {value}
            </span>
            {meta !== undefined && (
              <span className="text-xs sm:text-sm font-medium text-muted-foreground/40 font-mono">
                / {meta}
              </span>
            )}
          </div>
          {subtitle && (
            <p className={`mt-1 text-[10px] sm:text-xs font-medium ${iconVariantStyles[variant]}`}>
              {subtitle}
            </p>
          )}
        </div>
        <div className={`p-2 rounded-lg bg-muted/50 ${iconVariantStyles[variant]}`}>
          <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
        </div>
      </div>
    </div>
  );
}
