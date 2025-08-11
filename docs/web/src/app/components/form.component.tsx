'use client';

import {zodResolver} from '@hookform/resolvers/zod';
import {useForm} from 'react-hook-form';
import {z} from 'zod';
import {useCallback, useState, useEffect, useRef} from 'react';
import ReactMarkdown from 'react-markdown';
import {useHeader} from '@lp/components/header-context';
import {Sidebar} from '@lp/components/ui/sidebar';
import {ExclamationTriangleIcon, SymbolIcon} from '@radix-ui/react-icons';
import {Button} from '@lp/components/ui/button';
import {Card, CardContent, CardFooter, CardHeader, CardTitle} from '@lp/components/ui/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@lp/components/ui/form';
import {useQuery} from '@tanstack/react-query';
import {APIService} from '@lp/services/api.service';
import {Alert, AlertDescription, AlertTitle} from '@lp/components/ui/alert';
import {Input} from '@lp/components/ui/input';

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

const formSchema = z.object({
  file: z
    .any()
    .refine(
      (value) =>
        value !== null &&
        value !== undefined &&
        (value as File).type === 'application/pdf' &&
        (value as File).name.endsWith('.pdf'),
      {
        message: 'Please select a pdf file.',
      }
    ),
});

export function UploadForm() {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  const [fileSelected, setFileSelected] = useState(false);
  const [messages, setMessages] = useState<{role: string; content: string}[]>([]);
  const [input, setInput] = useState('');
  const [showUploadForm, setShowUploadForm] = useState(true);
  const [summary, setSummary] = useState('');
  const [showValidateButton, setShowValidateButton] = useState(false);
  const [onclick, setOnclick] = useState(false);
  const [validating, setValidating] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [companyName, setCompanyName] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [graphData, setGraphData] = useState<string>('');
  const [sessionId, setSessionId] = useState<string>(''); //Id that is regenerated everytime the page is refreshed
  const {setShowHeader} = useHeader();

  const [currentMessage, setCurrentMessage] = useState<string | null>(null);

  useEffect(() => {
    const initializeSession = async () => {
      const newSessionId = crypto.randomUUID();
      setSessionId(newSessionId);
    };
    initializeSession();
  }, []);

  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll when messages change
    if (chatContainerRef.current && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      const container = chatContainerRef.current;

      // User message: snap to bottom
      if (lastMessage.role === 'user') {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: SCROLL_BEHAVIOUR.user.type,
        });

        // Bot response: smooth to top
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
  }, [messages, currentMessage]); // Trigger on message updates

  const {isError, data, error, refetch, isFetching} = useQuery({
    queryKey: ['uploadFile', form.getValues()],
    queryFn: async () => {
      console.log("📡 queryFn 调用一次");
      const data = await APIService.uploadFile(form.getValues().file, sessionId);
      setMessages((prev) => [
        ...prev,
        {
          role: 'system',
          content: `${
            data.response || 'No response'
          } \n\nIf you'd like, I can quickly do an extra validation by searching and scraping from the web - hit the 'Validate' button below to do so. If you're happy with the current results or have any questions, feel free to ask below!`,
        },
      ]);
      console.log("graphData raw:", data.graphdata, typeof data.graphdata);
      setGraphData(data.graphdata);
      setSummary(data.response || '');
      setShowUploadForm(false);
      setShowHeader(false);
      setCompanyName(data.companyName);
      setShowValidateButton(true);
      return data;
    },
    enabled: false,
    throwOnError: (error, query) => {
      return false;
    },
  });

  const handleClick = () => {
    setOnclick(true);

    setTimeout(() => {
      setOnclick(false);
    }, 500);
  };

  const handleValidate = async () => {
    setValidating(true);
    setSidebarOpen(false);
    try {
      const data = await APIService.validateUpload(summary, companyName, sessionId);
      setMessages((prev) => [
        ...prev,
        {role: 'user', content: 'Validate'},
        {
          role: 'system',
          content: `I have analysed news articles to verify and validate the initial response I gave you which was based on just the uploaded document. Here is the new analysis:\n\n ${
            data.response || 'No response'
          }`,
        },
      ]);
      setGraphData(data.graphdata);
    } catch (error) {
      console.error('Validation error:', error);
      setMessages((prev) => [
        ...prev,
        {role: 'user', content: 'Validate'},
        {
          role: 'system',
          content: 'There was an error validating the document. Please try again.',
        },
      ]);
    } finally {
      setValidating(false);
      setShowValidateButton(false);
      setSidebarOpen(true);
    }
  };

  function onSubmit(values: z.infer<typeof formSchema>) {
    refetch();
  }

  const handleSend = async () => {
    if (!input.trim()) return;

    // Add user message immediately
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
    setShowValidateButton(false);

    try {
      const chatResponse = await APIService.sendChatMessage(userMessage, sessionId);

      let accumulatedText = ""; 
      for await (const chunk of chatResponse.values({ preventCancel: true })) {
        const str = new TextDecoder().decode(chunk);
        accumulatedText += str;
        setCurrentMessage(accumulatedText); 
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
    <>
      {showUploadForm && (
        <Card>
          {/* Sticky header to keep title visible during scroll */}
          <div className='sticky top-0 bg-white z-10'>
            <CardHeader>
              <CardTitle className='text-center'>Explainable AI</CardTitle>
            </CardHeader>
          </div>

          {/* Initial helper text shown before submission */}
          <CardContent>
            <p className='text-center text-gray-700'>
              Hi! I'm Explainable AI, here to help you understand your results.
            </p>
            <p className='text-center font-semibold text-gray-900 mt-1 text-xl'>
              Upload a file below so we can begin
            </p>
            <div className='h-8' />

            {/* PDF Upload Form */}
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)}>
                <div className='grid w-full items-center gap-4'>
                  <FormField
                    control={form.control}
                    name='file'
                    render={({field}) => (
                      <FormItem>
                        <FormLabel>Upload a pdf file</FormLabel>
                        <FormControl>
                          <Input
                            name={field.name}
                            disabled={field.disabled || isFetching}
                            type='file'
                            onChange={(ev) => {
                              if (ev.target.files!.length === 0) {
                                form.setError('file', {
                                  message: 'Please select a pdf file.',
                                });
                                return;
                              }

                              form.setValue('file', ev.target.files![0]);
                              setFileSelected(true);
                            }}
                          />
                        </FormControl>
                        <FormDescription>Only pdf files are supported.</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <CardFooter className='flex justify-center'>
                  <Button
                    type='submit'
                    disabled={isFetching || !fileSelected}
                    onClick={handleClick}>
                    {onclick || isFetching ? (
                      <SymbolIcon className='mr-2 h-4 w-4 animate-spin' />
                    ) : null}
                    Detect
                  </Button>
                </CardFooter>
              </form>
            </Form>
          </CardContent>
        </Card>
      )}

      {/* Chat Interface that shows up after you submit */}
      {isError ? (
        // Error display component
        <Alert variant='destructive'>
          <ExclamationTriangleIcon className='h-4 w-4' />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      ) : (
        !showUploadForm && (
          <div className='flex'>
            {/* Sidebar which provides visualisation of data */}

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

                {/* Scrollable Chat History (only inner scroll bar) */}
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
                              // labelled prose so it could be rendered correctly by tailwind typography
                              // the numbered lists were manually deleted and added back again due to incorrect initial formatting
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
                              // labelled prose so it could be rendered correctly by tailwind typography
                              // the numbered lists were manually deleted and added back again due to incorrect initial formatting
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

                  {showValidateButton && (
                    <div className='flex gap-x-1.5 mt-1 ml-3 text-token-text-primary'>
                      <Button
                        type='submit'
                        disabled={validating || !showValidateButton}
                        onClick={() => {
                          handleValidate();
                          handleClick();
                        }}
                        className='flex whitespace-nowrap bg-blue-500 text-white py-1 px-3 mb-2 rounded-full ml-auto hover:bg-blue-600 transition-colors duration-100'>
                        {!onclick && !validating ? (
                          <svg
                            width='20'
                            height='20'
                            viewBox='0 0 20 20'
                            fill='none'
                            xmlns='http://www.w3.org/2000/svg'
                            className='h-4 w-4 mr-[5px]'>
                            <circle
                              cx='10'
                              cy='10'
                              r='9'
                              stroke='currentColor'
                              strokeWidth='1.8'></circle>
                            <path
                              d='M10 1c1.657 0 3 4.03 3 9s-1.343 9-3 9M10 19c-1.657 0-3-4.03-3-9s1.343-9 3-9M1 10h18'
                              stroke='currentColor'
                              strokeWidth='1.8'></path>
                          </svg>
                        ) : (
                          <SymbolIcon className='mr-2 h-4 w-4 animate-spin' />
                        )}

                        <span className='leading-none mt-[-1px]'>Validate</span>
                      </Button>
                    </div>
                  )}
                </div>

                {/* Fixed Chatbot Input Bar */}
                <div className='sticky bottom-0 p-4 bg-white'>
                  <div className='flex items-center border rounded-lg overflow-hidden shadow-sm min-h-12'>
                    <textarea
                      className='flex-grow p-3 text-gray-700 placeholder-gray-400 focus:outline-none resize-none max-h-32'
                      placeholder='Message Explainable AI'
                      value={input}
                      disabled={sendingMessage || validating}
                      onKeyDown={handleKeyDown}
                      onChange={(e) => setInput(e.target.value)}
                      onInput={(e) => {
                        const target = e.target as HTMLTextAreaElement;
                        target.style.height = 'auto';
                        target.style.height = `${target.scrollHeight}px`;
                      }}
                      rows={1}
                    />

                    {/* Send button with arrow icon */}
                    <div className='button-container flex justif-between sm:mt-1'>
                      <button
                        onClick={handleSend}
                        className='p-3 hover:bg-gray-200'
                        disabled={sendingMessage || validating}>
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
        )
      )}
    </>
  );
}
