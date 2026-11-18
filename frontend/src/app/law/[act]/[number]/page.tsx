import { notFound } from "next/navigation";
import { Suspense } from "react";
import LoadingNote from "../../loading-note";
import ProvisionView from "../../provision-view";
import { decodeParam } from "@/lib/corpus";
import { getProvision } from "@/lib/law-api";

async function ProvisionContent({ act, number }: { act: string; number: string }) {
  const provision = await getProvision(decodeParam(act), decodeParam(number));
  if (!provision) notFound();
  return <ProvisionView provision={provision} />;
}

export default function ProvisionPage({
  params,
}: {
  params: Promise<{ act: string; number: string }>;
}) {
  return (
    <Suspense fallback={<LoadingNote />}>
      {params.then(({ act, number }) => (
        <ProvisionContent act={act} number={number} />
      ))}
    </Suspense>
  );
}
