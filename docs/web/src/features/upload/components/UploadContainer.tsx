'use client';

import {Card, CardContent, CardFooter, CardHeader, CardTitle} from '@lp/components/ui/card';
import {UploadInput} from './UploadInput';
import {UploadButton} from './UploadButton';
import {useState, useEffect} from 'react';
import {z} from 'zod';
import {formSchema} from '../types';
import {useForm} from 'react-hook-form';
import {zodResolver} from '@hookform/resolvers/zod';
import type {UploadFormProps} from '../types';

export function UploadContainer({onSubmit, isFetching, onclick}: UploadFormProps) {
  const [fileSelected, setFileSelected] = useState(false);
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  useEffect(() => {
    const initializeSession = async () => {
      const newSessionId = crypto.randomUUID();
      console.log('Initializing sessionId:', newSessionId);
      form.setValue('sessionId', newSessionId, {shouldValidate: true});
    };
    initializeSession();
  }, [form]);

  return (
    <Card>
      <div className='sticky top-0 bg-white z-10'>
        <CardHeader>
          <CardTitle className='text-center'>Explainable AI</CardTitle>
        </CardHeader>
      </div>

      <CardContent>
        <p className='text-center text-gray-700'>
          Hi! I'm Explainable AI, here to help you understand your results.
        </p>
        <p className='text-center font-semibold text-gray-900 mt-1 text-xl'>
          Upload a file below so we can begin
        </p>
        <div className='h-8' />

        <form onSubmit={form.handleSubmit(onSubmit)}>
          <div className='grid w-full items-center gap-4'>
              <UploadInput
              onChange={(file) => {
                if (!file) {
                  form.setError('file', {message: 'Please select a pdf file.'});
                  return;
                }
                console.log('Selected file:', file);
                form.setValue('file', file, {shouldValidate: true});
                setFileSelected(true);
              }}
              disabled={isFetching}
            />
          </div>
          <CardFooter className='flex justify-center'>
            <UploadButton
              isFetching={isFetching}
              onclick={onclick}
              fileSelected={fileSelected}
              onClick={() => {
                const values = form.getValues();
                console.log('Submitting form with values:', values);
                onSubmit(values);
              }}
            />
          </CardFooter>
        </form>
      </CardContent>
    </Card>
  );
}
