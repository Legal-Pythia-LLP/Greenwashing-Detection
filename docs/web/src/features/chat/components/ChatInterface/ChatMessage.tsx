'use client';

import ReactMarkdown from 'react-markdown';
import type { ChatMessage } from './types';

interface ChatMessageProps {
  message: ChatMessage;
  isCurrent?: boolean;
}

export function ChatMessage({ message, isCurrent = false }: ChatMessageProps) {
  return (
    <div
      className={`mb-3 flex ${
        message.role === 'user' ? 'justify-end' : 'justify-start'
      }`}
      data-role={message.role}
    >
      <div className='max-w-[600px] break-words'>
        <div
          className={`font-semibold mb-1 ${
            message.role === 'user' ? 'text-right mr-3' : 'text-left ml-3'
          }`}
        >
          {message.role === 'user' ? 'You' : 'Explainable AI'}
        </div>

        <div
          className={`whitespace-pre-line break-words border border-gray-300 p-3 rounded-3xl w-auto text-left`}
        >
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
                leading-tight"
            >
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
