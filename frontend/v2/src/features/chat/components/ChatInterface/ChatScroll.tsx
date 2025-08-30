'use client';

import { useEffect, useRef } from 'react';

import { ScrollBehaviour } from './types';

const SCROLL_BEHAVIOUR = {
  user: {
    type: 'smooth' as const,
    position: 'end' as const,
  },
  bot: {
    type: 'smooth' as const,
    position: 'start' as const,
  },
} satisfies { user: ScrollBehaviour; bot: ScrollBehaviour };

export function useChatScroll(messages: { role: string; content: string }[], currentMessage: string | null) {
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
          (lastBot as HTMLElement).scrollIntoView({
            behavior: SCROLL_BEHAVIOUR.bot.type,
            block: SCROLL_BEHAVIOUR.bot.position,
          });
        }
      }
    }
  }, [messages, currentMessage]);

  return chatContainerRef;
}
