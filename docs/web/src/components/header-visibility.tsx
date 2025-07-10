'use client';

import { ReactNode } from 'react';
import { useHeader } from './header-context';

export function HeaderVisibility({ children }: { children: ReactNode }) {
  const { showHeader } = useHeader();
  
  if (!showHeader) return null;
  
  return <>{children}</>;
}