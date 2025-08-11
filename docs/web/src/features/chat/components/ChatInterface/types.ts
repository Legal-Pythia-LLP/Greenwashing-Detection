export interface ChatMessage {
  role: string;
  content: string;
}

export interface ChatInterfaceProps {
  sessionId: string;
  initialMessages?: ChatMessage[];
  graphData?: string;
  companyName?: string;
  onHeaderVisibility?: (show: boolean) => void;
}

export const SCROLL_BEHAVIOUR = {
  user: {
    type: 'smooth' as const,
    position: 'end' as const,
  },
  bot: {
    type: 'smooth' as const,
    position: 'start' as const,
  },
};
