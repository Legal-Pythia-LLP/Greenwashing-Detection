'use client';

import {zodResolver} from '@hookform/resolvers/zod';
import {useForm} from 'react-hook-form';
import {z} from 'zod';
import {useState} from 'react';
import {SymbolIcon} from '@radix-ui/react-icons';
import {Button} from '@lp/components/ui/button';
import {Card, CardContent, CardFooter, CardHeader, CardTitle} from '@lp/components/ui/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@lp/components/ui/form';
import {Input} from '@lp/components/ui/input';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@lp/components/ui/select';
import {useQuery} from '@tanstack/react-query';
import {APIService} from '@lp/services/api.service';

const formSchema = z.object({
  file: z
    .any()
    .refine(
      (value) =>
        value !== null &&
        value !== undefined &&
        (value as File).type === 'application/pdf' &&
        (value as File).name.endsWith('.pdf'),
      {
        message: 'Please select a pdf file.',
      }
    ),
  language: z.string().optional(),
});

interface UploadFormProps {
  sessionId: string;
  onUploadSuccess: (data: any) => void;
}

export function UploadForm({sessionId, onUploadSuccess}: UploadFormProps) {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      language: 'en',
    },
  });

  const [fileSelected, setFileSelected] = useState(false);
  const [onclick, setOnclick] = useState(false);

  const {isFetching, refetch} = useQuery({
    queryKey: ['uploadFile', form.getValues()],
    queryFn: async () => {
      const values = form.getValues();
      const data = await APIService.uploadFile(values.file, sessionId, values.language, true);
      onUploadSuccess(data);
      return data;
    },
    enabled: false,
  });

  function onSubmit(values: z.infer<typeof formSchema>) {
    refetch();
  }

  const handleClick = () => {
    setOnclick(true);
    setTimeout(() => {
      setOnclick(false);
    }, 500);
  };

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
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className='grid w-full items-center gap-4'>
              <FormField
                control={form.control}
                name='file'
                render={({field}) => (
                  <FormItem>
                    <FormLabel>Upload a pdf file</FormLabel>
                    <FormControl>
                      <Input
                        name={field.name}
                        disabled={field.disabled || isFetching}
                        type='file'
                        onChange={(ev) => {
                          if (ev.target.files!.length === 0) {
                            form.setError('file', {
                              message: 'Please select a pdf file.',
                            });
                            return;
                          }
                          form.setValue('file', ev.target.files![0]);
                          setFileSelected(true);
                        }}
                      />
                    </FormControl>
                    <FormDescription>Only pdf files are supported.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name='language'
                render={({field}) => (
                  <FormItem>
                    <FormLabel>Document Language (Optional)</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select language" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="en">English</SelectItem>
                        <SelectItem value="zh">Chinese</SelectItem>
                        <SelectItem value="es">Spanish</SelectItem>
                        <SelectItem value="fr">French</SelectItem>
                        <SelectItem value="de">German</SelectItem>
                        <SelectItem value="it">Italian</SelectItem>
                        <SelectItem value="pt">Portuguese</SelectItem>
                        <SelectItem value="ru">Russian</SelectItem>
                        <SelectItem value="ja">Japanese</SelectItem>
                        <SelectItem value="ko">Korean</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>Select the language of your document for better analysis.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <CardFooter className='flex justify-center'>
              <Button
                type='submit'
                disabled={isFetching || !fileSelected}
                onClick={handleClick}>
                {onclick || isFetching ? (
                  <SymbolIcon className='mr-2 h-4 w-4 animate-spin' />
                ) : null}
                Analyze
              </Button>
            </CardFooter>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
