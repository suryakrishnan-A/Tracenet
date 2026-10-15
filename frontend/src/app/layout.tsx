import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TraceNest — Application Failure Investigation Platform',
  description: 'Understand and resolve software incidents through error grouping, timeline reconstruction, and AI-assisted investigation.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090d16] text-slate-100 antialiased bg-grid-pattern selection:bg-blue-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
