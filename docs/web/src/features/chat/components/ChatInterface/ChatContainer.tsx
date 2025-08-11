'use client';

import { useRef } from 'react';
import { Sidebar } from '@lp/components/ui/sidebar';
import { ChatMessage } from './ChatMessage';
import { ChatMessage as MessageType } from './types';

interface ChatContainerProps {
  messages: MessageType[];
  currentMessage: string | null;
  graphData: string;
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  chatContainerRef: React.RefObject<HTMLDivElement>;
}

export function ChatContainer({
  messages,
  currentMessage,
  graphData,
  sidebarOpen,
  setSidebarOpen,
  chatContainerRef
}: ChatContainerProps) {
  return (
    <div className='flex'>
      <div className={`z-30`}>
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onOpen={() => setSidebarOpen(true)}
          message={graphData}
        />
      </div>

      <div
        className={`fixed inset-0 bg-white flex items-center justify-center transition-transform duration-300 ${
          sidebarOpen ? 'translate-x-60' : ''
        }`}
      >
        <div className='w-full max-w-4xl h-[97vh] flex flex-col bg-white rounded-lg border shadow-sm overflow-hidden'>
          <div className='sticky top-0 z-10 bg-white p-4 '>
            <h1 className='text-center font-semibold text-xl'>Explainable AI</h1>
          </div>

          <div ref={chatContainerRef} className='flex-1 overflow-y-auto p-4 space-y-4'>
            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}

            {currentMessage && (
              <ChatMessage 
                message={{ role: 'system', content: currentMessage }} 
                isCurrent={true}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
