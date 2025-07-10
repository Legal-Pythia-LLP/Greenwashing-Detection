import '@lp/styles/globals.css';

import {Header} from '@lp/components/header';
import {HeaderVisibility} from '@lp/components/header-visibility';
import {WrapProviders} from './providers';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      <WrapProviders>
        <html lang='en'>
          <head>
            <title>Legal-Pythia | BMA</title>
            <meta name='viewport' content='width=device-width, initial-scale=1' />
          </head>

          <body className='min-h-screen bg-background font-sans antialiased'>
            <HeaderVisibility>
              <Header headerText='Legal-Pythia' description='BMA | Greenwashing' />
            </HeaderVisibility>

            <main className='grid center-content'>
              <div className='p-4'>{children}</div>
            </main>
          </body>
        </html>
      </WrapProviders>
    </>
  );
}
