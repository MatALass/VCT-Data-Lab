export function pct(value: number, digits = 1): string { return `${(value * 100).toFixed(digits)}%`; }
export function formatPct(value: number, digits = 1): string { return pct(value, digits); }
export function smartPct(value: number): string { const pctValue = value * 100; if (value === 0) return "0.0%"; if (pctValue >= 10) return `${pctValue.toFixed(1)}%`; if (pctValue >= 1) return `${pctValue.toFixed(1)}%`; if (pctValue >= 0.1) return `${pctValue.toFixed(2)}%`; if (pctValue >= 0.01) return `${pctValue.toFixed(3)}%`; return "<0.01%"; }
export function decimal(value: number, digits = 2): string { return value.toFixed(digits); }
