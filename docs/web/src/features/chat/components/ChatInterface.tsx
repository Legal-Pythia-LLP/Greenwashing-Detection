'use client';

import {useState, useEffect, useRef, useCallback} from 'react';
import ReactMarkdown from 'react-markdown';
import {ExclamationTriangleIcon, SymbolIcon} from '@radix-ui/react-icons';
import {Button} from '@lp/components/ui/button';
import {Alert, AlertDescription, AlertTitle} from '@lp/components/ui/alert';
import {Sidebar} from '@lp/components/ui/sidebar';
import {APIService} from '@lp/services/api.service';

const SCROLL_BEHAVIOUR = {
  user: {
    type: 'smooth' as const,
    position: 'end' as const,
  },
  bot: {
    type: 'smooth' as const,
    position: 'start' as const,
  },
};

interface ChatInterfaceProps {
  sessionId: string;
  initialMessages?: {role: string; content: string}[];
  graphData?: string;
  companyName?: string;
  onHeaderVisibility?: (show: boolean) => void;
}

export function ChatInterface({
  sessionId,
  initialMessages = [],
  graphData = '',
  companyName = '',
  onHeaderVisibility
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<{role: string; content: string}[]>(initialMessages);
  const [input, setInput] = useState('');
  const [currentMessage, setCurrentMessage] = useState<string | null>(null);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatContainerRef.current && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      const container = chatContainerRef.current;

      if (lastMessage.role === 'user') {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: SCROLL_BEHAVIOUR.user.type,
        });
      } else {
        const lastBot = container.querySelector('[data-role="system"]:last-child');
        if (lastBot) {
          lastBot.scrollIntoView({
            behavior: SCROLL_BEHAVIOUR.bot.type,
            block: SCROLL_BEHAVIOUR.bot.position,
          });
        }
      }
    }
  }, [messages, currentMessage]);

  const handleSend = async () => {
    if (!input.trim()) return;

    setMessages((prev) =>
      [
        ...prev,
        currentMessage ? {role: 'system', content: currentMessage} : null,
        {role: 'user', content: input},
      ].filter((v) => !!v)
    );

    setCurrentMessage(null);
    const userMessage = input;
    setInput('');

    const textarea = document.querySelector('textarea');
    if (textarea) {
      textarea.style.height = 'auto';
    }

    setSendingMessage(true);

    try {
      const response = await APIService.sendChatMessage(userMessage, sessionId);
      
      if (response && response.data) {
        const reader = response.data.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              if (data && data !== '[DONE]') {
                setCurrentMessage((prev) => (prev || '') + data);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'system',
          content: 'Sorry, there was an error processing your request. Please try again.',
        },
      ]);
    } finally {
      setSendingMessage(false);
    }
  };

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  function formatText(content: string) {
    return content.replace(/([$£])(\S+)/g, '**$1**$2****');
  }

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
        }`}>
        <div className='w-full max-w-4xl h-[97vh] flex flex-col bg-white rounded-lg border shadow-sm overflow-hidden'>
          <div className='sticky top-0 z-10 bg-white p-4 '>
            <h1 className='text-center font-semibold text-xl'>Explainable AI</h1>
          </div>

          <div ref={chatContainerRef} className='flex-1 overflow-y-auto p-4 space-y-4'>
            {messages.map((message, index) => (
              <div
                key={index}
                className={`mb-3 flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
                data-role={message.role}>
                <div className='max-w-[600px] break-words'>
                  <div
                    className={`font-semibold mb-1 ${
                      message.role === 'user' ? 'text-right mr-3' : 'text-left ml-3'
                    }`}>
                    {message.role === 'user' ? 'You' : 'Explainable AI'}
                  </div>

                  <div
                    className={`whitespace-pre-line break-words border border-gray-300 p-3 rounded-3xl w-auto text-left`}>
                    <div className='markdown-container'>
                      <ReactMarkdown
                        className="prose max-w-none 
                          p-1
                          [&_ol]:list-none [&_ol]:pl-0 [&_ol]:mx-0
                          [&_li>:first-child]:before:content-[counter(list-item,decimal)_'._']
                          [&_ul_li>:first-child]:before:content-none
                          [&_ul]:m-0 [&_ol]:m-0 [&_li]:m-0
                          [&_h3]:m-0
                          [&_li]:py-0
                          [&_li]:-my-2
                          [&_li]:pl-0
                          [&_ol]:-mt-10
                          [&_ul]:my-0
                          [&_ul]:py-0 [&_ol]:py-0
                          [&_p]:py-0
                          [&_p]:mb-1
                          [&_p]:mt-0
                          [&_p]:ml-0
                          [&_blockquote]:my-0
                          leading-tight">
                        {formatText(message.content)}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {currentMessage && (
              <div id='currentMessage' className='mb-3 flex justify-start' data-role='system'>
                <div className='max-w-[600px] break-words'>
                  <div className='font-semibold mb-1 text-left ml-3'>Explainable AI</div>
                  <div className='whitespace-pre-line break-words border border-gray-300 p-3 rounded-3xl w-auto text-left'>
                    <div className='markdown-container'>
                      <ReactMarkdown
                        className="prose max-w-none 
                          p-1
                          [&_ol]:list-none [&_ol]:pl-0 [&_ol]:mx-0
                          [&_li>:first-child]:before:content-[counter(list-item,decimal)_'._']
                          [&_ul_li>:first-child]:before:content-none
                          [&_ul]:m-0 [&_ol]:m-0 [&_li]:m-0
                          [&_h3]:m-0
                          [&_li]:py-0
                          [&_li]:-my-2
                          [&_li]:pl-0
                          [&_ol]:-mt-10
                          [&_ul]:my-0
                          [&_ul]:py-0 [&_ol]:py-0
                          [&_p]:py-0
                          [&_p]:mb-1
                          [&_p]:mt-0
                          [&_p]:ml-0
                          [&_blockquote]:my-0
                          leading-tight">
                        {formatText(currentMessage)}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className='sticky bottom-0 p-4 bg-white'>
            <div className='flex items-center border rounded-lg overflow-hidden shadow-sm min-h-12'>
              <textarea
                className='flex-grow p-3 text-gray-700 placeholder-gray-400 focus:outline-none resize-none max-h-32'
                placeholder='Message Explainable AI'
                value={input}
                disabled={sendingMessage}
                onKeyDown={handleKeyDown}
                onChange={(e) => setInput(e.target.value)}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = `${target.scrollHeight}px`;
                }}
                rows={1}
              />

              <div className='button-container flex justif-between sm:mt-1'>
                <button
                  onClick={handleSend}
                  className='p-3 hover:bg-gray-200'
                  disabled={sendingMessage}>
                  {sendingMessage ? (
                    <SymbolIcon className='h-6 w-6 animate-spin text-gray-600' />
                  ) : (
                    <svg
                      xmlns='http://www.w3.org/2000/svg'
                      fill='none'
                      viewBox='0 0 24 24'
                      strokeWidth={1.5}
                      stroke='currentColor'
                      className='h-6 w-6 text-gray-600'>
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
        </div>
      </div>
    </div>
  );
}
