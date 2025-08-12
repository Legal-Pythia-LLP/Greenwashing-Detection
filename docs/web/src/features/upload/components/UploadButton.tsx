'use client';

import {Button} from '@lp/components/ui/button';
import {SymbolIcon} from '@radix-ui/react-icons';
import type {UploadButtonProps} from '../types';

export function UploadButton({
  isFetching,
  onclick,
  fileSelected,
  onClick
}: UploadButtonProps) {
  return (
    <Button
      type='submit'
      disabled={isFetching || !fileSelected}
      onClick={onClick}
    >
      {onclick || isFetching ? (
        <SymbolIcon className='mr-2 h-4 w-4 animate-spin' />
      ) : null}
      Detect
    </Button>
  );
}
