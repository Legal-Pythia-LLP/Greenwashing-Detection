import {FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage} from '@lp/components/ui/form';
import {Input} from '@lp/components/ui/input';
import {useState} from 'react';

interface UploadInputProps {
  form: any;
  isUploading: boolean;
}

export function UploadInput({form, isUploading}: UploadInputProps) {
  const [fileSelected, setFileSelected] = useState(false);

  return (
    <FormField
      control={form.control}
      name="file"
      render={({field}) => (
        <FormItem>
          <FormLabel>Upload a pdf file</FormLabel>
          <FormControl>
            <Input
              name={field.name}
              disabled={field.disabled || isUploading}
              type="file"
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
  );
}
