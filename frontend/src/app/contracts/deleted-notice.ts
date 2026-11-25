// A Contract deleted on its own page, held until the list it returns to can say so.
type Deleted = { id: string; title: string };

let pending: Deleted | null = null;

export function noteDeleted(contract: Deleted): void {
  pending = contract;
}

// Hands the note over once.
export function takeDeleted(): Deleted | null {
  const taken = pending;
  pending = null;
  return taken;
}
