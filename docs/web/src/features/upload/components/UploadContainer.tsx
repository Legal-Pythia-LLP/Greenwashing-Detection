'use client';

import {z} from 'zod';
import {Form} from '@lp/components/ui/form';
import {useUpload} from '../hooks/useUpload';
import {UploadFormProps} from '../types';
import {useForm} from 'react-hook-form';
import {formSchema} from '../types';
import {zodResolver} from '@hookform/resolvers/zod';
import {UploadInput} from './UploadInput';
import {UploadLanguageSelect} from './UploadLanguageSelect';
import {UploadButton} from './UploadButton';
import {Card, CardContent, CardFooter, CardHeader, CardTitle} from '@lp/components/ui/card';

export function UploadContainer({sessionId, onUploadSuccess}: UploadFormProps) {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      language: 'en',
    },
  });

  const {isUploading, uploadFile} = useUpload({
    sessionId,
    onUploadSuccess,
    form
  });

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

        <Form {...form}>
          <form onSubmit={form.handleSubmit(() => uploadFile())}>
            <div className='grid w-full items-center gap-4'>
              <UploadInput form={form} isUploading={isUploading} />
              <UploadLanguageSelect form={form} />
            </div>
            <CardFooter className='flex justify-center'>
              <UploadButton isUploading={isUploading} />
            </CardFooter>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
