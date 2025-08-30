export interface Message {
  role: string;
  content: string;
}

export interface ChatContainerProps {
  messages: Message[];
  currentMessage: string | null;
  input: string;
  setInput: (value: string) => void;
  handleSend: () => void;
  handleKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  sendingMessage: boolean;
  validating: boolean;
  showValidateButton: boolean;
  handleValidate: () => void;
  onclick: boolean;
  setOnclick: (value: boolean) => void;
  graphData: any;
  sidebarOpen: boolean;
  setSidebarOpen: (value: boolean) => void;
  isError: boolean;
  error: any;
}

export interface ChatMessageProps {
  message: Message;
  currentMessage: string | null;
  isError: boolean;
  error: any;
}

export interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  handleSend: () => void;
  handleKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  sendingMessage: boolean;
  validating: boolean;
  showValidateButton: boolean;
  handleValidate: () => void;
  onclick: boolean;
  setOnclick: (value: boolean) => void;
}

export interface ScrollBehaviour {
  type: 'smooth' | 'auto';
  position: 'start' | 'center' | 'end' | 'nearest';
}
