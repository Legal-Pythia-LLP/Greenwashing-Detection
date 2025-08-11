'use client';

import { useState, useEffect, useCallback } from 'react';
import { APIService } from '@lp/services/api.service';
import { ChatMessage } from '../components/ChatInterface/types';

export function useChat(sessionId: string, initialMessages: ChatMessage[] = []) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState('');
  const [currentMessage, setCurrentMessage] = useState<string | null>(null);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleSend = useCallback(async () => {
    if (!input.trim()) return;

    setMessages((prev) =>
      [
        ...prev,
        currentMessage ? { role: 'system', content: currentMessage } : null,
        { role: 'user', content: input },
      ].filter(Boolean) as ChatMessage[]
    );

    setCurrentMessage(null);
    const userMessage = input;
    setInput('');
    setSendingMessage(true);

    try {
      const response = await APIService.sendChatMessage(userMessage, sessionId);
      
      if (response?.data) {
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
  }, [input, currentMessage, sessionId]);

  return {
    messages,
    input,
    setInput,
    currentMessage,
    sendingMessage,
    sidebarOpen,
    setSidebarOpen,
    handleSend,
  };
}
