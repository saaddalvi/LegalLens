import { notFound } from "next/navigation";
import { Suspense } from "react";
import ActView from "../act-view";
import LoadingNote from "../loading-note";
import { decodeParam } from "@/lib/corpus";
import { getAct } from "@/lib/law-api";

async function ActContent({ act }: { act: string }) {
  const index = await getAct(decodeParam(act));
  if (!index) notFound();
  return <ActView index={index} />;
}

// The Act is a route param, which is only known per request, so it is read inside Suspense.
export default function ActPage({ params }: { params: Promise<{ act: string }> }) {
  return (
    <Suspense fallback={<LoadingNote />}>
      {params.then(({ act }) => (
        <ActContent act={act} />
      ))}
    </Suspense>
  );
}
