import type { Metadata } from "next";
import { Anek_Devanagari, Anek_Latin, Tiro_Devanagari_Hindi } from "next/font/google";
import "./globals.css";

// The interface: Anek, with its width axis for condensed headings.
const anekLatin = Anek_Latin({
  variable: "--font-anek-latin",
  subsets: ["latin"],
  axes: ["wdth"],
});

const anekDevanagari = Anek_Devanagari({
  variable: "--font-anek-devanagari",
  subsets: ["devanagari"],
  axes: ["wdth"],
});

// The law: answers, statute text and Citations, in English and Hindi alike.
const tiro = Tiro_Devanagari_Hindi({
  variable: "--font-tiro",
  subsets: ["latin", "devanagari"],
  weight: "400",
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "LegalLens",
  description: "Plain-language answers about Indian law, with verifiable citations.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${anekLatin.variable} ${anekDevanagari.variable} ${tiro.variable} h-full antialiased`}
    >
      <head>
        {/* Applies a saved theme before first paint, so there is no flash. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
