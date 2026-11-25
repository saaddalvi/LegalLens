import ConfirmDelete from "./confirm-delete";

// Deleting a Contract takes its Clauses and conversations with it.
export default function DeleteContract({
  contractId,
  title,
  returnTo,
  onDeleted,
}: {
  contractId: string;
  title: string;
  returnTo?: string;
  onDeleted: () => void;
}) {
  return (
    <ConfirmDelete
      path={`/contracts/${encodeURIComponent(contractId)}`}
      label={`Delete ${title}`}
      question="Delete this Contract? Its Clauses and conversations are deleted too. This cannot be undone."
      thing="Contract"
      returnTo={returnTo}
      onDeleted={onDeleted}
    />
  );
}
