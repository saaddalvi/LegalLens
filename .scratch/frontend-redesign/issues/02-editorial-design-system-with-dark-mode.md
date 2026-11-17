# 02: Editorial design system with dark mode, applied to `/ask`

**What to build:** LegalLens gets its editorial, reference-book look (see `../spec.md`, "Design system"), and the existing `/ask` screen is restyled with it. Colours are tokens: paper background, ink-blue foreground and primary, saffron accent, surface, border, muted, and the red and amber warning tones. Each token is redefined for dark mode, so the screen follows the device's colour scheme. A serif display face is added for headings and statute quotes. Geist stays the body font and Noto Sans Devanagari the Hindi fallback. Citation cards read as quoted statute excerpts. The plain-text answer is laid out as well-spaced paragraphs in a readable serif. Behaviour does not change. Later tickets build their new components with these tokens.

**Blocked by:** 01 (Move the asking screen to `/ask`)

**Status:** done

- [x] Colour tokens are defined once and redefined for `prefers-color-scheme: dark`. Components use tokens instead of hard-coded zinc, red or amber colours
- [x] A serif display face is loaded and used for headings and Citation quotes. Hindi text still renders in Noto Sans Devanagari
- [x] Citation cards are styled as quoted statute excerpts and still expand and collapse. The repealed and model-Act warnings keep distinct, legible styling in both themes
- [x] The answer text is rendered as well-spaced paragraphs. The generation prompt is unchanged and no Markdown renderer is added
- [x] The disclaimer stays prominent
- [x] Keyboard focus is visible on every control in both themes
- [x] The existing component tests pass unchanged
- [x] Manual check in a browser: `/ask` with an answer, a Fallback answer, a repealed Citation, a model-Act Citation and a refusal looks right in light and dark mode and at phone width with no horizontal scrolling
- [x] Lint, typecheck and tests pass
