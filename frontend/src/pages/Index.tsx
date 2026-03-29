import { useState, useRef, useCallback, DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileVideo, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { analyzeVideo } from "@/lib/api";

const ACCEPTED_TYPES = ["video/mp4", "video/webm", "video/quicktime"];
const MAX_SIZE = 300 * 1024 * 1024; // 300MB

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const UploadPage = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback((f: File) => {
    setError(null);
    if (!ACCEPTED_TYPES.includes(f.type)) {
      setError("Unsupported format. Please use MP4, WebM, or MOV.");
      return;
    }
    if (f.size > MAX_SIZE) {
      setError("File too large. Maximum size is 300MB.");
      return;
    }
    setFile(f);
    setFileUrl(URL.createObjectURL(f));
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const clearFile = () => {
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    setFile(null);
    setFileUrl(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setAnalyzing(true);
    try {
      const { session_id } = await analyzeVideo(file);
      navigate(`/session/${session_id}/timeline`);
    } catch {
      // API unavailable — fall back to demo
      toast({
        title: "Backend not connected",
        description: "Using demo mode. Connect the API for real analysis.",
        variant: "destructive",
      });
      setTimeout(() => navigate("/session/demo/timeline"), 2000);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-6rem)] px-4">
      {/* Header */}
      <div className="text-center mb-10 max-w-xl">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Analyze Your Focus
        </h1>
        <p className="text-muted-foreground">
          Upload a lecture recording or start a live session to understand your
          engagement patterns
        </p>
      </div>

      {/* Upload Card */}
      <div className="w-full max-w-lg">
        <Card className="bg-card border-border p-6 flex flex-col">
          <h2 className="text-lg font-semibold text-foreground mb-4">
            Upload Video
          </h2>

          {!file ? (
            <>
              {/* Dropzone */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center min-h-[200px] rounded-lg border-2 border-dashed cursor-pointer transition-colors ${
                  dragOver
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-muted-foreground"
                }`}
              >
                <Upload className="h-10 w-10 text-muted-foreground mb-3" />
                <p className="text-sm text-muted-foreground text-center">
                  Drag &amp; drop your lecture video here
                </p>
              </div>

              <div className="flex items-center gap-3 my-4">
                <div className="h-px flex-1 bg-border" />
                <span className="text-xs text-muted-foreground">or</span>
                <div className="h-px flex-1 bg-border" />
              </div>

              <Button onClick={() => fileInputRef.current?.click()}>
                Browse Files
              </Button>

              <p className="text-xs text-muted-foreground mt-3 text-center">
                MP4, WebM, MOV — Max 300MB
              </p>

              <input
                ref={fileInputRef}
                type="file"
                accept="video/mp4,video/webm,video/quicktime"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFile(f);
                }}
              />

              {error && (
                <p className="text-xs text-destructive mt-2 text-center">
                  {error}
                </p>
              )}
            </>
          ) : (
            /* File selected state */
            <div className="flex flex-col gap-4 flex-1">
              {fileUrl && (
                <video
                  src={fileUrl}
                  className="w-full rounded-lg aspect-video bg-background object-cover"
                  muted
                />
              )}

              <div className="flex items-center gap-3">
                <FileVideo className="h-5 w-5 text-primary shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatSize(file.size)}
                  </p>
                </div>
                <button
                  onClick={clearFile}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {analyzing ? (
                <div className="space-y-2">
                  <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
                    <div className="h-full bg-primary animate-indeterminate rounded-full" />
                  </div>
                  <p className="text-xs text-muted-foreground text-center animate-pulse">
                    Analyzing engagement patterns...
                  </p>
                </div>
              ) : (
                <Button onClick={handleAnalyze} className="w-full">
                  Analyze
                </Button>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default UploadPage;
