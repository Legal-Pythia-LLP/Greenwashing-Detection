'use client';

import { useEffect, useRef } from 'react';
import { SCROLL_BEHAVIOUR } from './types';

export function useChatScroll(messages: any[], currentMessage: string | null) {
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

  return chatContainerRef;
}
