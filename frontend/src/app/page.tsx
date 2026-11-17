import { redirect } from "next/navigation";

// Temporary: the landing page replaces this redirect (ticket 06).
// The redirect depends on the request, so the route may block instead of
// prerendering an instant shell.
export const instant = false;

export default function Home() {
  redirect("/ask");
}
