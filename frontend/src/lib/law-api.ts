import { cacheLife } from "next/cache";
import type { ActIndex, ActSummary, Provision } from "./ask-types";

// Server-side reads of the law, for the pages under /law. The text of an Act changes only
// when the Corpus is rebuilt, so each read is cached; a missing Act or Provision is a
// result (null) and is cached too, while any other failure is thrown and never cached.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 15_000; // a sleeping Space can take a while to wake

async function read<T>(path: string): Promise<T | null> {
  const res = await fetch(`${API_URL}${path}`, { signal: AbortSignal.timeout(TIMEOUT_MS) });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`The LegalLens service answered ${res.status} for ${path}`);
  return (await res.json()) as T;
}

export async function getActs(): Promise<ActSummary[]> {
  "use cache";
  cacheLife("hours");
  return (await read<ActSummary[]>("/acts")) ?? [];
}

export async function getAct(act: string): Promise<ActIndex | null> {
  "use cache";
  cacheLife("hours");
  return read<ActIndex>(`/acts/${encodeURIComponent(act)}`);
}

export async function getProvision(act: string, number: string): Promise<Provision | null> {
  "use cache";
  cacheLife("hours");
  return read<Provision>(`/provision/${encodeURIComponent(act)}/${encodeURIComponent(number)}`);
}
