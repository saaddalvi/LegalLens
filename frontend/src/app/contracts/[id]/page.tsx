import ContractView from "./contract-view";

export default function ContractPage({ params }: { params: Promise<{ id: string }> }) {
  return params.then(({ id }) => <ContractView id={id} />);
}
