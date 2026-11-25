export type TrustLabel =
  | "corpus"
  | "fallback"
  | "corpus_and_fallback"
  | "contract"
  | "contract_and_corpus"
  | "contract_and_fallback"
  | "contract_corpus_and_fallback"
  | "none";

// One source of the Trust label wording: shown on answers and explained on the landing page.
export const TRUST_TEXT: Record<TrustLabel, string> = {
  corpus: "From statute text",
  fallback: "From web sources (less reliable)",
  corpus_and_fallback: "From statute text and web sources",
  contract: "From your Contract",
  contract_and_corpus: "From your Contract and statute text",
  contract_and_fallback: "From your Contract and web sources",
  contract_corpus_and_fallback: "From your Contract, statute text and web sources",
  none: "No supporting source found",
};

export const TRUST_EXPLANATION: Record<TrustLabel, string> = {
  corpus: "Every claim rests on Provisions in the Corpus, and each Citation was checked against it.",
  fallback:
    "The statutes did not cover your question, so the answer draws on web search. Read the sources and treat it with care.",
  corpus_and_fallback:
    "The statutes cover part of your question and web sources fill the rest.",
  contract:
    "The answer rests on Clauses of your own Contract, quoted word for word. Check them against your copy.",
  contract_and_corpus:
    "The answer rests on Clauses of your Contract and on Provisions in the Corpus. Each Clause is quoted word for word and each Citation was checked against the Corpus.",
  contract_and_fallback:
    "The answer rests on Clauses of your Contract, and on web search for what the law says. Read the sources and treat that part with care.",
  contract_corpus_and_fallback:
    "The answer rests on Clauses of your Contract, on Provisions in the Corpus and on web sources that fill the gaps. Treat the web part with care.",
  none: "LegalLens found nothing it can stand behind, so it says so instead of guessing.",
};

// Labels whose support is weaker than statute text alone: the answer page says
// what they mean in a line, so a reader learns it before reading the answer.
export const TRUST_NEEDS_EXPLANATION: ReadonlySet<TrustLabel> = new Set<TrustLabel>([
  "fallback",
  "corpus_and_fallback",
  "contract_and_fallback",
  "contract_corpus_and_fallback",
  "none",
]);
