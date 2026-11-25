import type { Metadata } from "next";
import { Suspense } from "react";
import ContractView from "./contract-view";

// Until the Contract has loaded and names the tab itself.
export const metadata: Metadata = { title: "Contract | LegalLens" };

// One page per Contract, held here so that moving between its conversations keeps it on screen:
// ContractView reads the conversation from the address, and the routes below only name those
// addresses. The Contract's id is a route param, which is only known per request, so it is read
// inside Suspense. The fallback reads as ContractView's own loading state does.
export default function ContractLayout({ children, params }: LayoutProps<"/contracts/[id]">) {
  return (
    <>
      <Suspense fallback={<p className="text-muted">Loading…</p>}>
        {params.then(({ id }) => (
          <ContractView id={id} />
        ))}
      </Suspense>
      {children}
    </>
  );
}
