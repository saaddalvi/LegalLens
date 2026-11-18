import { connection } from "next/server";
import { Suspense } from "react";
import ActsView from "./acts-view";
import LoadingNote from "./loading-note";
import { getActs } from "@/lib/law-api";

async function Acts() {
  // The backend is read when someone asks for the page, never while the site is built.
  await connection();
  return <ActsView acts={await getActs()} />;
}

export default function LawIndexPage() {
  return (
    <Suspense fallback={<LoadingNote />}>
      <Acts />
    </Suspense>
  );
}
