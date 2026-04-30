// app/layout.jsx
export const metadata = {
  title: "Orchaid — Grocery Supply Chain Intelligence",
  description: "Multi-Agent Intelligent Warehouse prototype for grocery distribution. Built on NVIDIA NIM, LangGraph, Google Cloud, and FDA OpenData.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0, background: "#070c15" }}>
        {children}
      </body>
    </html>
  );
}
