import { type LucideIcon } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: "default" | "success" | "warning" | "critical";
}

const variantStyles = {
  default: "border-border",
  success: "border-success/50",
  warning: "border-warning/50",
  critical: "border-critical/50",
};

const iconVariantStyles = {
  default: "text-accent",
  success: "text-success",
  warning: "text-warning",
  critical: "text-critical",
};

export default function KpiCard({ title, value, subtitle, icon: Icon, variant = "default" }: KpiCardProps) {
  return (
    <div
      className={`rounded-md border bg-card p-5 transition-all duration-300 hover:hud-glow animate-slide-in ${variantStyles[variant]}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
            {title}
          </p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-foreground font-mono">
            {value}
          </p>
          {subtitle && (
            <p className={`mt-1 text-xs ${iconVariantStyles[variant]}`}>
              {subtitle}
            </p>
          )}
        </div>
        <Icon className={`h-5 w-5 ${iconVariantStyles[variant]}`} />
      </div>
    </div>
  );
}
