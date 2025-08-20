'use client';

import { SymbolIcon } from '@radix-ui/react-icons';
import { Button } from '@/components/ui/button';

import { ChatInputProps } from './types';

export function ChatInput({
  input,
  setInput,
  handleSend,
  handleKeyDown,
  sendingMessage,
  validating,
  showValidateButton,
  handleValidate,
  onclick,
  setOnclick,
}: ChatInputProps) {
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const target = e.target;
    target.style.height = 'auto';
    target.style.height = `${target.scrollHeight}px`;
  };

  return (
    <div className='sticky bottom-0 p-4 bg-card'>
      <div className='flex items-center border rounded-lg overflow-hidden shadow-sm min-h-12 bg-background'>
        <textarea
          className='flex-grow p-3 text-foreground placeholder:text-muted-foreground focus:outline-none resize-none max-h-32'
          placeholder='Message Explainable AI'
          value={input}
          disabled={sendingMessage || validating}
          onKeyDown={handleKeyDown}
          onChange={handleTextareaChange}
          rows={1}
        />

        <div className='button-container flex justif-between sm:mt-1'>
          <button onClick={handleSend} className='p-3 hover:bg-muted' disabled={sendingMessage || validating}>
            {sendingMessage ? (
              <SymbolIcon className='h-6 w-6 animate-spin text-muted-foreground' />
            ) : (
              <svg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' strokeWidth={1.5} stroke='currentColor' className='h-6 w-6 text-muted-foreground'>
                <path strokeLinecap='round' strokeLinejoin='round' d='M15 11.25l-3-3m0 0l-3 3m3-3v7.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z' />
              </svg>
            )}
          </button>
        </div>
      </div>

      {showValidateButton && (
        <div className='flex gap-x-1.5 mt-1 ml-3'>
          <Button
            type='submit'
            size='sm'
            disabled={validating || !showValidateButton}
            onClick={() => {
              handleValidate();
              setOnclick(true);
              setTimeout(() => setOnclick(false), 500);
            }}
            className='ml-auto mb-2'
          >
            {!onclick && !validating ? (
              <svg width='20' height='20' viewBox='0 0 20 20' fill='none' xmlns='http://www.w3.org/2000/svg' className='h-4 w-4 mr-[5px]'>
                <circle cx='10' cy='10' r='9' stroke='currentColor' strokeWidth='1.8'></circle>
                <path d='M10 1c1.657 0 3 4.03 3 9s-1.343 9-3 9M10 19c-1.657 0-3-4.03-3-9s1.343-9 3-9M1 10h18' stroke='currentColor' strokeWidth='1.8'></path>
              </svg>
            ) : (
              <SymbolIcon className='mr-2 h-4 w-4 animate-spin' />
            )}
            <span className='leading-none mt-[-1px]'>Validate</span>
          </Button>
        </div>
      )}
    </div>
  );
}
