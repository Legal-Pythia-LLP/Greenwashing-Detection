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
  sessionId: z.string().uuid(),
});

export type UploadFormProps = {
  onSubmit: (values: z.infer<typeof formSchema> & {sessionId: string}) => void;
  isFetching: boolean;
  onclick: boolean;
};

export interface UploadButtonProps {
  isFetching: boolean;
  onclick: boolean;
  fileSelected: boolean;
  onClick: () => void;
}

export interface UploadInputProps {
  onChange: (file: File | null) => void;
  disabled: boolean;
}

export interface UploadLanguageSelectProps {
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}
