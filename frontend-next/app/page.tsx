import { redirect } from "next/navigation";

// Temporary until plan Phase N builds the real public landing page --
// / just forwards into the console shell for now, same as before but at
// its new address.
export default function Home() {
  redirect("/command");
}
