---
name: LegalLens
description: Bare-act statute pages with violet stamp-pad ink marking only what has been checked against the Corpus.
colors:
  paper: "#fbfbf8"
  ledger: "#eceee8"
  ink: "#1f2330"
  muted: "#5c6170"
  rule: "#cdd0c7"
  stamp: "#5a3e9b"
  redtape: "#a3271f"
  warn: "#6b4300"
  warn-bg: "#fbf1d9"
  warn-border: "#d9a93d"
  paper-dark: "#1b1a2e"
  ledger-dark: "#25243b"
  ink-dark: "#e8e6f0"
  muted-dark: "#a6a3ba"
  rule-dark: "#3c3a55"
  stamp-dark: "#b7a3f2"
  redtape-dark: "#f08a80"
typography:
  display:
    fontFamily: "Anek Latin, Anek Devanagari, system-ui, sans-serif"
    fontSize: "4.5rem"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.005em"
  headline:
    fontFamily: "Anek Latin, Anek Devanagari, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.005em"
  body:
    fontFamily: "Anek Latin, Anek Devanagari, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  law:
    fontFamily: "Tiro Devanagari Hindi, Georgia, serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "Anek Latin, Anek Devanagari, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: "4px"
  row: "8px"
  tail: "6px"
  bubble: "24px"
  composer: "28px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "32px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "10px 24px"
  field:
    backgroundColor: "{colors.ledger}"
    textColor: "{colors.ink}"
    typography: "{typography.law}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
  stamp:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.stamp}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "3px 14px 2px"
  query-bubble:
    backgroundColor: "{colors.ledger}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.bubble}"
    padding: "10px 16px"
  composer:
    backgroundColor: "{colors.ledger}"
    textColor: "{colors.ink}"
    typography: "{typography.law}"
    rounded: "{rounded.composer}"
    padding: "6px 6px 6px 20px"
  button-send:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    size: "44px"
  button-send-disabled:
    backgroundColor: "{colors.rule}"
    textColor: "{colors.muted}"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.bubble}"
    padding: "8px 16px"
---

# Design System: LegalLens

## Overview

**Creative North Star: "The Stamp Pad"**

LegalLens reads like a page from a bare act: off-white paper, dark ink, a narrow marginal note beside each block of text, and the law itself set in a serif. The one saturated colour, stamp-pad violet, appears only where LegalLens has verified something against the Corpus. Red appears only for what is struck out (a repealed Provision) or has failed. Everything else is ink on paper.

The system is calm and document-like. The one app-like screen is a Contract's page, a chat that fills the window and uses the same inks and type. Interface text is a condensed-capable sans; statute text, Citations, Clause quotes and answers are in a serif so the reader always knows which words are the law's. Density is low and lines of running text are held to about 65 to 75 characters by the `measure` utility (54ch). Dark mode is "carbon paper": the same roles redefined on a deep indigo ground.

**Key Characteristics:**
- Paper and ink neutrals; violet is rare and meaningful.
- Sans for the interface, serif for the law.
- Condensed bold headings, after bare-act cover lettering.
- Flat surfaces, rules and borders instead of shadows.
- One orchestrated motion: the Trust label is stamped onto the answer.

## Colors

Cool paper, blue-black ink, one ink-pad violet, and one brick red.

### Primary
- **Stamp-Pad Violet** (#5a3e9b light, #b7a3f2 dark): marks what LegalLens has checked: the Trust stamp, the running Stage's finished dots, Citation links, the focus ring.

### Secondary
- **Red Tape** (#a3271f light, #f08a80 dark): struck-out repealed Provisions and failed Stages only.

### Neutral
- **Paper** (#fbfbf8 / #1b1a2e): page ground.
- **Ledger** (#eceee8 / #25243b): inset fields, quoted statute text, the Contract page's sidebar, the Query bubble and the composer.
- **Ink** (#1f2330 / #e8e6f0): text, primary buttons, heavy rules.
- **Muted Ink** (#5c6170 / #a6a3ba): secondary text and labels.
- **Rule** (#cdd0c7 / #3c3a55): hairline dividers and margin rules.
- **Caution Amber** (#6b4300 on #fbf1d9, border #d9a93d; dark #ffd98a on #33290f, border #7d6220): warnings, such as the not-legal-advice notice.

### Named Rules
**The Verified-Only Violet Rule.** Violet means "checked against the Corpus". It never decorates.
**The Struck-Out Red Rule.** Red marks only repealed or failed. Never use it for emphasis or errors of style.

## Typography

**Interface Font:** Anek Latin + Anek Devanagari (variable width axis), system-ui fallback
**Law Font:** Tiro Devanagari Hindi (Latin + Devanagari), Georgia fallback

**Character:** A modern Indic-aware sans carries the interface; a bookish serif carries everything that is law or quoted from it. Both cover Devanagari so English and Hindi sit together.

### Hierarchy
- **Display** (700, 3rem to 4.5rem, 1.02, font-stretch 78%): landing headline and the specimen's section number.
- **Headline** (700, 1.5rem, 1.02, condensed): section headings such as "Citations" and marginal notes.
- **Body** (400, 1rem, 1.5): interface copy, muted secondary at 1.125rem for lead text.
- **Law** (400, 1.125rem, 1.7, `measure`, serif): answers, quoted Provision and Clause text, the Query field and composer.
- **Label** (500, 0.875rem): stamps, captions, "Your Contract, Clause 4".

### Named Rules
**The Two Voices Rule.** Sans speaks for LegalLens; serif speaks for the law. Never set statute or Contract text in the sans.

## Layout

Single column inside a `max-w-6xl` container with 16px side gutters (32px from `sm`). The landing hero is a 7/5 grid at `lg`; screens stack on phones. The signature structure is the **margin grid**: a 10rem right-aligned heading column with a vertical rule beside the content, stacking with a bottom rule under 40rem. Rhythm uses 8, 12, 16 and 32px steps, with 48 to 80px between major sections.

A Contract's page is the exception: it fills the window (`100dvh`) and the document itself does not scroll. A compact site header sits over two columns. On the left, from `lg`, an 18rem ledger sidebar lists the conversations; below `lg` it is a drawer. On the right are the title bar with its tabs and, under it, one part at a time, each scrolling on its own with a thin rule-coloured scrollbar. Messages, composer, Contract brief and Clauses share a centred 42rem column. The composer stays at the foot of the chat.

## Elevation & Depth

Flat. Depth comes from tonal ledger insets, hairline rules, and 2px ink borders (the specimen's top rule, the field's bottom border). The open drawer is set off by a flat scrim over the page (ink at 40% in light, paper at 70% in dark). No shadows exist.

### Named Rules
**The No-Shadow Rule.** Surfaces are paper, ledger or ruled. Do not add box-shadows or blur.

## Shapes

Mostly square and ruled. Buttons and fields use a small 4px radius (the field rounds only its top corners over a heavy bottom border). Quotes and cards are marked by a 2px left border instead of a box. The stamp is the one oval with a double outline, like an ink impression.

The Contract chat has its own softer shapes: the Query bubble (24px, its lower right corner 6px), the composer (28px), chips (24px), conversation rows (8px), and round (999px) send and "New conversation" buttons.

### Named Rules
**The Chat-Only Curve Rule.** Rounded bubbles, chips and the pill composer belong to the Contract chat. Elsewhere, buttons and fields keep the 4px radius. Buttons that confirm or retry keep it inside the chat too.

## Components

### Buttons
- **Shape:** 4px radius.
- **Primary:** ink fill, paper text, 10px 24px, semibold; 50% opacity when disabled.
- **Secondary / link:** underlined text with `underline-offset-4`; muted, darkening to ink on hover.

### Inputs / Fields
- **Style:** ledger fill, 2px ink bottom border, serif 1.125rem text, muted placeholder.
- **Focus:** 2px violet outline, no offset.

### Navigation
- Header: condensed wordmark on the left, small underlined links, account control and theme toggle on the right, closed by a hairline rule. On a Contract's page it is one shallow full-width row, and on phones its links move into the drawer.
- Tabs (Chat, Brief, Contract): plain text in the title bar, muted until chosen; the chosen one is ink, semibold, with a 2px ink line on the bar's rule. Arrow, Home and End keys move between them.
- Conversation sidebar: ledger ground, a "Your Contracts" link, an outlined pill "New conversation" button that fills with ink on hover, then titles clamped to two lines. The open conversation sits on paper in semibold. Delete is an icon that a mouse reveals on hover or focus and touch always shows; its confirmation opens inside the row.
- Drawer: below `lg` the sidebar slides over the page from a menu button, closes on Escape, the scrim or a choice, and makes the page behind it inert.

### Chat
- **Query bubble:** the user's own words on the right, ledger fill, sans, at most 85% of the column, line breaks kept.
- **Answer:** on the left with no bubble or box: Trust stamp, serif text, disclaimer, then the actions.
- **Composer:** ledger pill with a 1px muted border that turns ink on focus; the whole pill carries the 2px violet focus outline. The textarea is serif, grows to 10rem, then scrolls. The send button is a round ink arrow, rule-coloured while the box is empty; while an answer is being written it reads "Ask this instead".
- **Chips:** starter questions and the "Sources" button, outlined in rule, ink border on hover. "Sources" counts what an answer rests on, turns its chevron when open, and states a repealed count in Red Tape.
- **Empty conversation:** a condensed question as its title, one muted line, the starter chips, then links to the Contract brief and in Hindi.

### Trust stamp (signature)
- Oval with a 2px border plus a 1px outline offset 2px, in violet. Variants: dashed border for corpus plus web, muted dashed for web only, muted single hairline for none. A larger version (3px border) appears in the hero specimen. It is pressed onto the answer with a 220ms scale-in.

### Clause quote and Citation card
- Left 2px rule, a small label above, quoted text in serif; Citation quotes sit on a ledger inset. Repealed Provisions are struck through with a 2px red line.

### Stage list
- Vertical hairline with 9px dots: violet when done, pulsing ink when running, red on failure; labels carry screen-reader status text.

## Do's and Don'ts

### Do:
- **Do** reserve violet for verified content and red for repealed or failed.
- **Do** set law and quotes in the serif at no more than the `measure`, with `lang="en"` on English statute text.
- **Do** keep every theme token defined for light and dark; honour `prefers-color-scheme` and the saved toggle.
- **Do** respect `prefers-reduced-motion` for every animation.
- **Do** use the glossary terms in copy (Provision, Clause, Citation, Flagged clause).
- **Do** keep every answer's sources one press away, and show that a Citation is repealed while they are folded.

### Don't:
- **Don't** use shadows, gradients or glass effects.
- **Don't** use red or violet as general emphasis or decoration.
- **Don't** set statute or Contract text in the sans.
- **Don't** word Flagged clauses as "risky" or "red flag", or imply whether to sign.
- **Don't** put an answer in a bubble; only the user's Query has one.
