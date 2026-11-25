// The Corpus keeps the line breaks of the printed page, and most of them only mark where a
// line ran out. This keeps the breaks that start a new part of a Provision (a sub-section, a
// proviso, an Explanation, an Illustration) and joins the rest, changing no words.

// "(1)", "(2A)", "(a)", "(iv)", or the word that opens a proviso, Explanation and the like.
const OPENS_A_PART = /^(?:\((?:\d{1,3}[A-Z]?|[a-z]{1,2}|[ivxl]+|[A-Z])\)|(?:Provided|Explanation|Exception|Illustration)s?\b)/;
// "(1) of section 5", "(2).", "(g) and (h)": a number being referred to, mid-sentence.
const REFERENCE = /^\([^)]*\)\s*(?:[,.;]|of\b|(?:and|or|to)\s+\()/;
// "(2) When ..." is a sub-section even when the line above lost its full stop.
const SUB_SECTION = /^\(\d{1,3}[A-Z]?\)\s*[A-Z]/;
// A part has ended: "." ":" ";" or a dash, perhaps closing a quotation, or "; and". Without
// this, "sub-section / (1) of section 5" would break mid-sentence.
const ENDS_A_PART = /(?:[.:;—–]|--|[\s:]-|;\s*(?:and|or))["'”’\]]*$/;
// How one item of a list can lead into the next, in front of its "(b)".
const LEADS_ON = /(?:,|\b(?:and|or))$/;
// A line that is only a heading, so what follows starts afresh.
const HEADING_LINE = /^(?:Explanation|Exception|Illustration)s?$/;

function startsAPart(line: string, before: string): boolean {
  if (HEADING_LINE.test(before)) return true;
  if (!OPENS_A_PART.test(line)) return false;
  if (ENDS_A_PART.test(before) || SUB_SECTION.test(line)) return true;
  return line.startsWith("(") && LEADS_ON.test(before) && !REFERENCE.test(line);
}

export function provisionText(text: string): string {
  const parts: string[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    const last = parts[parts.length - 1];
    if (last === undefined || startsAPart(line, last)) {
      parts.push(line);
    } else {
      // A word hyphenated at the end of a line ("sub- / section") is joined without a space.
      parts[parts.length - 1] = /\p{L}-$/u.test(last) ? last + line : `${last} ${line}`;
    }
  }
  return parts.join("\n");
}
