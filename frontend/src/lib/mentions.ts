// Finds mentions of cited Provisions in answer text, such as "BNS 103" or
// "Article 21". Only Provisions in the answer's own Citation list match, so a
// chip always has a card to open. Act names are not translated in answers, so
// the same patterns serve English and Hindi text; only the section word
// ("section" / "धारा", "Article" / "अनुच्छेद") differs.
//
// The aliases mirror ACT_ALIASES in backend/src/legallens/refs.py.

const ACT_ALIASES: Record<string, string[]> = {
  "Constitution of India": ["constitution of india"],
  "Indian Penal Code": ["indian penal code", "i.p.c.", "ipc"],
  "Code of Criminal Procedure": ["code of criminal procedure", "cr.p.c.", "crpc"],
  "Indian Evidence Act": ["indian evidence act", "evidence act", "iea"],
  "Bharatiya Nyaya Sanhita": ["bharatiya nyaya sanhita", "bns"],
  "Bharatiya Nagarik Suraksha Sanhita": ["bharatiya nagarik suraksha sanhita", "bnss"],
  "Bharatiya Sakshya Adhiniyam": ["bharatiya sakshya adhiniyam", "bsa"],
  "Indian Contract Act": ["indian contract act", "contract act"],
  "Consumer Protection Act": ["consumer protection act"],
  "Transfer of Property Act": ["transfer of property act", "tpa"],
  "Model Tenancy Act": ["model tenancy act", "mta"],
  "Code on Wages": ["code on wages"],
  "Industrial Relations Code": ["industrial relations code"],
  "Code on Social Security": ["code on social security"],
  "Occupational Safety, Health and Working Conditions Code": [
    "occupational safety, health and working conditions code",
    "osh code",
  ],
};

const ALIAS_TO_ACT = new Map(
  Object.entries(ACT_ALIASES).flatMap(([act, aliases]) => aliases.map((a) => [a, act] as const)),
);
const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const ALIAS = [...ALIAS_TO_ACT.keys()].sort((a, b) => b.length - a.length).map(escape).join("|");
const NUMBER = "(\\d+[a-z]{0,3})";
const SECTION = "(?:sections?|sec\\.?|s\\.|धारा)";
const ARTICLE = "(?:articles?|अनुच्छेद)";

// "IPC 302", "BNS section 103"
const ACT_FIRST = new RegExp(`(?<!\\w)(${ALIAS})\\s*(?:${SECTION}\\s*)?${NUMBER}(?!\\w)`, "gi");
// "section 103 of the BNS", "धारा 103 BNS"
const NUMBER_FIRST = new RegExp(
  `(?<!\\w)${SECTION}\\s*${NUMBER}\\s+(?:of\\s+(?:the\\s+)?)?(${ALIAS})(?!\\w)`,
  "gi",
);
// "Article 21", "अनुच्छेद 21": the Constitution's numbering
const ARTICLE_RE = new RegExp(`(?<!\\w)${ARTICLE}\\s*${NUMBER}(?!\\w)`, "gi");

export type ProvisionKey = { act: string; number: string };
export type Segment = { text: string } | { text: string; act: string; number: string };

export function provisionKey(c: ProvisionKey): string {
  return `${c.act}|${c.number.toUpperCase()}`;
}

/** Splits text into plain and Provision-mention segments, in order. */
export function splitMentions(text: string, cited: ProvisionKey[]): Segment[] {
  const canonical = new Map(cited.map((c) => [provisionKey(c), c.number]));
  const found: { start: number; end: number; act: string; number: string }[] = [];
  const add = (m: RegExpMatchArray, act: string, number: string) => {
    // Carry the Citation's own number, so ids built from it match the card's.
    const own = canonical.get(provisionKey({ act, number }));
    if (own !== undefined) found.push({ start: m.index!, end: m.index! + m[0].length, act, number: own });
  };
  for (const m of text.matchAll(ACT_FIRST)) add(m, ALIAS_TO_ACT.get(m[1].toLowerCase())!, m[2]);
  for (const m of text.matchAll(NUMBER_FIRST)) add(m, ALIAS_TO_ACT.get(m[2].toLowerCase())!, m[1]);
  for (const m of text.matchAll(ARTICLE_RE)) add(m, "Constitution of India", m[1]);

  found.sort((a, b) => a.start - b.start || b.end - a.end);
  const segments: Segment[] = [];
  let pos = 0;
  for (const f of found) {
    if (f.start < pos) continue; // overlaps an earlier mention
    if (f.start > pos) segments.push({ text: text.slice(pos, f.start) });
    segments.push({ text: text.slice(f.start, f.end), act: f.act, number: f.number });
    pos = f.end;
  }
  if (pos < text.length) segments.push({ text: text.slice(pos) });
  return segments;
}
