import { Suspense } from "react";
import AskScreen from "./ask-screen";

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
