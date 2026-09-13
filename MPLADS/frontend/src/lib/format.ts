export function formatInteger(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "Not available";
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(number) : "Not available";
}

export function formatCurrency(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "Not available";
  const number = Number(value);
  return Number.isFinite(number)
    ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(number)
    : "Not available";
}

export function formatCompactCurrency(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "Not available";
  const number = Number(value);
  return Number.isFinite(number)
    ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", notation: "compact", maximumFractionDigits: 1 }).format(number)
    : "Not available";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function displayHouse(value: string | null | undefined): string {
  if (!value) return "Not available";
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}
