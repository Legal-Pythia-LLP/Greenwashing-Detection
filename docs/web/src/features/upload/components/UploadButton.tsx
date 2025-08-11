import {Button} from '@lp/components/ui/button';
import {SymbolIcon} from '@radix-ui/react-icons';
import {useState} from 'react';

interface UploadButtonProps {
  isUploading: boolean;
}

export function UploadButton({isUploading}: UploadButtonProps) {
  const [onclick, setOnclick] = useState(false);

  const handleClick = () => {
    setOnclick(true);
    setTimeout(() => {
      setOnclick(false);
    }, 500);
  };

  return (
    <Button
      type="submit"
      disabled={isUploading}
      onClick={handleClick}
    >
      {onclick || isUploading ? (
        <SymbolIcon className="mr-2 h-4 w-4 animate-spin" />
      ) : null}
      Analyze
    </Button>
  );
}
