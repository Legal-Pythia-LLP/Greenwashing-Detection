import {useQuery} from '@tanstack/react-query';
import {APIService} from '@lp/services/api.service';
import {UploadFormValues} from '../types';
import {UseFormReturn} from 'react-hook-form';

interface UseUploadProps {
  sessionId: string;
  onUploadSuccess: (data: any) => void;
  form: UseFormReturn<UploadFormValues>;
}

export function useUpload({sessionId, onUploadSuccess, form}: UseUploadProps) {
  const {isFetching, refetch} = useQuery({
    queryKey: ['uploadFile', form.getValues()],
    queryFn: async () => {
      const values = form.getValues();
      const data = await APIService.uploadFile(
        values.file, 
        sessionId, 
        values.language
      );
      onUploadSuccess(data);
      return data;
    },
    enabled: false,
  });

  return {
    isUploading: isFetching,
    uploadFile: refetch,
  };
}
