'use client';

import { useState, useCallback } from 'react';
import { SymbolIcon } from '@radix-ui/react-icons';

interface ChatInputProps {
  value: string;
  sending: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
}

export function ChatInput({ value, sending, onChange, onSend }: ChatInputProps) {
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        onSend();
      }
    },
    [onSend]
  );

  return (
    <div className='sticky bottom-0 p-4 bg-white'>
      <div className='flex items-center border rounded-lg overflow-hidden shadow-sm min-h-12'>
        <textarea
          className='flex-grow p-3 text-gray-700 placeholder-gray-400 focus:outline-none resize-none max-h-32'
          placeholder='Message Explainable AI'
          value={value}
          disabled={sending}
          onKeyDown={handleKeyDown}
          onChange={(e) => onChange(e.target.value)}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = 'auto';
            target.style.height = `${target.scrollHeight}px`;
          }}
          rows={1}
        />

        <div className='button-container flex justif-between sm:mt-1'>
          <button
            onClick={onSend}
            className='p-3 hover:bg-gray-200'
            disabled={sending}
          >
            {sending ? (
              <SymbolIcon className='h-6 w-6 animate-spin text-gray-600' />
            ) : (
              <svg
                xmlns='http://www.w3.org/2000/svg'
                fill='none'
                viewBox='0 0 24 24'
                strokeWidth={1.5}
                stroke='currentColor'
                className='h-6 w-6 text-gray-600'
              >
                <path
                  strokeLinecap='round'
                  strokeLinejoin='round'
                  d='M15 11.25l-3-3m0 0l-3 3m3-3v7.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
                />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
