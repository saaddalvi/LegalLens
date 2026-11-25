import type { Metadata } from "next";
import { Suspense } from "react";
import AskScreen from "./ask-screen";

export const metadata: Metadata = {
  title: "Ask a question | LegalLens",
  description: "Ask a question about Indian law in English or Hindi.",
};

async function AskFromAddress({ searchParams }: Pick<PageProps<"/ask">, "searchParams">) {
  const { q } = await searchParams;
  const initialQuery = (Array.isArray(q) ? q[0] : q)?.trim();
  return <AskScreen initialQuery={initialQuery || undefined} />;
}

export default function AskPage({ searchParams }: PageProps<"/ask">) {
  return (
    <Suspense>
      <AskFromAddress searchParams={searchParams} />
    </Suspense>
  );
}
