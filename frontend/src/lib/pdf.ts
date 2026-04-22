import type { SlideCard, TranscriptSection } from "./types";

const API_URL = (
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : "http://localhost:8000"
).replace(/\/+$/, "");

function resolveImageUrl(imageRef: string): string {
  if (!imageRef || imageRef.startsWith("[")) return "";
  if (imageRef.startsWith("http")) return imageRef;
  if (imageRef.startsWith("/")) return imageRef;
  if (imageRef.startsWith("screenshots/")) {
    const filename = imageRef.replace("screenshots/", "");
    return `${API_URL}/api/screenshots/${filename}`;
  }
  return `/${imageRef}`;
}

function cleanNarrative(text: string): string {
  // Strip "Slide X " prefix the generator sometimes prepends
  let t = text.replace(/^Slide \d+\s+/m, "");
  // Strip raw === SLIDE === blocks (generator failure fallback — extract exam tips only)
  // Strip raw === SLIDE === blocks line by line
  t = t.split("\n").filter(line => !line.startsWith("=== SLIDE ===")).join("\n");
  // Collapse leftover blank lines
  t = t.replace(/\n{3,}/g, "\n\n").trim();
  return t;
}

function stripMarkdownToHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*([\s\S]+?)\*\*/g, '<strong style="color:#E8450A">$1</strong>')
    .replace(/(?<!\*)\*(?!\*)([\s\S]+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>")
    .replace(/~~([\s\S]+?)~~/g, '<del style="opacity:0.4">$1</del>');
}

function openPrintWindow(html: string) {
  const win = window.open("", "_blank");
  if (win) {
    win.document.write(html);
    win.document.close();
  }
}

/** Slides PDF — anatomy-prof style compact grid, 2 per row, all a/b/c cards */
export function downloadSlidesPDF(
  slides: SlideCard[],
  _transcript: TranscriptSection[],
  sessionName: string
) {
  const cardsHtml = slides
    .map((card) => {
      const imgUrl = resolveImageUrl(card.image_ref);
      // object-fit:contain + max-height so portrait images don't blow up the cell
      const imgHtml = imgUrl
        ? `<div style="background:#f8f8f8;border-radius:6px;overflow:hidden;margin-bottom:8px;display:flex;align-items:center;justify-content:center;min-height:80px;">
             <img src="${imgUrl}" alt="${card.title}"
               style="width:100%;max-height:300px;object-fit:contain;display:block;" />
           </div>`
        : "";

      const bulletsHtml =
        card.bullet_points.length > 0
          ? `<ul style="margin:0 0 8px 0;padding-left:16px;">${card.bullet_points
              .map(
                (bp) =>
                  `<li style="margin-bottom:3px;font-size:11.5px;line-height:1.5;">${stripMarkdownToHtml(bp)}</li>`
              )
              .join("")}</ul>`
          : "";

      const examTipHtml = card.exam_tip
        ? `<div style="background:#fff3ec;border-left:3px solid #E8450A;padding:6px 10px;border-radius:0 4px 4px 0;font-size:11px;margin-top:6px;">
             <strong style="color:#E8450A;">Exam tip:</strong> ${stripMarkdownToHtml(card.exam_tip)}
           </div>`
        : "";

      return `
        <div style="break-inside:avoid;border:1px solid #e8e8e8;border-radius:8px;padding:12px;background:#fff;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
            <span style="background:#fff3ec;color:#E8450A;font-size:10px;font-weight:700;padding:1px 7px;border-radius:4px;font-family:monospace;white-space:nowrap;">${card.slide_id}</span>
            <span style="font-size:12px;font-weight:600;color:#1a1a1a;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${card.title}</span>
            <span style="font-size:10px;color:${card.ei_percent >= 70 ? "#E8450A" : "#aaa"};white-space:nowrap;">EI ${card.ei_percent}%</span>
          </div>
          ${imgHtml}
          ${bulletsHtml}
          ${examTipHtml}
        </div>`;
    })
    .join("");

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${sessionName} — Slides</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      color: #1a1a1a; background: #fff;
      padding: 32px 48px; max-width: 700px; margin: 0 auto;
    }
    .title { font-size: 20px; font-weight: 800; margin-bottom: 4px; }
    .subtitle { font-size: 12px; color: #888; margin-bottom: 28px; padding-bottom: 16px; border-bottom: 2px solid #E8450A; }
    .print-bar {
      position: fixed; top: 0; left: 0; right: 0;
      background: #fff; border-bottom: 1px solid #e8e8e8;
      padding: 10px 24px; display: flex; align-items: center; gap: 16px;
      font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
      z-index: 100;
    }
    .print-bar button {
      background: #E8450A; color: #fff; border: none; border-radius: 7px;
      padding: 7px 18px; font-size: 13px; font-weight: 600; cursor: pointer;
    }
    .print-bar span { font-size: 12px; color: #888; }
    .content { padding-top: 52px; }
    .grid {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    @media print {
      .print-bar { display: none; }
      .content { padding-top: 0; }
      body { padding: 20px 24px; }
      .grid { gap: 12px; }
    }
  </style>
</head>
<body>
  <div class="print-bar">
    <button onclick="window.print()">Save as PDF</button>
    <span>File → Print → Save as PDF (or Ctrl+P)</span>
  </div>
  <div class="content">
    <div class="title">${sessionName}</div>
    <div class="subtitle">Lecture Slides — generated by Klare</div>
    <div class="grid">
      ${cardsHtml || "<p style='color:#888;'>No slides available.</p>"}
    </div>
  </div>
</body>
</html>`;

  openPrintWindow(html);
}

/** Notes PDF — clean prose, each heading shows slide reference */
export function downloadTranscriptPDF(
  transcript: TranscriptSection[],
  sessionName: string
) {
  const sectionsHtml = transcript
    .map((section, i) => {
      const cleaned = cleanNarrative(section.narrative);
      // Skip sections that have no real content after cleaning
      if (!cleaned) return "";

      const paragraphs = cleaned
        .split("\n\n")
        .map((para) => {
          const isStruck = para.startsWith("~~") && para.endsWith("~~");
          const clean = isStruck ? para.slice(2, -2) : para;
          const html = stripMarkdownToHtml(clean);
          return `<p style="margin-bottom:13px;line-height:1.8;font-size:14px;color:${isStruck ? "#aaa" : "#1a1a1a"};">${isStruck ? `<del>${html}</del>` : html}</p>`;
        })
        .join("");

      return `
        <div style="margin-bottom:28px;${i > 0 ? "margin-top:28px;" : ""}">
          <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
            <h2 style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:16px;font-weight:700;color:#1a1a1a;">${section.title}</h2>
            <span style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:10px;color:#aaa;white-space:nowrap;">Slide ${section.slide_number}</span>
            <span style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:10px;color:${section.ei_percent >= 70 ? "#E8450A" : "#bbb"};background:${section.ei_percent >= 70 ? "#fff3ec" : "#f5f5f5"};padding:1px 7px;border-radius:10px;white-space:nowrap;">EI ${section.ei_percent}%</span>
          </div>
          ${paragraphs}
        </div>`;
    })
    .filter(Boolean)
    .join("");

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${sessionName} — Notes</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: Georgia, 'Times New Roman', serif;
      color: #1a1a1a; background: #fff;
      padding: 48px 64px; max-width: 700px; margin: 0 auto;
    }
    .print-bar {
      position: fixed; top: 0; left: 0; right: 0;
      background: #fff; border-bottom: 1px solid #e8e8e8;
      padding: 10px 24px; display: flex; align-items: center; gap: 16px;
      font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
      z-index: 100;
    }
    .print-bar button {
      background: #E8450A; color: #fff; border: none; border-radius: 7px;
      padding: 7px 18px; font-size: 13px; font-weight: 600; cursor: pointer;
    }
    .print-bar span { font-size: 12px; color: #888; }
    .content { padding-top: 52px; }
    .doc-title { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; font-size: 20px; font-weight: 800; margin-bottom: 4px; }
    .subtitle { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; font-size: 12px; color: #888; margin-bottom: 32px; padding-bottom: 14px; border-bottom: 2px solid #E8450A; }
    @media print {
      .print-bar { display: none; }
      .content { padding-top: 0; }
      body { padding: 20px 32px; }
    }
  </style>
</head>
<body>
  <div class="print-bar">
    <button onclick="window.print()">Save as PDF</button>
    <span>File → Print → Save as PDF (or Ctrl+P)</span>
  </div>
  <div class="content">
    <div class="doc-title">${sessionName}</div>
    <div class="subtitle">Lecture Notes — generated by Klare</div>
    ${sectionsHtml || "<p style='color:#888;'>No notes available.</p>"}
  </div>
</body>
</html>`;

  openPrintWindow(html);
}
