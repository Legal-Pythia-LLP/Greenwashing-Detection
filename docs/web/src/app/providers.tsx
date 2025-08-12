'use client';

import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HeaderProvider } from '@lp/components/header-context';

export const ReactQueryClientProvider = ({ children }: Readonly<{ children: React.ReactNode }>) => {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // With SSR, we usually want to set some default staleTime
            // above 0 to avoid refetching immediately on the client
            staleTime: 60 * 1000,
          },
        },
      })
  );
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
};

export function WrapProviders({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <HeaderProvider>
      <ReactQueryClientProvider>
        {children}
      </ReactQueryClientProvider>
    </HeaderProvider>
  );
  
}
