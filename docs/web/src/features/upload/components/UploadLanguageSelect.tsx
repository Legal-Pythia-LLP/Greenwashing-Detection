import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@lp/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@lp/components/ui/select';

interface UploadLanguageSelectProps {
  form: any;
}

export function UploadLanguageSelect({form}: UploadLanguageSelectProps) {
  return (
    <FormField
      control={form.control}
      name="language"
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
          <FormDescription>
            Select the language of your document for better analysis.
          </FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
