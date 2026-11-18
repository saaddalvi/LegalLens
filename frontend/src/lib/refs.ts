// References to Provisions as the backend stores them in `superseded_by` and
// `supersedes`: "<Act> <number>", "; "-separated when there are several
// (see backend/src/legallens/refs.py).

export type ProvisionRef = { act: string; number: string };

export function parseRefs(value: string | null): ProvisionRef[] {
  if (!value) return [];
  return value.split("; ").flatMap((ref) => {
    const at = ref.lastIndexOf(" ");
    return at > 0 ? [{ act: ref.slice(0, at), number: ref.slice(at + 1) }] : [];
  });
}
