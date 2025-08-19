import { useCallback, useState } from "react"; 
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import TopNav from "@/components/TopNav";
import Seo from "@/components/Seo";
import { FloatingChatbot } from "@/components/FloatingChatbot";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { APIService, api } from "../services/api.service";

const Upload = () => {
  const { t } = useTranslation();
  const [dragActive, setDragActive] = useState(false);
  const [priority, setPriority] = useState("normal");
  const [customRules, setCustomRules] = useState(false);
  const [files, setFiles] = useState<FileList | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState('');
  const [showDuplicateDialog, setShowDuplicateDialog] = useState(false);
  const [duplicateResult, setDuplicateResult] = useState<any>(null);
  const navigate = useNavigate();

  const onFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;
    setFiles(files);
    const names = Array.from(files).map(f => f.name).join(", ");
    toast.success(t('upload.selectedFiles', { names }));
  }, [t]);

  const generateSessionId = () => "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);

  const handleStart = async () => {
    if (!files || files.length === 0) {
      toast.error(t("upload.selectFirstMsg"));
      return;
    }

    const formData = new FormData();
    formData.append("file", files[0]);
    // If optional language is needed, add this line:
    // formData.append("overrided_language", "zh");

    try {
      setUploading(true);
      setUploadProgress(10);
      setUploadStage(t("upload.uploadingFile"));

      // Simulate progress update
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev < 90) return prev + 10;
          return prev;
        });
      }, 2000);

      // Call API service with FormData upload
      const data = await APIService.uploadFile(formData);
      
      // Handle duplicate file situation
      if (data?.status === "duplicate") {
        clearInterval(progressInterval);
        setUploadProgress(0);
        setUploadStage("");
        setDuplicateResult(data);
        setShowDuplicateDialog(true);
        return;
      }

      const sessionId = data?.session_id;
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadStage(t("upload.analysisComplete"));

      if (!sessionId) {
        toast.error("Backend did not return session_id, unable to view analysis results");
        return;
      }

      toast.success(t("upload.analysisCreated"));
      try {
        localStorage.setItem("lastSessionId", sessionId);
      } catch {}

      navigate(`/company/${sessionId}`);
    } catch (e: any) {
      console.error("Upload error:", e);

      // Provide more friendly error messages
      let errorMessage = t("upload.uploadFailedRetry");

      if (e?.message) {
        if (e.message.includes("timeout")) {
          errorMessage = t("upload.errors.timeout");
        } else if (e.message.includes("ECONNABORTED")) {
          errorMessage = t("upload.errors.connectionFailed");
        } else {
          errorMessage = e.message;
        }
      }

      toast.error(errorMessage);
    } finally {
      setUploading(false);
      setUploadProgress(0);
      setUploadStage("");
    }
  };

  return (
    <div className="min-h-screen [background-image:var(--gradient-soft)]">
      <Seo
        title={`${t('upload.title')} | ${t('nav.title')}`}
        description={t('upload.subtitle')}
        canonical={typeof window !== 'undefined' ? window.location.href : undefined}
      />
      <TopNav />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight">{t('upload.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('upload.subtitle')}</p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>{t('nav.upload')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => { e.preventDefault(); setDragActive(false); onFiles(e.dataTransfer.files); }}
              className={`border-2 border-dashed rounded-md p-10 text-center transition-colors ${dragActive ? 'border-accent' : 'border-border'}`}
              aria-label={t('upload.selectFile')}
            >
              <p className="mb-3">{t('upload.selectFile')}</p>
              <Input type="file" accept=".pdf,image/*" multiple onChange={(e) => onFiles(e.target.files)} />
            </div>

            <Separator className="my-6" />

            <div className="grid gap-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
                <Label htmlFor="priority">{t('upload.analysisPriority')}</Label>
                <Select value={priority} onValueChange={setPriority}>
                  <SelectTrigger id="priority">
                    <SelectValue placeholder={t('upload.priorityPlaceholder')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="urgent">{t('upload.urgent')}</SelectItem>
                    <SelectItem value="normal">{t('upload.normal')}</SelectItem>
                    <SelectItem value="low">{t('upload.low')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
                <Label htmlFor="rules">{t('upload.customRules')}</Label>
                <div className="flex items-center gap-3">
                  <Switch id="rules" checked={customRules} onCheckedChange={setCustomRules} />
                  <span className="text-sm text-muted-foreground">{t('upload.customRulesDesc')}</span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
                <Label htmlFor="note">{t('upload.note')}</Label>
                <Input id="note" placeholder={t('upload.notePlaceholder')} />
              </div>

              {/* Upload progress display */}
              {uploading && (
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span>{uploadStage}</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-muted-foreground text-center">
                    {t("upload.analysisTimeWarning")}
                  </p>
                </div>
              )}

              <div className="flex justify-end">
                <Button onClick={handleStart} disabled={uploading || !files}>
                  {uploading ? t('upload.uploading') : t('upload.startAnalysis')}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
      <FloatingChatbot />

      {/* Duplicate file dialog */}
      <AlertDialog open={showDuplicateDialog} onOpenChange={setShowDuplicateDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("upload.duplicateDialog.title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("upload.duplicateDialog.description")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              if (duplicateResult?.session_id) {
                navigate(`/company/${duplicateResult.session_id}`);
              }
            }}>
              {t("upload.duplicateDialog.showOld")}
            </AlertDialogCancel>
            <AlertDialogAction onClick={async () => {
              try {
                setUploading(true);
                setUploadProgress(10);
                setUploadStage(t("upload.reanalyzing"));
                setShowDuplicateDialog(false);
                
                // Force reanalysis, add random session_id and force_new flag
                const formData = new FormData();
                formData.append("file", files[0]);
                formData.append("session_id", `s_${Date.now()}`);
                formData.append("force_new", "true");
                // Add current language setting
                formData.append("language", localStorage.getItem("i18nextLng") || "en");
                
                const data = await APIService.uploadFile(formData);
                const sessionId = data?.session_id;
                if (sessionId) {
                  navigate(`/company/${sessionId}`);
                }
              } catch (error) {
                toast.error(t("upload.errors.reanalyzeFailed"));
              } finally {
                setUploading(false);
              }
            }}>
              {t("upload.duplicateDialog.reanalyze")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Upload;
