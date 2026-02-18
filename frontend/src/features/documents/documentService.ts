import { generateDocx, generateXlsx, downloadFile } from "@/utils/api";

export interface DocumentRequest {
  message: string;
  provider: string;
  model: string;
  api_key?: string;
}

export class DocumentService {
  static async generateDocument(
    action: string,
    request: DocumentRequest
  ): Promise<{
    filename: string;
    blob?: Blob;
  }> {
    let filename = "";

    if (action === "docx") {
      filename = await generateDocx(request);
    } else if (action === "xlsx") {
      filename = await generateXlsx(request);
    }

    if (filename) {
      const blob = await downloadFile(filename);
      return { filename, blob };
    }

    return { filename: "" };
  }

  static downloadFile(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
}
