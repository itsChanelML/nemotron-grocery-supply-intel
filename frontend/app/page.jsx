// app/page.jsx
"use client";
// The CommandCenter is a fully client-side component.
// Agent chat calls go through /api/chat (server-side) to protect API keys.
// Telemetry and FDA data are fetched from /api/telemetry and /api/fda.

import CommandCenter from "../components/CommandCenter";

export default function Home() {
  return <CommandCenter />;
}
