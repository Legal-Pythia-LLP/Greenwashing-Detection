'use client';

import {useState} from 'react';
import ReactMarkdown from 'react-markdown';
import {Sidebar} from '@lp/components/ui/sidebar';
import {ChatMessage} from './ChatMessage';
import {ChatInput} from './ChatInput';
import {useChatScroll} from './ChatScroll';

import { ChatContainerProps } from './types';

export function ChatContainer({
  messages,
  currentMessage,
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
  graphData,
  sidebarOpen,
  setSidebarOpen,
  isError,
  error
}: ChatContainerProps) {
  const chatContainerRef = useChatScroll(messages, currentMessage);

  return (
    <>
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
                <ChatMessage
                  key={index}
                  message={message}
                  currentMessage={currentMessage}
                  isError={isError}
                  error={error}
                />
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
                          {currentMessage}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <ChatInput
              input={input}
              setInput={setInput}
              handleSend={handleSend}
              handleKeyDown={handleKeyDown}
              sendingMessage={sendingMessage}
              validating={validating}
              showValidateButton={showValidateButton}
              handleValidate={handleValidate}
              onclick={onclick}
              setOnclick={setOnclick}
            />
          </div>
        </div>
      </div>
    </>
  );
}
