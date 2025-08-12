'use client';

import {Input} from '@lp/components/ui/input';
import {FormControl, FormDescription, FormItem, FormLabel, FormMessage} from '@lp/components/ui/form';
import type {UploadInputProps} from '../types';

export function UploadInput({onChange, disabled}: UploadInputProps) {
  return (
    <FormItem>
      <FormLabel>Upload a pdf file</FormLabel>
      <FormControl>
        <Input
          type='file'
          disabled={disabled}
          onChange={(ev) => {
            if (ev.target.files?.length) {
              onChange(ev.target.files[0]);
            } else {
              onChange(null);
            }
          }}
          accept='.pdf'
        />
      </FormControl>
      <FormDescription>Only pdf files are supported.</FormDescription>
      <FormMessage />
    </FormItem>
  );
}
