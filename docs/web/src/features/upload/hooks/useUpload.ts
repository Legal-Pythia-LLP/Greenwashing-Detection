'use client';

import {useState} from 'react';
import {formSchema} from '../types';
import {z} from 'zod';

export function useUpload() {
  const [isFetching, setIsFetching] = useState(false);
  const [onclick, setOnclick] = useState(false);

  const handleSubmit = async (values: z.infer<typeof formSchema>) => {
    setIsFetching(true);
    setOnclick(true);
    
    try {
      // 这里添加实际的上传逻辑
      console.log('Uploading file:', values.file);
      
      // 模拟上传延迟
      await new Promise(resolve => setTimeout(resolve, 1000));
    } finally {
      setIsFetching(false);
      setTimeout(() => setOnclick(false), 500);
    }
  };

  return {
    isFetching,
    onclick,
    handleSubmit
  };
}
