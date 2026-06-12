import type { Metadata } from 'next';
import { Inter, Noto_Sans_Bengali } from 'next/font/google';
import Providers from '@/components/providers';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const notoBengali = Noto_Sans_Bengali({
  subsets: ['bengali'],
  variable: '--font-noto-bn',
  weight: ['400', '500', '600', '700'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'হ্যালো এ্যাডভকেট',
  description:
    'আপনার আইনি অধিকার আদায়ের প্রথম সোপান। AI-powered Bangladesh law assistant.',
  keywords: ['Bangladesh law', 'legal AI', 'বাংলাদেশ আইন', 'আইনি সহায়তা', 'হ্যালো এ্যাডভকেট'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="bn" className={`${inter.variable} ${notoBengali.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
