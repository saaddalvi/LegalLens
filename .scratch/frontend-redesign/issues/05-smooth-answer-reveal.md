# 05: Smooth answer reveal

**What to build:** Once the verified answer arrives, it reveals smoothly instead of appearing all at once (see `../spec.md`, "Reveal behaviour"). The answer text fades in word by word, with the per-word delay chosen so the whole reveal finishes in about 1.5 seconds whatever the answer's length. The Trust label, Citations and web sources then fade in. Refusals and "cannot answer" messages use the same reveal. Clicking the answer, or `prefers-reduced-motion: reduce`, shows everything at once. Motion uses CSS only, with no animation library. Screen readers get the full answer text, not word fragments.

**Blocked by:** 03 (Stage streaming end to end)

**Status:** done

- [x] With reduced motion set, the answer, Trust label and Citations appear at once (the existing component tests run in this mode)
- [x] Component test with fake timers: a long answer is fully revealed within the cap, and the Trust label and Citations appear only after the text
- [x] Component test: clicking the answer during the reveal shows the full answer, Trust label and Citations at once
- [x] Refusals and "cannot answer" messages reveal the same way
- [x] Hindi answers reveal correctly, with words not broken mid-grapheme
- [x] Screen readers announce the complete answer once, not word by word
- [ ] Manual check in a browser: the reveal looks smooth for a short English answer and a long Hindi answer, in both themes
- [x] Lint, typecheck and tests pass
