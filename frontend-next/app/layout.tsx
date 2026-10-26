import type { Metadata } from "next";
import Script from "next/script";
import {
  Geist,
  Geist_Mono,
  IBM_Plex_Mono,
  IBM_Plex_Sans,
  Instrument_Sans,
  Instrument_Serif,
  JetBrains_Mono,
  Oswald,
} from "next/font/google";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const instrumentSans = Instrument_Sans({ subsets: ["latin"], variable: "--font-instrument" });
const instrumentSerif = Instrument_Serif({ subsets: ["latin"], weight: "400", variable: "--font-instrument-serif" });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });
const oswald = Oswald({ subsets: ["latin"], variable: "--font-oswald" });

// Console typography: Plex Sans for UI text, Plex Mono for every number, ID and
// timestamp (both ship tabular figures). Loaded via next/font, no network link.
const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "EOC Command Dashboard",
  description: "Autonomous multi-agent disaster-response command dashboard",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="dark"
      className={`${geistSans.variable} ${geistMono.variable} ${instrumentSans.variable} ${instrumentSerif.variable} ${jetbrainsMono.variable} ${oswald.variable} ${plexSans.variable} ${plexMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* Apply the persisted theme before first paint so light-theme users
            don't get a dark flash on load (data-theme="dark" is the SSR
            default). */}
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem("theme");if(t)document.documentElement.setAttribute("data-theme",t);}catch(e){}`,
          }}
        />
      </head>
      {/* Normal document flow so the public landing page scrolls at the
          document level (its nav's scroll listener + sphere positioning depend
          on window scroll). The console shell fills the viewport via its own
          h-screen wrapper in (console)/layout.tsx, so it doesn't need the body
          to be a flex column. */}
      <body className="min-h-screen">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
