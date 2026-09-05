export type UploadKind = "screenshot" | "audio";
export const imageTypes = ["image/png", "image/jpeg", "image/webp"];
export const audioTypes = ["audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave", "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a", "audio/m4a", "audio/webm", "video/webm"];
const audioExtensions = ["wav", "mp3", "m4a", "webm"];

export function validateUpload(file: File, kind: UploadKind): string | null {
  if (kind === "screenshot") {
    if (!imageTypes.includes(file.type)) return "Choose a PNG, JPEG or WEBP screenshot.";
    if (file.size > 5 * 1024 * 1024) return "Choose a screenshot up to 5 MiB.";
  } else {
    if (!audioExtensions.includes(file.name.split(".").at(-1)?.toLowerCase() ?? "") ||
      (file.type && !audioTypes.includes(file.type.split(";")[0]))) return "Choose a WAV, MP3, M4A or WEBM recording.";
    if (file.size > 20 * 1024 * 1024) return "Choose a recording up to 20 MiB and two minutes long.";
  }
  return null;
}

export function appendUpload(form: FormData, file: File, kind: UploadKind) {
  const typeByExtension: Record<string, string> = { wav: "audio/wav", mp3: "audio/mpeg", m4a: "audio/mp4", webm: "audio/webm" };
  const value = kind === "audio" && !file.type
    ? new Blob([file], { type: typeByExtension[file.name.split(".").at(-1)!.toLowerCase()] }) : file;
  form.append("file", value, file.name);
}
