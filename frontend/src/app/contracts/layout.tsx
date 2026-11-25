import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Your Contracts | LegalLens",
  description: "Upload a Contract and see its Clauses.",
};

// Each page under /contracts brings its own frame: the list a column, a Contract the window.
export default function ContractsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
