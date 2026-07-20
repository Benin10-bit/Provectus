// Mapping for redação status colors based on backend logic:
// <400 Crítica | <600 Fraca | <700 Regular | <800 Boa | <900 Muito Boa | >=900 Excelente

export type RedacaoStatusInfo = {
  label: string;
  textClass: string;
  bgClass: string;
  borderClass: string;
  dotClass: string;
  rangeLabel: string;
};

const NORMALIZED: Record<string, RedacaoStatusInfo> = {
  critica: {
    label: "Crítica",
    textClass: "text-critical",
    bgClass: "bg-critical/10",
    borderClass: "border-critical/40",
    dotClass: "bg-critical",
    rangeLabel: "< 400",
  },
  fraca: {
    label: "Fraca",
    textClass: "text-destructive",
    bgClass: "bg-destructive/10",
    borderClass: "border-destructive/40",
    dotClass: "bg-destructive",
    rangeLabel: "400–599",
  },
  regular: {
    label: "Regular",
    textClass: "text-warning",
    bgClass: "bg-warning/10",
    borderClass: "border-warning/40",
    dotClass: "bg-warning",
    rangeLabel: "600–699",
  },
  boa: {
    label: "Boa",
    textClass: "text-accent",
    bgClass: "bg-accent/10",
    borderClass: "border-accent/40",
    dotClass: "bg-accent",
    rangeLabel: "700–799",
  },
  "muito boa": {
    label: "Muito Boa",
    textClass: "text-success",
    bgClass: "bg-success/10",
    borderClass: "border-success/40",
    dotClass: "bg-success",
    rangeLabel: "800–899",
  },
  excelente: {
    label: "Excelente",
    textClass: "text-success",
    bgClass: "bg-success/15",
    borderClass: "border-success/60",
    dotClass: "bg-success shadow-[0_0_8px_hsl(var(--success))]",
    rangeLabel: "≥ 900",
  },
};

const FALLBACK: RedacaoStatusInfo = {
  label: "—",
  textClass: "text-muted-foreground",
  bgClass: "bg-muted/30",
  borderClass: "border-border",
  dotClass: "bg-muted-foreground",
  rangeLabel: "",
};

export function getRedacaoStatusInfo(status: string | null | undefined): RedacaoStatusInfo {
  if (!status) return FALLBACK;
  const key = status.trim().toLowerCase();
  return NORMALIZED[key] ?? FALLBACK;
}

/** Normalize string | string[] | null into a clean list of items. */
export function toListaTextos(input: unknown): string[] {
  if (!input) return [];
  if (Array.isArray(input)) {
    return input.map((s) => String(s).trim()).filter(Boolean);
  }
  const text = String(input).trim();
  if (!text) return [];
  // Split on bullets or newlines if backend ever returns a single joined string
  const parts = text
    .split(/\r?\n|(?:^|\s)[•\-▸·]\s+/g)
    .map((s) => s.trim())
    .filter(Boolean);
  return parts.length > 0 ? parts : [text];
}
