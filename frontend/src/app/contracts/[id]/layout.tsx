import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import SiteHeader from "../../site-header";
import ContractView from "./contract-view";

// Until the Contract has loaded and names the tab itself.
export const metadata: Metadata = { title: "Contract | LegalLens" };

// Where an on-screen keyboard allows it, the page shrinks to stay above it, question box and all.
export const viewport: Viewport = { interactiveWidget: "resizes-content" };

// One page per Contract, as tall as the window, held here so that moving between its
// conversations keeps it on screen: ContractView reads the conversation from the address, and
// the routes below only name those addresses. The Contract's id is a route param, which is only
// known per request, so it is read inside Suspense. The fallback reads as ContractView's own
// loading state does.
export default function ContractLayout({ children, params }: LayoutProps<"/contracts/[id]">) {
  return (
    <div className="flex h-dvh flex-col overflow-clip">
      <SiteHeader current="contracts" compact />
      <Suspense fallback={<p className="p-4 text-muted">Loading…</p>}>
        {params.then(({ id }) => (
          <ContractView id={id} />
        ))}
      </Suspense>
      {children}
    </div>
  );
}
