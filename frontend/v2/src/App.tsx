import {Toaster} from '@/components/ui/toaster';
import {Toaster as Sonner} from '@/components/ui/sonner';
import {TooltipProvider} from '@/components/ui/tooltip';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {BrowserRouter, Routes, Route} from 'react-router-dom';
import Index from './pages/Index';
import Company from './pages/Company';
import RiskByLocation from "@/pages/RiskByLocation";
import Upload from './pages/Upload';
import NotFound from './pages/NotFound';
import {FloatingChatbot} from './components/FloatingChatbot';

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path='/' element={<Index />} />
          <Route path='/company/:id' element={<Company />} />
          <Route path="/risk-by-location" element={<RiskByLocation />} />
          <Route path="/by-location" element={<RiskByLocation />} />

          <Route path='/upload' element={<Upload />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path='*' element={<NotFound />} />
        </Routes>
        <FloatingChatbot />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
