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
---

# Design System: LegalLens

## Overview

**Creative North Star: "The Stamp Pad"**

LegalLens reads like a page from a bare act: off-white paper, dark ink, a narrow marginal note beside each block of text, and the law itself set in a serif. The one saturated colour, stamp-pad violet, appears only where LegalLens has verified something against the Corpus. Red appears only for what is struck out (a repealed Provision) or has failed. Everything else is ink on paper.

The system is calm and document-like, not app-like. Interface text is a condensed-capable sans; statute text, Citations, Clause quotes and answers are in a serif so the reader always knows which words are the law's. Density is low and lines of running text are held to about 65 to 75 characters by the `measure` utility (54ch). Dark mode is "carbon paper": the same roles redefined on a deep indigo ground.

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
- **Ledger** (#eceee8 / #25243b): inset fields and quoted statute text.
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
- **Law** (400, 1.125rem, 1.7, `measure`, serif): answers, quoted Provision and Clause text, the Query field.
- **Label** (500, 0.875rem): stamps, captions, "Your Contract, Clause 4".

### Named Rules
**The Two Voices Rule.** Sans speaks for LegalLens; serif speaks for the law. Never set statute or Contract text in the sans.

## Layout

Single column inside a `max-w-6xl` container with 16px side gutters (32px from `sm`). The landing hero is a 7/5 grid at `lg`; screens stack on phones. The signature structure is the **margin grid**: a 10rem right-aligned heading column with a vertical rule beside the content, stacking with a bottom rule under 40rem. Rhythm uses 8, 12, 16 and 32px steps, with 48 to 80px between major sections.

## Elevation & Depth

Flat. Depth comes from tonal ledger insets, hairline rules, and 2px ink borders (the specimen's top rule, the field's bottom border). No shadows exist.

### Named Rules
**The No-Shadow Rule.** Surfaces are paper, ledger or ruled. Do not add box-shadows or blur.

## Shapes

Mostly square and ruled. Buttons and fields use a small 4px radius (the field rounds only its top corners over a heavy bottom border). Quotes and cards are marked by a 2px left border instead of a box. The only fully round shape is the stamp oval (999px) with a double outline, like an ink impression.

## Components

### Buttons
- **Shape:** 4px radius.
- **Primary:** ink fill, paper text, 10px 24px, semibold; 50% opacity when disabled.
- **Secondary / link:** underlined text with `underline-offset-4`; muted, darkening to ink on hover.

### Inputs / Fields
- **Style:** ledger fill, 2px ink bottom border, serif 1.125rem text, muted placeholder.
- **Focus:** 2px violet outline, no offset.

### Navigation
- Header: condensed wordmark on the left, small underlined links, account control and theme toggle on the right, closed by a hairline rule.

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

### Don't:
- **Don't** use shadows, gradients or glass effects.
- **Don't** use red or violet as general emphasis or decoration.
- **Don't** set statute or Contract text in the sans.
- **Don't** word Flagged clauses as "risky" or "red flag", or imply whether to sign.
