import type { Metadata } from "next";
import { Suspense } from "react";
import ContractView from "./contract-view";

// Until the Contract has loaded and names the tab itself.
export const metadata: Metadata = { title: "Contract | LegalLens" };

// The Contract's id is a route param, which is only known per request, so it is read inside
// Suspense. The fallback reads as ContractView's own loading state does.
export default function ContractPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<p className="text-muted">Loading…</p>}>
      {params.then(({ id }) => (
        <ContractView id={id} />
      ))}
    </Suspense>
  );
}
