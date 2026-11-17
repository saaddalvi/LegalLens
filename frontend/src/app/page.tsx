import { redirect } from "next/navigation";

// Temporary: the landing page replaces this redirect (ticket 06).
export default function Home() {
  redirect("/ask");
}
