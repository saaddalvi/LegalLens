# Frontend redesign: landing page, Stage streaming and answer reveal

Status: ready-for-agent

## Problem Statement

LegalLens works, but it does not look like a product a layperson would trust or return to. The whole interface is a disclaimer, a text box and an Ask button. A first-time visitor gets no explanation of what LegalLens is, what Acts it covers, why its Citations can be trusted, or what the Trust labels mean. After asking, the user stares at "Thinking…" for the full length of the Corrective RAG pipeline (several Gemini calls, sometimes a web search), with no sign of progress. Then the whole answer appears at once. Users cannot tell whether anything is happening, and the long wait feels longer than it is. LegalLens's main differentiator is that every Citation is checked against the Corpus before it is shown, but it is invisible: the user never sees that checking happen.

## Solution

LegalLens gets a landing page and a redesigned asking screen in an editorial, reference-book style: a warm paper background, ink-blue text, a restrained saffron accent, serif headings and Citations styled as quoted statute text, with a full dark mode.

The landing page at the site root explains what LegalLens is, how it answers, which Acts the Corpus covers, and what the Trust labels mean. It also offers English and Hindi example Queries that start an answer with one click.

The asking screen moves to its own route and shows one Query at a time. While the Query is answered, the user sees the Stages the pipeline actually goes through, written in plain language and in the Query's language: checking the question, searching the statutes, checking whether they answer it, searching the web when the statutes do not fully cover it, writing the answer, and verifying Citations against the Corpus. When the verified answer arrives, it reveals smoothly in a short, capped animation, then the Trust label and Citations fade in. No unverified answer text is ever shown, so the guarantee that Hallucinated citations are blocked holds exactly as before. If a Stage fails, the user sees which one, a friendly message and a one-click Try again.

## User Stories

1. As a first-time visitor, I want a landing page that explains in one sentence what LegalLens does, so that I know at once whether it can help me.
2. As a first-time visitor, I want to see that answers are grounded in Indian statute text with verifiable Citations, so that I understand why LegalLens is more trustworthy than a generic chatbot.
3. As a first-time visitor, I want a short "how it works" explanation (I ask, it is checked against the statutes, I get an answer with Citations I can read), so that I understand the process without technical terms.
4. As a first-time visitor, I want to see which Acts the Corpus covers, listed by name, so that I know whether my topic is covered before I ask.
5. As a visitor with an old IPC section number, I want the landing page to tell me that repealed criminal-code Provisions are linked to their Superseding provisions, so that I know I can ask about them.
6. As a first-time visitor, I want the Trust labels explained ("From statute text" against "From web sources"), so that I understand the label when I see it on an answer.
7. As a visitor, I want to see the not-legal-advice disclaimer on the landing page, so that I understand LegalLens's limits before I rely on it.
8. As a visitor, I want an ask box directly on the landing page, so that I can ask without first navigating elsewhere.
9. As a visitor, I want clickable example Queries in English, so that I can try LegalLens without thinking of a question.
10. As a Hindi speaker, I want clickable example Queries in Hindi on the landing page, so that I can see that LegalLens answers in Hindi.
11. As a visitor, I want clicking an example Query to take me to the asking screen and start answering it at once, so that I do not have to press Ask again.
12. As a visitor, I want submitting the landing page's ask box to take me to the asking screen and start answering, so that asking feels like one action.
13. As a returning user, I want to go straight to the asking screen, so that I do not scroll past marketing content every time.
14. As a user, I want the asking screen to show one Query and its answer at a time, so that I am not led to believe LegalLens remembers my earlier questions.
15. As a user, I want my Query kept in the page address, so that I can bookmark or share a question and its answer reloads.
16. As a user, I want the browser back button to return me to my previous Query, so that navigation works as I expect.
17. As a user waiting for an answer, I want to see each Stage of the work as it happens, so that I know LegalLens is making progress.
18. As a user waiting for an answer, I want the Stage that is running to be visibly active and the finished ones marked done, so that I can tell how far along it is.
19. As a user whose Query the statutes do not fully cover, I want to see a Stage saying LegalLens is searching the web, so that the lower-trust label on the answer does not surprise me.
20. As a user, I want to see a Stage where LegalLens verifies Citations against the Corpus, so that I can see the check that makes its Citations trustworthy.
21. As a user whose answer needed a second try because a Citation could not be verified, I want a Stage telling me LegalLens is rechecking, so that a longer wait is explained.
22. As a user, I never want to see answer text that was later withdrawn, so that I am never misled by an unverified Citation.
23. As a user, I want Stages described in plain language, never as internal terms like "Verdict: ambiguous", so that I understand them without knowing how the system works.
24. As a Hindi speaker, I want the Stages shown in Hindi when I ask in Hindi, so that my whole wait and answer are in my language.
25. As a user asking an Out-of-scope query, I want the Stages to stop after the question check and the refusal to appear, so that I quickly learn LegalLens cannot help with it.
26. As a user, I want the answer text to reveal smoothly once it is ready, so that the result feels responsive rather than dumped on the screen.
27. As a user with a long answer, I want the reveal to finish within about a second and a half, so that I am not made to wait a second time.
28. As a user, I want to click the answer to show it all at once, so that I can skip the animation.
29. As a user who has set the operating system to reduce motion, I want the answer to appear at once without animation, so that the interface respects my accessibility settings.
30. As a user, I want the Trust label and Citations to appear after the answer text, so that I read the answer first and then its support.
31. As a user, I want Citations styled as quoted statute excerpts, so that it is visually clear I am reading the law itself.
32. As a user, I still want Citations to expand and collapse, so that the answer stays readable while the full Provision text stays available.
33. As a user, I still want repealed Provisions flagged with their Superseding provision, and model-Act Provisions flagged as not in force by themselves, so that the redesign loses none of the existing warnings.
34. As a user of a Fallback-sourced answer, I still want the web sources listed, so that I can judge them.
35. As a user whose question failed partway (for example the service is briefly unavailable), I want to see which Stage failed and a friendly message, so that I understand what happened.
36. As a user whose question failed, I want a Try again button that resubmits the same Query, so that I do not have to retype it.
37. As a user who cannot reach the service at all, I want the existing friendly network message, so that I know to check my connection.
38. As a user with a dark-mode device, I want LegalLens to use a dark theme, so that it is comfortable to read at night.
39. As a user on a phone, I want both pages to work at phone width with no horizontal scrolling, so that I can use LegalLens anywhere.
40. As a user of the asking screen, I want the not-legal-advice disclaimer always visible, so that I never mistake an answer for legal advice.
41. As a Hindi reader, I want Hindi text rendered in a proper Devanagari font, so that answers and Stages are easy to read.
42. As a keyboard or screen-reader user, I want Stage progress announced politely and every control reachable by keyboard, so that the redesign does not reduce accessibility.
43. As the maintainer, I want the existing `/ask` endpoint unchanged, so that the evaluation harness and its results stay valid.
44. As the maintainer, I want the streamed final answer to be exactly what `/ask` would have returned, so that there is one source of truth for answers.

## Implementation Decisions

- **Two endpoints, one pipeline.** A new `POST /ask/stream` endpoint takes the same request body as `/ask` and returns Server-Sent Events. `/ask` is unchanged. Both call the same pipeline function. It gains an optional progress callback that is told when each Stage starts. `/ask` passes no callback, so its behaviour and the evaluation harness are untouched.
- **Event contract for `/ask/stream`.** Three event types:
  - `stage`: `{ id, label }`, sent when a Stage starts. `id` is a stable identifier from a fixed set: `scope_check`, `retrieval`, `grading`, `fallback`, `generation`, `citation_check`, `citation_recheck`. `label` is the plain-language text in the Query's language.
  - `answer`: the full `AskResponse` payload, sent once at the end. It is identical to what `/ask` returns for the same Query and dependencies.
  - `error`: `{ stage, message }`, sent if the pipeline raises. `stage` is the id of the Stage that was running. The stream then ends. The `message` matches the existing 503 wording.
- **Stages reflect the real path.** Every Query emits `scope_check`. An Out-of-scope query stops there and goes straight to `answer` with the refusal. In-scope Queries emit `retrieval` and `grading`. `fallback` is emitted only when the Verdict is ambiguous or incorrect. `generation` is emitted for each generation. `citation_check` is emitted when Citations are verified. `citation_recheck` is emitted only when the first generation had a Hallucinated citation and the pipeline regenerates. Raw Verdict words never appear in labels.
- **Stage labels are bilingual.** Language detection runs first and is local, so every Stage label is in the Query's language (English or Hindi), from a fixed table of strings kept beside the pipeline's other bilingual messages.
- **No unverified text is streamed.** Gemini tokens are not streamed. Answer text reaches the client only inside the final `answer` event, after the Citation check. The Hallucinated-citation guarantee is unchanged.
- **Routes.** The site root becomes the landing page. The asking screen moves to `/ask`. The `/ask` route reads the `q` search parameter on the server and passes it to the client asking component as an `initialQuery` prop. When it is present, the component submits it at once. Submitting a new Query updates `q` in the address with a history entry, so back and forward move between Queries.
- **One Query at a time.** The asking screen shows one Query and its answer. A new submission replaces the previous answer and cancels any in-flight stream. There is no chat thread and no stored history.
- **Client stream reading.** The asking component posts to `/ask/stream` with `fetch` and reads the response body as a stream, parsing SSE frames. `EventSource` is not used because it cannot POST. HTTP errors returned before the stream starts (422, 429, 5xx) keep the existing friendly messages.
- **Reveal behaviour.** Once the `answer` event arrives, the answer text reveals word by word with a fade. The per-word delay is chosen so the whole reveal finishes in about 1.5 seconds whatever the answer's length. The Trust label, Citations and web sources fade in after the text. Clicking the answer, or `prefers-reduced-motion: reduce`, shows everything at once. Refusals and "cannot answer" messages use the same reveal.
- **Failure display.** On an `error` event, or if the stream drops mid-way, the running Stage is marked failed, the existing friendly error message is shown, and a Try again button resubmits the same Query.
- **Answer formatting stays plain text.** Answers are rendered as well-spaced paragraphs in a readable serif. The generation prompt is not changed and no Markdown renderer is added.
- **Design system.** Colours are defined as tokens in the global stylesheet: paper background, ink-blue foreground and primary, saffron accent, plus surface, border, muted and the existing red and amber warning tones. Every token is redefined for dark mode under `prefers-color-scheme: dark`. A serif display face (for example Fraunces or Source Serif, via `next/font`) is added for headings and statute quotes. Geist stays the body font and Noto Sans Devanagari stays the Hindi fallback. Components use the tokens instead of hard-coded zinc, red and amber colours, so both themes work.
- **Motion.** All motion uses CSS (Tailwind utilities and a few keyframes). No animation library is added.
- **Landing page sections.**
  1. A hero: a headline and subheading, the ask box, and example Queries in English and Hindi. The examples link to `/ask?q=…` and the ask box submits to `/ask?q=…`.
  2. How it works, in three steps: you ask, it is checked against the statute text, you get an answer with Citations you can read.
  3. What the Corpus covers: the Acts listed by name, with a note that repealed IPC, CrPC and IEA Provisions point to their BNS, BNSS and BSA replacements.
  4. Trust labels explained, using the same wording as the labels on answers.
  5. The disclaimer and a footer.
  
  The landing page shows no evaluation figures. The example Queries are taken from the golden set's cases that CRAG answers well.
- **Disclaimer.** The not-legal-advice disclaimer stays visible on both pages.
- **Accessibility.** The Stage list is a polite live region. The active Stage is conveyed by text as well as styling. Every control is keyboard reachable with visible focus. `lang` attributes stay on Hindi answer text and Stage labels.
- **Glossary.** "Stage" was added to the glossary for this work. Code and UI copy use "Stage" for these steps and avoid "status", which means a Provision's in-force state.

## Testing Decisions

- **What makes a good test here.** Tests exercise external behaviour only: HTTP responses and events on the backend, and what a user sees and can do on the frontend. They do not assert on internal function calls, the callback mechanism, CSS class names or animation timings, except for the single reveal-cap test.
- **Backend seam: the HTTP app.** Tests build the app with `create_app(corpus=…, llm=…, fallback=…)` and the existing fakes (the bag-of-words fake embedder, the fake LLM with a configurable Grader score, the recording Fallback), then call `/ask/stream` through `TestClient` and parse the SSE events. Prior art: the existing endpoint tests for CRAG, Hindi, scope, repeal handling and asking.
  - Stage sequence for each path:
    - correct Verdict: no `fallback` Stage
    - ambiguous Verdict: `fallback` present
    - incorrect Verdict: `fallback` present
    - failed Fallback
    - Hallucinated citation on the first generation, then a valid one: `citation_recheck` present
    - Hallucinated citation on both generations: blocked "cannot answer"
    - Out-of-scope query: only `scope_check`, then `answer`
  - A Hindi Query produces Hindi Stage labels.
  - For each path, the final `answer` event's payload equals the `/ask` response body for the same Query and fakes.
  - An exception in the LLM produces an `error` event naming the Stage that was running, and the stream ends.
  - The existing `/ask` tests keep passing unchanged.
- **Frontend seam: render the page component with `fetch` stubbed.** Prior art: the existing page component tests with Testing Library, `user-event` and `fetch` stubbed via `vi.stubGlobal`. The `fetch` stub is extended to return a `Response` whose body is a stream of SSE text, so tests can control the timing of events.
  - The asking component, rendered with and without `initialQuery`:
    - Stages appear in order, with the active one marked
    - the answer, Trust label and Citations render after the `answer` event
    - a model-Act Citation and a repealed Citation still show their warnings
    - Citations expand and collapse
    - Fallback sources are listed
    - an `error` event marks the Stage failed and Try again resubmits the same Query
    - pre-stream HTTP errors (429, 5xx, network failure) show the existing messages
    - the disclaimer is visible
  - Tests run with reduced motion stubbed, so the reveal is instant. One test uses fake timers to check that a long answer is fully revealed within the cap.
  - The landing page:
    - the disclaimer is present
    - English and Hindi example Queries link to `/ask?q=…` with the Query encoded
    - the ask box submits to `/ask?q=…`
    - the covered Acts are listed
    - the Trust label explanations are present
- **Not tested automatically:** visual design, dark-mode colours, and phone-width layout. These are checked by hand in a browser, at phone width and in both colour schemes, before the work is closed.

## Out of Scope

- Streaming Gemini tokens directly, or showing any answer text before the Citation check.
- Asking Gemini for Markdown-formatted answers. That changes the generation prompt and would require rerunning the evaluation.
- Linking Provision mentions in the answer text (for example "BNS 103") to their Citation cards. This becomes a follow-up ticket.
- A chat thread, follow-up Queries that use earlier turns, or stored Query history.
- Translating the interface (landing page copy, buttons, headings) into Hindi. Only answers and Stage labels follow the Query's language.
- Rate limiting and deployment (ticket 12 of LegalLens v1).
- Any change to retrieval, grading, the Fallback, the Corpus or the evaluation.

## Further Notes

- The latest evaluation run hit three Gemini 503 errors in 72 runs, so mid-stream failures will happen in real use. The Try again path is a core part of this work, not an edge case.
- When rate limiting (v1 ticket 12) lands, a 429 on `/ask/stream` is returned before the stream starts, so the existing pre-stream error handling covers it.
- CORS already allows the frontend origin for all methods. SSE over a POST response needs no extra configuration. Proxies in front of a deployed backend may need buffering disabled for the stream (for example an `X-Accel-Buffering: no` header). Ticket 12's deployment work should take this into account.
