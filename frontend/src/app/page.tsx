import type { Metadata } from "next";
import LandingPage from "./landing-page";

export const metadata: Metadata = {
  title: "LegalLens: plain-language answers about Indian law",
  description:
    "Ask about Indian law in English or Hindi. Answers are grounded in statute text, with every Citation verified against it.",
};

export default function Home() {
  return <LandingPage />;
}
