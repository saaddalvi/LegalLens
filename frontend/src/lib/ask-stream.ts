// What /ask and a Contract conversation share when they stream an answer.
import { waitText } from "./daily-cap";

// The language the backend will detect for a Query, so Stage labels can be marked up with it.
export function detectedLang(q: string): string {
  const letters = [...q].filter((c) => /\p{L}/u.test(c));
  const deva = letters.filter((c) => /[\u0900-\u097F]/.test(c)).length;
  return deva * 2 > letters.length ? "hi" : "en";
}

// `retryAfter` is the seconds a 429 says to wait.
export function errorMessage(status: number | null, retryAfter: number | null = null): string {
  if (status === null)
    return "We could not reach the LegalLens service. Check your connection and try again.";
  if (status === 401)
    return "Your session has expired. Please sign in again, then ask your question.";
  if (status === 429 && retryAfter !== null && retryAfter > 60)
    return `You have asked too many questions. Please try again in ${waitText(retryAfter)}.`;
  if (status === 429)
    return "You have asked too many questions in a short time. Please wait a minute and try again.";
  if (status === 503 || status >= 500)
    return "The service is unavailable right now. Please try again shortly.";
  if (status === 422)
    return "That question could not be processed. Please check it and try again.";
  return "Something went wrong. Please try again.";
}
