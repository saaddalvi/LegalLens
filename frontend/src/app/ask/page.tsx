import type { Metadata } from "next";
import { Suspense } from "react";
import SiteHeader from "../site-header";
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
    // The header holds its place while the address is read, as the screen draws it there too.
    <Suspense
      fallback={
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 sm:px-8">
          <SiteHeader current="ask" />
        </main>
      }
    >
      <AskFromAddress searchParams={searchParams} />
    </Suspense>
  );
}
