# LegalLens: ingestion

How the **Corpus** is built: where each **Act** comes from, how its text becomes **Provisions** (Chunks), how old-to-new links are recorded, how the build is checked, and how the result is stored for search. Terms in **bold** are defined in `GLOSSARY.md`. For how the Corpus is used at question time, see `DATA_FLOW.md`; for the HTTP side, `API_ROUTES.md`. Design decisions are in `docs/adr/0002` (one Chunk per Provision) and `docs/adr/0003` (embedding model).

## At a glance

```
 pinned sources                  adapters / parsers              records → Provisions             store
 ──────────────                  ──────────────────              ────────────────────             ─────
 Constitution JSON (GitHub) ──▶  parse_constitution  ──────────▶ ┐
 6 criminal-law PDFs        ──▶  pdf_text adapters  ──▶ section  │  Provision objects ─▶ apply_mappings ─▶ build_report ─▶ Corpus.add
 8 everyday-law PDFs        ──▶  pdf_text adapters      records ─┘  (one per Section)    (old ⇄ new links)  (count checks)   (split → embed → Chroma)
 3 NCRB mapping tables      ──▶  mapping_tables parsers ────────────────────────────────▶ ┘
```

Run it with:

```bash
cd backend && python -m legallens.build_corpus
```

Entry point: `backend/src/legallens/build_corpus.py`. The package `backend/src/legallens/ingestion/` holds everything else.

**Result:** 3,693 Provisions across 15 Acts, stored in a local Chroma vector store at `backend/data/chroma` (gitignored).

| Act | Provisions | Status stored | Source |
|---|---|---|---|
| Constitution of India | 499 | `in_force` (or `repealed` for omitted Articles) | civictech-India JSON dataset + patches |
| Indian Penal Code | 575 | `repealed` | Indian Kanoon PDF + patches |
| Code of Criminal Procedure | 535 | `repealed` | India Code PDF |
| Indian Evidence Act | 185 | `repealed` | India Code PDF |
| Bharatiya Nyaya Sanhita | 358 | `in_force` | Gazette PDF |
| Bharatiya Nagarik Suraksha Sanhita | 531 | `in_force` | Gazette PDF |
| Bharatiya Sakshya Adhiniyam | 170 | `in_force` | Gazette PDF |
| Indian Contract Act | 192 | `in_force` | Legislative Department bare-act PDF, via Drishti Judiciary (third-party mirror) |
| Consumer Protection Act | 107 | `in_force` | Gazette PDF (via PRS) |
| Transfer of Property Act (Chapter V only) | 14 | `in_force` | International Insolvency Institute PDF (unofficial) |
| Model Tenancy Act | 47 | `model` | LiveLaw PDF (unofficial) |
| Code on Wages | 69 | `in_force` | Gazette PDF |
| Industrial Relations Code | 104 | `in_force` | Gazette PDF (via PRS) |
| Code on Social Security | 164 | `in_force` | Gazette PDF (via PRS) |
| Occupational Safety, Health and Working Conditions Code | 143 | `in_force` | Gazette PDF (via PRS) |

The counts are the exact expected totals enforced by the build (see [Validation](#validation)). The Constitution is held to a range (480 to 520); the built Corpus has 499.

---

## 1. Sources

Two kinds of source feed the build: one open dataset that is downloaded, and PDFs that a person must place by hand.

### 1.1 Constitution: an open dataset, downloaded

`fetch_constitution()` in `ingestion/sources.py` downloads `constitution_of_india.json` from `civictech-India/constitution-of-india`, **pinned to commit `48871da…`** and checked against `DATASET_SHA256`. It is saved to `backend/data/raw/constitution_of_india.json`. Details:

- If the file is already present it is not downloaded again, but its hash is **checked every run**. A mismatch raises `RuntimeError`.
- The download is written to a `.part` file and renamed, so a truncated file is never left at the final path.
- Each record is `{"article": …, "description": …}`.

### 1.2 Statutes: PDFs, pinned by hash

India Code answers automated downloads with 504s and the Gazette needs a manual download, so none of the PDFs are fetched. You put them in `backend/data/raw/` (gitignored) and `ingestion/sources.py` pins each by **filename and sha256** (`PinnedPdf`). `_read_pinned()` refuses to read a missing file (the error names the file, its description and where to put it) or one whose hash differs.

`backend/data/raw/criminal/` (`CRIMINAL_PDFS`):

| Key | File | What it is |
|---|---|---|
| `bns` | `bns_gaz.pdf` | BNS 2023, Gazette of India Extraordinary 250883 |
| `bnss` | `bnss_gaz.pdf` | BNSS 2023, Gazette 250884 |
| `bsa` | `bsa_gaz.pdf` | BSA 2023, Gazette 250882 |
| `crpc` | `crpc_ic.pdf` | CrPC 1973, India Code handle 15272 |
| `iea` | `iea_1872.pdf` | Evidence Act 1872, India Code consolidated text, last updated 13-3-2020 |
| `ipc` | `ipc_ik.pdf` | IPC 1860, Indian Kanoon print as of 7 Feb 2022 (**unofficial**) |
| `ipc_ic_2012` | `ipc_ic_2012.pdf` | IPC, India Code text from before 2013. Used only to check the Kanoon text |
| `ipc_unknown_2016` | `ipc_unknown_2016.pdf` | IPC, unattributed text from about 2016. Used only to check the Kanoon text |
| `ncrb_bns` | `ncrb_bns.pdf` | NCRB Sankalan: BNS plus its BNS-IPC corresponding-section table |
| `ncrb_bnss` | `ncrb_bnss.pdf` | NCRB Sankalan: BNSS plus its BNSS-CrPC table |
| `ncrb_bsa` | `bsa_ncrb.pdf` | NCRB Sankalan: BSA plus its BSA-IEA table |

`backend/data/raw/everyday/` (`EVERYDAY_PDFS`):

| Key | File | What it is |
|---|---|---|
| `contract` | `contract_act_ld.pdf` | Indian Contract Act 1872 (No. 9 of 1872), the Legislative Department's bare-act text with amendment footnotes, as mirrored by Drishti Judiciary. India Code answers with 504s |
| `cpa` | `cpa_prs.pdf` | Consumer Protection Act 2019 (No. 35 of 2019), Gazette print via PRS India |
| `wages` | `wages_gaz.pdf` | Code on Wages 2019 (No. 29 of 2019), egazette.gov.in |
| `ir` | `ir_prs.pdf` | Industrial Relations Code 2020 (No. 35 of 2020), Gazette via PRS |
| `ss` | `ss_prs.pdf` | Code on Social Security 2020 (No. 36 of 2020), Gazette via PRS |
| `osh` | `osh_prs.pdf` | OSH Code 2020 (No. 37 of 2020), Gazette via PRS |
| `tpa` | `tpa_ila.pdf` | Transfer of Property Act 1882, International Insolvency Institute print (unofficial); only Chapter V is used |
| `mta` | `mta_livelaw.pdf` | Model Tenancy Act 2021, MoHUA text as printed by LiveLaw (unofficial) |
| `ss_ic` | `ss_ic.pdf` | Code on Social Security, India Code text as on 21 Nov 2025. Used only to check the Gazette print |

Why pin by hash: the build must be reproducible. A silently different PDF would shift section boundaries and corrupt Provisions without any error.

**Provenance caveats** (recorded in `backend/sources/criminal_codes.json` and `everyday_acts.json`):

- The IPC is **not official**. India Code no longer lists it (repealed 1 July 2024), its older copy predates the 2013 and 2018 amendments, and the third copy (about 2016) lacks 376AB, 376DA, 376DB and 376E. The Kanoon print is the only one both complete and current.
- The Transfer of Property Act and Model Tenancy Act prints are unofficial.
- The Indian Contract Act is the Legislative Department's text, but the PDF comes from a third-party mirror, not from India Code or the Department (both unreachable), and its body text has not been diffed against an independent copy. Its 192 live sections are checked against the print's own contents list. Sale of goods (Chapter VII, sections 76-123) and partnership (Chapter XI, 239-266) are repealed and have no text, so they are not Provisions.
- The four Labour Codes and the Consumer Protection Act are the Gazette prints **as enacted**, so they carry no later amendments. The Labour Codes were brought into force on 21 November 2025 (per India Code and press reports; not checked against the Gazette notification itself), so they are stored as `in_force`.
- The Acts the Labour Codes replaced (for example the Minimum Wages Act 1948) are not in the Corpus, so no repealed-to-superseding link is recorded for them.

---

## 2. From source text to section records

Every statute adapter produces the same intermediate shape, a **section record**:

```json
{ "section": "302", "chapter": "Chapter XVI", "text": "…" }
```

(an optional `title` is carried by some adapters and ignored later). Because the shape is shared, one parser (`parse_section_records`) serves all 14 statutes; the Constitution has its own because its source is JSON.

PDF text is extracted per page with `pypdf` (`pdf_pages()` in `ingestion/pdf_text.py`). Each Act family then has an adapter that handles that print's quirks. Nothing is machine-learned; these are deterministic, regex- and heuristic-based parsers, each exercised in `backend/tests/` against short real excerpts.

### 2.1 Constitution (`ingestion/constitution.py`)

- Source records are `{article, description}`. **Article 0 is the Preamble and is skipped** (it is not an Article).
- Article numbers are normalised (whitespace removed, upper-cased) and must match `^\d+[A-Z]*$`, else `ValueError`.
- **Chapter** is the Constitution **Part** (`Part III`), derived from the Article number: `_PART_STARTS` lists the first Article of each of the 26 Parts (including IVA, IXA, IXB, XIVA) and a number takes the last Part starting at or before it.
- **Status** is `repealed` when the text begins with `Rep.`, `Omitted` or `Repealed` (optionally after a bracketed amendment note); otherwise `in_force`.
- Text is cleaned: runs of spaces collapsed, blank lines dropped.
- Duplicate Article numbers in the source are an error.
- Output is sorted in statute order (`21` < `21A` < `22`).
- **Patches** (`backend/sources/constitution_patches.json`) are applied last; see [section 4](#4-recorded-patches).

### 2.2 Gazette Acts: BNS, BNSS, BSA and five everyday Acts (`gazette_sections`)

Used for BNS, BNSS, BSA, Consumer Protection Act, Code on Wages, Industrial Relations Code, Code on Social Security and the OSH Code. The Gazette layout puts side-headings and "40 of 2019." citation notes into a block just above each page footer. The adapter:

- drops the cover block (the Hindi-font cover and the assent block on page 1) and everything before section 1;
- drops running heads (`2 THE GAZETTE OF INDIA …`, `SEC. 1] THE GAZETTE …`);
- drops the marginal block: side-headings are detected by a length heuristic (short, not all caps, not starting with `(` / `Explanation` / `Illustration` / `Provided` / `Exception`, not ending in `;` `:` or a dash), in runs of at least 4 lines. A trailing Act-citation note glued onto a line (`enactments.10 of 1897.`) is stripped;
- tracks `CHAPTER …` headings to set each record's chapter;
- requires section numbers to **follow the previous number** (`follows()`), so stray numbered lines in the body do not start a new section;
- stops at the Act's end (`THE SCHEDULE`, a rule of dashes).

Consequence: a Chunk is **the section's operative text without its marginal title**. BNS and BNSS Chunks carry no titles.

Known limits (documented in `criminal_codes.json`): a few words are split mid-token where the Gazette text layer is irregular (for example `either d escription` in BNS 323); BNSS 359 (compounding tables) is a table flattened by the text layer, so word order inside its cells is not reliable; a one-word final line at a page end could in principle be dropped with the side-headings (checked against the NCRB text, no loss found in BNS or BNSS).

### 2.3 Code of Criminal Procedure (`crpc_sections`)

India Code PDF. The adapter skips the table of contents (its headings lack the `.—` before the text), the **footnotes under each page's rule**, **State amendment blocks**, and amendment markers (`1[` and `]`). The result is the **central Act's text only**. Includes lettered insertions such as `41A` and `105A`-`105L`; `105-I` and `265-I` are printed hyphenated in the PDF and are stored as `105I` and `265I`. 535 Chunks.

### 2.4 Indian Evidence Act (`iea_sections`)

India Code consolidated text. Skips the contents list (everything before the preamble), footnotes, page numbers, PART headings and amendment markers. A heading counts only if it is **the next section number and has the `––` between title and text**. 185 Chunks: 167 numbered sections plus 18 lettered insertions (22A, 45A, 47A, 53A, 65A, 65B, 67A, 73A, 81A, 85A-85C, 88A, 90A, 111A, 113A, 113B, 114A). Section 2 (and 22A, 82, 88, 113, 166) are kept as repealed or deleted Chunks. Footnote reference digits inside text (`Judges 9 and Magistrates 10`) stay, because they cannot be told from real numbers safely.

### 2.5 Indian Penal Code (`kanoon_ipc_sections` + `repair_kanoon`)

The hardest source. The Indian Kanoon PDF's text layer is damaged, so `repair_kanoon()` first repairs characters: a dash printed as a euro sign, quotation marks and apostrophes, words split at a line end, footnote digits stuck to words, glued enumerators and labels. Then:

- A heading is a line `N. Title` whose N is the **next section number**; a title that wraps ends on a later line with a dash. Repealed sections are single `[Title.] Rep. by …` lines. A few headings (376AB) have no dash.
- Page furniture and chapter titles are dropped. The case-law notes Kanoon appends to sections 303, 377 and 497 are removed.
- Roman and Arabic chapter numbers are normalised.
- Kanoon **loses section 333 and prints 334 twice**, and has some typos. These are fixed by recorded patches ([section 4](#4-recorded-patches)).

Result: 575 Chunks, 511 numbered sections plus lettered insertions, including 21 repealed sections that survive as one-line repeal notes (13, 58, 161 to 165A and so on). Square brackets round amended passages (for example in 376) are left in.

### 2.6 Transfer of Property Act (`tpa_lease_sections`)

Only **Chapter V (leases), sections 105-117 plus the inserted 114A**: 14 Chunks. The print drops amendment footnotes into the middle of sections, glues a footnote number onto some section numbers (`2107.` is section 107) and runs sub-headings into the body. The adapter removes footnotes, sub-headings, `1[` markers and `[***]` deletions. The source's own typos are kept (for example `A.C's lease` in the section 116 illustration).

### 2.7 Model Tenancy Act (`model_tenancy_sections`)

The LiveLaw print interleaves each clause's side-heading and Act citations (`41 of` / `2006.`) into the text. The adapter reads the **table of contents titles** and removes each clause's title by matching it, including a title wrapped across lines or placed in a neighbouring clause's text. Page furniture (`Page N of M`, `WWW.LIVELAW.IN`) is dropped. The body ends at the First Schedule, whose forms also number lines `1.`, `2.`. 47 clauses in 8 chapters.

Its Chunks use the Status `model`: it is a template that States may adopt (its own text reads `(Name of State/Union territory) Tenancy Act`), not law in force by itself. The LLM prompt and the `/law` page say so.

### 2.7a Indian Contract Act (`contract_act_sections`)

The Legislative Department print puts each section as `27. Agreement in restraint of trade, void.—Every agreement …`, so the title is inline, not in a margin; it is kept as the record's `title` and left out of the text. The adapter:

- starts after the date line `[25th April, 1872.]`, so the contents list is skipped;
- drops page numbers, the mirror's footer line and the footnotes under each page's line of spaces;
- removes amendment marks (`2[` … `]`), the stars that stand for repealed text (`3*****`) and footnote digits glued to words (`arbitration4.`) or to a section number (`1151.` is 151);
- accepts a heading only if it is the next section number (`follows()`), and lets a title wrap over up to three lines;
- leaves out repealed sections (entries like `76.[…] Rep. by s. 65`) and the repealed Chapters VII and XI, and stops at the repealed Schedule. A section's unnumbered paragraphs (section 1's "Extent, Commencement") stay in its text.

The Chunks are 1-75 (with 19A) and 124-238 (with 178A), in Preliminary and Chapters I-VI, VIII, IX and X. `scripts/verify_everyday_acts.py` checks them against the Act's published numbering and the print's contents list; `scripts/smoke_retrieval.py` checks that s.27 and s.74 are retrievable.

### 2.8 Section numbers, ordering, and Status

For all statutes, `parse_section_records()`:

- normalises the number (`^\d+[A-Z]{0,3}$`, whitespace removed, upper-cased) and rejects anything else;
- trims chapter, cleans text (collapses spaces, drops blank lines);
- sets **Status** from the Act's configuration (`CriminalAct.status`), not from the text: IPC, CrPC and IEA are `repealed`; BNS, BNSS, BSA and the everyday Acts are `in_force`; the Model Tenancy Act is `model`;
- **rejects duplicate section numbers** within an Act (`ValueError`);
- returns the Provisions sorted in statute order.

The per-Act configuration lives in `CRIMINAL_ACTS` (`ingestion/criminal_codes.py`) and `EVERYDAY_ACTS` (`ingestion/everyday_acts.py`), each holding the Act name, Status and exact expected Chunk count.

### 2.9 Chunking decision: one Chunk per Provision

Each Section or Article is **one Provision**, not a fixed-size window (ADR 0002). That makes a **Citation** map to exactly one retrievable unit and keeps the Hallucinated-citation check exact. The cost is a per-Act parser (everything above). Long Provisions are split *for embedding only*; see [section 6](#6-storage-and-embedding).

---

## 3. Old-to-new mappings (repeal handling)

The three new criminal codes replaced three old ones. The corresponding-section tables published in NCRB's Sankalan compilations drive a two-way link recorded on each Provision:

| New Act | Replaces | Table parser |
|---|---|---|
| BNS | IPC | `parse_bns_table` |
| BNSS | CrPC | `parse_corresponding_table` |
| BSA | Evidence Act | `parse_bsa_table` |

(`ingestion/mapping_tables.py`; `parse_bns_table` and `parse_bsa_table` share `_parse_sequential_table`.)

The PDF flattens a two-column table into text, so a row's numbers can land several lines apart. The parsers handle the row shapes that occur:

- a plain pair (`8. Court of Session 9. Court of Session.`), on one line or spread out;
- `Deleted 8. Metropolitan areas.`: an old section with no new counterpart;
- `86. …` then `New Section`: a new section with no old counterpart;
- sub-section rows (`35(1)`, `35(2) 41(2)`, `43(3) New Sub-Section`), which **collapse to whole-section pairs**;
- one new section mapping to **several** old ones (BNSS 35 maps to CrPC 41 and 41A) and the reverse.

For BNSS the new section's heading is a plain number opening a line, above the last new number, in a row whose old number is known; anything else after the first number is an old section. For BSA and BNS the new numbers run 1..N with no letters, so a heading is the next row only when it is exactly the next number and the current row already has its old counterpart (or is `New Section`).

`apply_mappings()` then writes the links onto the Provisions:

- every mapping names `old_act`/`old_number` and `new_act`/`new_number`;
- the old Provision gets `superseded_by`, the new one gets `supersedes`, both as `"<Act> <number>"` references joined by `"; "` when there are several (see `refs.py`);
- **a mapping that names a Provision not in the Corpus is an error** (the mapping or the source is wrong).

Provisions with no counterpart get **no link**: CrPC sections marked `Deleted`, BNSS sections marked `New Section` (10 and 9 respectively; `verify_criminal_codes.py` lists them), IEA sections 2, 22A, 82, 88, 113 and 166, BSA sections 61 and 170, and BNS sections 48, 69, 95, 111, 112, 113, 152, 226, 304 and 358. 29 IPC sections for which the NCRB table has no row are recorded under `not_in_mapping_table` in `criminal_codes.json`.

These links are what let LegalLens answer an IPC-numbered Query with the BNS Provision (for example IPC 302 to BNS 103) and show the Trust label and repeal note.

---

## 4. Recorded patches

Source defects are never fixed by hand-editing a file. Each fix is **data**, recorded with a reason, and applied at build time. A patch that no longer fits **fails the build**, which is how a changed source is noticed.

### Constitution (`backend/sources/constitution_patches.json`)

Verified against the official Constitution of India, Ministry of Law and Justice, as on May 2022 (India Code CDN PDF, sha256 `4699ff98…`). Operations:

- `add`: an Article absent from the dataset (for example 43B, inserted by the 97th Amendment). Fails if the Article already exists.
- `replace`: corrects an Article's text. Fails if the Article is missing.

Deliberate non-changes, recorded in the file's `notes`: Articles **124 and 222 keep the pre-NJAC text** (the official text shows the 99th Amendment version, which the Supreme Court struck down, so the dataset text is the operative law); **124A-124C are not added** (also struck down); 232 is not added (only a substitution note, no text); 370 matches the official text.

### IPC (`backend/sources/ipc_patches.json`, `ingestion/record_patches.py`)

`apply_record_patches()` takes `{"replacements", "texts", "insertions"}`:

- **replacement**: a section and a `find` text that must occur **exactly once** (whitespace runs match a space, because the source wraps mid-phrase). Example: section 19 `under 21 Regulation` becomes `under Regulation` (21 was a footnote number).
- **text**: fills a section the source printed with no text. The section must exist and be empty.
- **insertion**: adds a whole section the source lost (333), after the section named in `after`. Fails if it is already present.

A fix is recorded **only where both older IPC copies agree**, on a section neither amended after 2012 nor otherwise doubtful. Other single-word differences from the older copies (spelling such as `authorised`) are left as Kanoon prints them.

---

## 5. Validation

Validation happens in two layers: inside every build, and in separate verify scripts.

### 5.1 During the build (`ingestion/report.py`)

`build_report()` produces per-Act counts and a list of warnings. **Any warning makes the build fail.**

- Count outside the Act's expected range (`EXPECTED_COUNTS`). All 13 statutes are exact (min = max); the Constitution is 480-520.
- An Act with Chunks but **no configured range**.
- A **required Act with no Chunks at all** (a build that silently lost a whole Act). `build_corpus` requires the Constitution and all 13 statutes.
- Duplicate `(act, number)`.
- Any Provision with empty text.

On top of that, the parsers themselves raise on duplicate numbers, unparseable numbers, patches that no longer fit and mappings naming missing Provisions.

### 5.2 Verify scripts (`backend/scripts/`, run on demand)

| Script | Checks |
|---|---|
| `verify_constitution.py OFFICIAL.pdf` | Every word of each Article appears **in order** in the official PDF, and no official Article is missing. Catches stale or wrong text; **cannot** detect text that is merely truncated. Headings it cannot locate are listed for manual check. |
| `verify_criminal_codes.py` | Counts and gap-free numbering; section numbers against an independent index (NCRB's own index for BNS/BNSS/BSA; CrPC and IEA tables of contents); for BNS/BNSS/BSA, every word of each Chunk in order in the NCRB's separately extracted reprint (accepted differences are listed in `criminal_codes.json`); mapping coverage in both directions (every section is a mapping target/source, `New Section`, `Deleted`, or listed as absent from the table); IPC compared word for word with two older copies, **failing if the list of unverified sections changes**. |
| `verify_everyday_acts.py` | Section and chapter totals against the published ones; gap-free numbering; Code on Social Security section numbers against the "Arrangement of Sections" of the India Code copy as on 21 Nov 2025; Transfer of Property Act is exactly 105-117 + 114A in Chapter V; no leftover Gazette furniture, footnotes or amendment marks. |

### 5.3 What is NOT verified

Stated plainly in the source files so it is not mistaken for verified text:

- **Not diffed against India Code itself:** the BNS/BNSS/BSA/CrPC/IEA/IPC text (ticket 08, last checkbox), and the CPA, Wages, IR and OSH Codes and Transfer of Property Act text (India Code returned 504s when tried 16 Nov 2026). Count and numbering do agree with the published totals.
- **CrPC and IEA have no second copy** to diff against, so their body text rests on one PDF plus the table-of-contents check.
- **IPC:** 62 sections match only the 2016 copy and 31 match neither older copy (amended or added after 2016, repealed-section notes, small wording differences). For those, only the Kanoon print supports the text. The exact lists are `ipc_verification.only_2016_copy` and `neither_copy` in `criminal_codes.json`.
- **Model Tenancy Act:** only checked for 47 clauses in 8 chapters, numbered 1..47 without a gap, with each side-heading removed. It is not on India Code.
- Page footnote reference digits left inside IEA text, and side-heading stripping being a length heuristic (see [2.2](#22-gazette-acts-bns-bnss-bsa-and-five-everyday-acts-gazette_sections)).

---

## 6. Storage and embedding

`Corpus` (`backend/src/legallens/corpus.py`) wraps a Chroma persistent collection named `provisions`, with **cosine** distance.

### 6.1 Splitting long Provisions into pieces

The embedding model reads only about 512 tokens, so a long Provision (BNS 303 is 5.9 KB) was matched on its opening alone and a plain-language Query could not reach the part that answered it. `split_text()` therefore splits any Provision longer than **800 characters (`PIECE_CHARS`)** into pieces of at most about 800 characters, **breaking only at line ends** (a line is never cut). Each piece is embedded separately.

A Provision is still one unit everywhere outside the store: `get`, `count`, `list_act` and `search` return whole Provisions, and one Citation maps to one Provision (ADR 0002 amendment).

### 6.2 What is stored per piece

| Chroma field | Value |
|---|---|
| id | `"<act>|<number>|<piece index>"`, for example `Constitution of India|21A|0` |
| document | the piece's text |
| embedding | vector from the local embedder |
| metadata | `act`, `chapter`, `number`, `status`, `superseded_by` (`""` if none), `supersedes` (`""` if none), `piece` (index) |
| metadata `text` | **only on piece 0**: the whole verbatim Provision |

Piece 0 is therefore the canonical record: `get(act, number)` reads `"<act>|<number>|0"` and rebuilds the Provision from its metadata, so the verbatim text a Citation shows never comes from a fragment. `count()` and `act_counts()` count `piece == 0` rows.

Writes are **upserts in batches of 1,000** because Chroma rejects a single upsert above about 5,400 records.

### 6.3 Embeddings (`embeddings.py`, ADR 0003)

- Model: **`Qwen/Qwen3-Embedding-0.6B`** via `sentence-transformers`, run locally (about 1.1 GB of weights, downloaded from Hugging Face on first use). Vectors are L2-normalised.
- It is **multilingual**, so Hindi Queries match English Provisions without a paid embedding API.
- It is asymmetric: Queries are embedded with the model's built-in `query` instruction prompt (`is_query=True`); Provisions are embedded with **no prompt** (`is_query=False`).
- The model loads lazily on first `embed()` call.
- **Vectors from different models do not mix.** Changing `MODEL_NAME` requires a full rebuild.

Chosen over `multilingual-e5-small/base/large` and `bge-m3` by measurement on the golden set (expected Provision in the top 10 for 23 of 26 retrieval cases, up from 20 for e5-small), at roughly 8 times the embedding time of e5-small. The full Corpus builds in about 4 minutes on an Apple-silicon laptop. Numbers and trade-offs are in ADR 0003; `scripts/compare_embeddings.py MODEL (whole|pieces)` reproduces them without touching the Corpus.

### 6.4 Search

`Corpus.search(query, k)` embeds the Query, fetches `k × 5` pieces, then keeps the first `k` **distinct Provisions** in order of their best piece, and returns whole Provisions.

---

## 7. The build procedure

`python -m legallens.build_corpus [--out PATH] [--raw-dir PATH] [--patches PATH]`

| Option | Default |
|---|---|
| `--out` | `$CHROMA_PATH`, else `backend/data/chroma` |
| `--raw-dir` | `backend/data/raw` |
| `--patches` | `backend/sources/constitution_patches.json` |

Steps:

1. **Safety check:** if `--out` exists but is not a Chroma store (no `chroma.sqlite3`), exit 2 without touching it.
2. **Fetch the Constitution** (hash-checked, see 1.1).
3. **Load all PDFs** (`load_criminal_codes`, `load_everyday_acts`), each checked by hash, then run through its adapter. The IPC also gets `ipc_patches.json` applied. The three mapping tables are parsed. A missing PDF prints which file and where to put it, and exits 2.
4. **Build in a staging directory** beside the target (`<out>.building`), removing any previous staging directory first. A real `LocalEmbedder` is used.
5. **`build()`**: `parse_constitution` (with patches), `parse_criminal_code` for each of six Acts, `parse_everyday_act` for each of eight, `apply_mappings`, `Corpus.add` (split, embed, upsert), then `build_report`.
6. Print Chunk counts per Act and any `WARNING:` lines.
7. **Swap only a clean result.** With any warning: exit 1, **leave the existing store alone** and keep the rejected build in the staging directory for inspection. Otherwise delete the old store, rename staging into place, and print `Built Corpus at … (N Chunks stored)`.

Exit codes: `0` built, `1` validation warnings (nothing replaced), `2` missing source file or `--out` is not a Chroma store.

The build always rebuilds **from scratch**. There is no incremental update. A bad parse can never destroy a good store.

---

## 8. After the build

- **Sample fixture:** if the store is empty, the app (not the build) seeds 3 sample Provisions from `backend/fixtures/sample_provisions.json` (Articles 14 and 21, IPC 302) so a fresh clone runs. Setting `REQUIRE_CORPUS=1` turns that into an error instead. `GET /ready` reports `"fixture": true` when only the sample is loaded.
- **Deployment:** the Corpus and PDFs are gitignored, so the repository alone cannot be built. `scripts/deploy_space.py` copies the built store next to the Dockerfile and code and uploads them to the Hugging Face Space. It **refuses to ship an empty Corpus or the sample fixture**. The image sets `REQUIRE_CORPUS=1`.
- **Reading it back:** the `/acts`, `/acts/{act}` and `/provision/{act}/{number}` routes read the Corpus directly (see `API_ROUTES.md`); question answering searches it (see `DATA_FLOW.md`). The Hallucinated-citation check looks every cited Provision up in this store.

---

## 9. Common tasks

**Rebuild after changing a parser, patch or the embedding model**

```bash
cd backend && python -m legallens.build_corpus
```

**Re-verify**

```bash
cd backend
python scripts/verify_constitution.py path/to/official.pdf
python scripts/verify_criminal_codes.py
python scripts/verify_everyday_acts.py
```

**Add a correction to the Constitution:** add an entry to `backend/sources/constitution_patches.json` with `op`, `number`, `text`, `reason`, and what you verified it against. Rebuild.

**Fix an IPC defect:** add a `replacements` / `texts` / `insertions` entry to `backend/sources/ipc_patches.json` with a `reason`, only where the older copies agree. Rebuild, then re-run `verify_criminal_codes.py` (it fails if the unverified-sections list changes, so update `criminal_codes.json` to match).

**Add a new Act**

1. Put the PDF in `backend/data/raw/…` and pin it by sha256 in `ingestion/sources.py`.
2. Write an adapter in `ingestion/pdf_text.py` that returns `{section, chapter, text}` records (reuse `gazette_sections` if it is a Gazette print), with tests on a real excerpt.
3. Register it in `CRIMINAL_ACTS` or `EVERYDAY_ACTS` with its name, Status and **exact** expected count; load it in `load_criminal_codes` / `load_everyday_acts`.
4. Add alias spellings to `ACT_ALIASES` in `refs.py` so Queries can name it.
5. If it replaces an old Act, add a mapping-table parser and feed it to `apply_mappings`.
6. Add a verify script or check, rebuild, and add Queries to `backend/evaluation/golden_set.json`.

**Tests:** `cd backend && pytest`. Ingestion tests: `test_ingestion.py`, `test_criminal_ingestion.py`, `test_criminal_sources.py`, `test_everyday_ingestion.py`, the per-source adapter tests (`test_gazette_adapter.py`, `test_crpc_adapter.py`, `test_iea_adapter.py`, `test_ipc_kanoon_adapter.py`, `test_tpa_adapter.py`, `test_model_tenancy_adapter.py`, `test_everyday_gazette_adapter.py`), the mapping tests (`test_mapping_table.py`, `test_bns_table.py`, `test_bsa_table.py`), `test_record_patches.py`, `test_long_provisions.py` and `test_embeddings.py`. Their fixtures are in `backend/tests/fixtures/`.

---

## 10. File map

| Path | Role |
|---|---|
| `backend/src/legallens/build_corpus.py` | CLI entry point; `build()` orchestration; staging and swap |
| `backend/src/legallens/ingestion/sources.py` | Pinned dataset and PDF hashes; loaders for all Acts and mappings |
| `backend/src/legallens/ingestion/constitution.py` | Constitution parser, Part lookup, patch application |
| `backend/src/legallens/ingestion/criminal_codes.py` | `CRIMINAL_ACTS`, `parse_section_records`, `apply_mappings` |
| `backend/src/legallens/ingestion/everyday_acts.py` | `EVERYDAY_ACTS` |
| `backend/src/legallens/ingestion/pdf_text.py` | PDF text extraction and the per-source adapters |
| `backend/src/legallens/ingestion/mapping_tables.py` | NCRB corresponding-section table parsers |
| `backend/src/legallens/ingestion/record_patches.py` | Patch applier for section records (IPC) |
| `backend/src/legallens/ingestion/report.py` | Count ranges and build warnings |
| `backend/src/legallens/corpus.py` | Piece splitting, Chroma store, `get` / `search` / listing |
| `backend/src/legallens/embeddings.py` | `LocalEmbedder` (Qwen3-Embedding-0.6B) |
| `backend/src/legallens/refs.py` | Act aliases and reference formatting |
| `backend/sources/*.json` | Recorded patches, verification notes and accepted differences |
| `backend/data/raw/` | Source PDFs and dataset (gitignored) |
| `backend/data/chroma/` | Built Corpus (gitignored) |
| `backend/scripts/verify_*.py` | Independent checks of the built text |
| `backend/scripts/compare_embeddings.py` | Embedding-model comparison |
| `backend/scripts/deploy_space.py` | Packages the built Corpus for deployment |
| `backend/fixtures/sample_provisions.json` | 3-Provision sample used when no Corpus is built |
