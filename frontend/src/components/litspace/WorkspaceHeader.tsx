import type { Project } from "@/lib/api";

type WorkspaceHeaderProps = {
  project: Project | null;
  paperCount: number;
  indexedCount: number;
  uploading: boolean;
  onUploadFiles: (files: FileList | null) => void;
};

export function WorkspaceHeader({
  project,
  paperCount,
  indexedCount,
  uploading,
  onUploadFiles,
}: WorkspaceHeaderProps) {
  const canUpload = Boolean(project) && !uploading;

  return (
    <header className="flex h-[78px] shrink-0 items-center justify-between border-b border-slate-200/90 bg-white/90 px-6 backdrop-blur">
      <div className="min-w-0">
        {project ? (
          <div className="flex min-w-0 items-center gap-3">
            <h1 className="truncate text-lg font-semibold text-slate-950">{project.name}</h1>
            <span className="shrink-0 rounded-full bg-[var(--brand-blue-soft)] px-3 py-1 text-xs font-semibold text-[var(--brand-ink-soft)]">
              {indexedCount} of {paperCount} indexed
            </span>
          </div>
        ) : (
          <>
            <h1 className="text-lg font-semibold text-slate-950">Project workspace</h1>
            <p className="mt-1 text-sm text-slate-500">Create a project to start a dedicated paper workspace.</p>
          </>
        )}
      </div>

      <label
        className={[
          "ml-4 rounded-md px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition",
          canUpload
            ? "cursor-pointer bg-[var(--brand-teal)] hover:bg-[var(--brand-teal-hover)]"
            : "cursor-not-allowed bg-slate-400 opacity-70",
        ].join(" ")}
      >
        {uploading ? "Processing PDFs..." : "Upload PDFs"}
        <input
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="hidden"
          disabled={!canUpload}
          onChange={(event) => {
            onUploadFiles(event.target.files);
            event.target.value = "";
          }}
        />
      </label>
    </header>
  );
}
