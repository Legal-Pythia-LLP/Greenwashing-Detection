'use client';

import ReactMarkdown from 'react-markdown';
import { ExclamationTriangleIcon } from '@radix-ui/react-icons';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

import { ChatMessageProps } from './types';

export function ChatMessage({ message, currentMessage, isError, error }: ChatMessageProps) {
  function formatText(content: string) {
    return content.replace(/([$£])(\S+)/g, '**$1**$2****');
  }

  if (isError) {
    return (
      <Alert variant='destructive'>
        <ExclamationTriangleIcon className='h-4 w-4' />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error?.message ?? 'Unknown error'}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className={`mb-3 flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className='max-w-[600px] break-words'>
        <div className={`font-semibold mb-1 ${message.role === 'user' ? 'text-right mr-3' : 'text-left ml-3'}`}>
          {message.role === 'user' ? 'You' : 'Explainable AI'}
        </div>

        <div className={`whitespace-pre-line break-words border border-border p-3 rounded-3xl w-auto text-left`}>
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
  );
}
