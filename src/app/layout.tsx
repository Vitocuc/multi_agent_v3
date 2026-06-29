import type { Metadata } from 'next';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'Protego Life Simulator',
  description: 'Simulatore di finanza comportamentale per allenare la disciplina finanziaria',
  manifest: '/manifest.json',
  themeColor: '#1A365D',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Protego',
  },
  icons: {
    icon: '/icons/icon-192x192.png',
    apple: '/icons/apple-touch-icon.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="it">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
