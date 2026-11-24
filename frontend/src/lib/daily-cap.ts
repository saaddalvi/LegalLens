// The daily caps on new Contracts and on Queries in Contract conversations (UTC days). The backend
// answers 429 with Retry-After: seconds until the count resets.

// "5 hours 30 minutes", "2 hours", "12 minutes". Rounds up, so it never promises too early.
export function waitText(seconds: number): string {
  const minutes = Math.max(1, Math.ceil(seconds / 60));
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  const part = (n: number, unit: string) => `${n} ${unit}${n === 1 ? "" : "s"}`;
  return [h > 0 ? part(h, "hour") : "", m > 0 ? part(m, "minute") : ""].filter(Boolean).join(" ");
}

export function retryAfterSeconds(res: { headers?: Headers }): number | null {
  const n = Number(res.headers?.get?.("Retry-After"));
  return Number.isFinite(n) && n > 0 ? n : null;
}

// The backend marks a daily-cap 429 with X-Limit-Scope: daily, to tell it from the per-minute limit.
export function isDailyCap(res: { headers?: Headers }): boolean {
  return res.headers?.get?.("X-Limit-Scope") === "daily";
}

export function dailyCapMessage(noun: string, again: string, seconds: number | null): string {
  const base = `You have reached your limit of ${noun} for today.`;
  return seconds === null
    ? `${base} Please try again tomorrow.`
    : `${base} ${again} in ${waitText(seconds)}, when the limit resets at midnight UTC.`;
}
