import { TRUST_TEXT, type TrustLabel } from "@/lib/trust-labels";

// A Trust label, drawn as a stamp-pad impression. `press` plays the stamping
// animation once, when an answer settles.
export default function Stamp({
  trust,
  press = false,
  large = false,
}: {
  trust: TrustLabel;
  press?: boolean;
  large?: boolean;
}) {
  const size = large ? "stamp-large text-lg" : "text-sm";
  return (
    <span data-trust={trust} className={`stamp ${size} ${press ? "stamp-in" : ""}`}>
      {TRUST_TEXT[trust]}
    </span>
  );
}
