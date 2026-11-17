export type TrustLabel = "corpus" | "fallback" | "corpus_and_fallback" | "none";

// One source of the Trust label wording: shown on answers and explained on the landing page.
export const TRUST_TEXT: Record<TrustLabel, string> = {
  corpus: "From statute text",
  fallback: "From web sources (less reliable)",
  corpus_and_fallback: "From statute text and web sources",
  none: "No supporting source found",
};

export const TRUST_EXPLANATION: Record<TrustLabel, string> = {
  corpus: "Every claim rests on Provisions in the Corpus, and each Citation was checked against it.",
  fallback:
    "The statutes did not cover your question, so the answer draws on web search. Read the sources and treat it with care.",
  corpus_and_fallback:
    "The statutes cover part of your question and web sources fill the rest.",
  none: "LegalLens found nothing it can stand behind, so it says so instead of guessing.",
};
