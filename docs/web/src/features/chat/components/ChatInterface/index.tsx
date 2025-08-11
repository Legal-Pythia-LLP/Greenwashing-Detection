'use client';

import { ChatInterfaceProps } from './types';
import { useChat } from '../../hooks/useChat';
import { useChatScroll } from './ChatScroll';
import { ChatContainer } from './ChatContainer';
import { ChatInput } from './ChatInput';

export function ChatInterface({
  sessionId,
  initialMessages = [],
  graphData = '',
  companyName = '',
  onHeaderVisibility
}: ChatInterfaceProps) {
  const {
    messages,
    input,
    setInput,
    currentMessage,
    sendingMessage,
    sidebarOpen,
    setSidebarOpen,
    handleSend
  } = useChat(sessionId, initialMessages);

  const chatContainerRef = useChatScroll(messages, currentMessage);

  return (
    <>
      <ChatContainer
        messages={messages}
        currentMessage={currentMessage}
        graphData={graphData}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        chatContainerRef={chatContainerRef}
      />
      <ChatInput
        value={input}
        sending={sendingMessage}
        onChange={setInput}
        onSend={handleSend}
      />
    </>
  );
}
