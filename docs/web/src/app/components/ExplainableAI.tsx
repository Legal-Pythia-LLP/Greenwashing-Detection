'use client';

import {useState, useEffect} from 'react';
import {UploadContainer} from '@lp/features/upload/components';
import {ChatInterface} from '@lp/features/chat/components/ChatInterface';
import {useHeader} from '@lp/components/header-context';

export function ExplainableAI() {
  const [sessionId, setSessionId] = useState<string>('');
  const [messages, setMessages] = useState<{role: string; content: string}[]>([]);
  const [graphData, setGraphData] = useState<string>('');
  const [companyName, setCompanyName] = useState<string>('');
  const [showUploadForm, setShowUploadForm] = useState(true);
  const {setShowHeader} = useHeader();

  useEffect(() => {
    const initializeSession = async () => {
      const newSessionId = crypto.randomUUID();
      setSessionId(newSessionId);
    };
    initializeSession();
  }, []);

  const handleUploadSuccess = (data: any) => {
    const responseText = data.response || 'No response';
    const comprehensiveText = data.comprehensive_analysis || '';
    const finalText = comprehensiveText ? `${responseText}\n\n${comprehensiveText}` : responseText;
    
    setMessages([
      {
        role: 'system',
        content: `${finalText} \n\nIf you have any questions about the analysis, feel free to ask below!`,
      },
    ]);
    setGraphData(data.graphdata || '');
    setShowUploadForm(false);
    setShowHeader(false);
    setCompanyName(data.company_name || '');
  };

  return (
    <div className="container mx-auto p-4">
      {showUploadForm ? (
        <UploadContainer
          sessionId={sessionId} 
          onUploadSuccess={handleUploadSuccess} 
        />
      ) : (
        <ChatInterface
          sessionId={sessionId}
          initialMessages={messages}
          graphData={graphData}
          companyName={companyName}
          onHeaderVisibility={setShowHeader}
        />
      )}
    </div>
  );
}
