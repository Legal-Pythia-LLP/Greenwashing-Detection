import {z} from 'zod';

export const formSchema = z.object({
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

export type UploadFormValues = z.infer<typeof formSchema>;

import {UseFormReturn} from 'react-hook-form';

export interface UploadFormProps {
  sessionId: string;
  onUploadSuccess: (data: any) => void;
}
