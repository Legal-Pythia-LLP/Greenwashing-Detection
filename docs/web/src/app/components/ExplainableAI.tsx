'use client';

import {useCallback, useState, useEffect} from 'react';
import {useQuery} from '@tanstack/react-query';
import {useForm, FormProvider} from 'react-hook-form';
import {z} from 'zod';
import {zodResolver} from '@hookform/resolvers/zod';
import {APIService} from '@lp/services/api.service';
import {useHeader} from '@lp/components/header-context';
import {UploadContainer} from '@lp/features/upload/components/UploadContainer';
import {ChatContainer} from '@lp/features/chat/components/ChatInterface/ChatContainer';
import {formSchema} from '@lp/features/upload/types';

export function ExplainableAI() {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });
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
  const [currentMessage, setCurrentMessage] = useState<string | null>(null);
  const {setShowHeader} = useHeader();

  const {isError, data, error, refetch, isFetching} = useQuery({
    queryKey: ['uploadFile'],
    queryFn: async () => {
      const formValues = form.getValues();
      console.log('Uploading file:', formValues.file);
      console.log('With sessionId:', formValues.sessionId);
      const data = await APIService.uploadFile(formValues.file, formValues.sessionId, false); // 是否使用模拟数据mockData.ts
      setMessages((prev) => [
        ...prev,
        {
          role: 'system',
          content: `${data.response || 'No response'} \n\nIf you'd like, I can quickly do an extra validation by searching and scraping from the web - hit the 'Validate' button below to do so. If you're happy with the current results or have any questions, feel free to ask below!`,
        },
      ]);
      setGraphData(JSON.stringify({
        overall_greenwashing_score: {score: 8},
        Vague_or_unsubstantiated_claims: {score: 9},
        Lack_of_specific_metrics_or_targets: {score: 7},
        Misleading_terminology: {score: 8},
        Cherry_picked_data: {score: 6},
        Absence_of_third_party_verification: {score: 7}
      }));
      setSummary(data.response || '');
      setShowUploadForm(false);
      setShowHeader(false);
      setCompanyName(data.companyName);
      setShowValidateButton(true);
      return data;
    },
    enabled: false,
    throwOnError: (error, query) => false,
  });

  const handleClick = () => {
    setOnclick(true);
    setTimeout(() => setOnclick(false), 500);
  };

  const handleValidate = async () => {
    setValidating(true);
    setSidebarOpen(false);
    try {
      const formValues = form.getValues();
      const data = await APIService.validateUpload(summary, companyName, formValues.sessionId);
      setMessages((prev) => [
        ...prev,
        {role: 'user', content: 'Validate'},
        {
          role: 'system',
          content: `I have analysed news articles to verify and validate the initial response I gave you which was based on just the uploaded document. Here is the new analysis:\n\n ${data.response || 'No response'}`,
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
    setSendingMessage(true);
    setShowValidateButton(false);

    try {
      const formValues = form.getValues();
      const chatResponse = await APIService.sendChatMessage(userMessage, formValues.sessionId);
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

  return (
    <FormProvider {...form}>
      {showUploadForm ? (
      <UploadContainer 
        onSubmit={(values) => {
          console.log('Form submitted with values:', values);
          form.setValue('file', values.file);
          form.setValue('sessionId', values.sessionId);
          refetch();
        }}
        isFetching={isFetching} 
        onclick={onclick} 
      />
      ) : (
            <ChatContainer
              messages={messages}
              currentMessage={currentMessage}
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
              graphData={graphData}
              sidebarOpen={sidebarOpen}
              setSidebarOpen={setSidebarOpen}
              isError={isError}
              error={error}
            />
      )}
    </FormProvider>
  );
}
