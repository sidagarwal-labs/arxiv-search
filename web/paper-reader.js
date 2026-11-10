import { citationURL } from "./paper-api.js";

const $ = selector => document.querySelector(selector);

function paperIdentity(paper) {
  if (!/^\d{4}\.\d{4,5}$/.test(paper?.arxiv_id ?? "")) return null;
  if (paper.version == null) return paper.arxiv_id;
  if (!Number.isSafeInteger(paper.version) || paper.version < 1) return null;
  return `${paper.arxiv_id}v${paper.version}`;
}

export function sourceURL(paper) {
  const identity = paperIdentity(paper);
  return identity ? `https://arxiv.org/abs/${identity}` : null;
}

export function pdfURL(paper) {
  const identity = paperIdentity(paper);
  return identity ? `https://arxiv.org/pdf/${identity}` : null;
}

export function setPaperView(conversation, view) {
  conversation.view = view === "discuss" ? "discuss" : "read";
  $("#paper-workspace").setAttribute("data-view", conversation.view);
  $("#paper-read-tab").setAttribute("aria-pressed", String(conversation.view === "read"));
  $("#paper-discuss-tab").setAttribute("aria-pressed", String(conversation.view === "discuss"));
}

function paragraph(text, className = "") {
  const p = document.createElement("p");
  p.textContent = text;
  p.className = className;
  return p;
}

function externalLink(href, text) {
  const link = document.createElement("a");
  link.href = href;
  link.textContent = text;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  return link;
}

export function renderReader(conversation) {
  const paper = conversation.paper;
  setPaperView(conversation, conversation.view);
  const body = $("#paper-reader-body");
  const signature = JSON.stringify([paper.arxiv_id, paper.version, paper.coverage,
    paper.outline, conversation.viewerUnavailable, conversation.real]);
  // Keep the native viewer mounted during ordinary chat updates.
  if (conversation.readerSignature === signature && body.dataset.paper === paper.arxiv_id) return;
  conversation.readerSignature = signature;
  body.dataset.paper = paper.arxiv_id;
  body.replaceChildren();
  const pdf = pdfURL(paper);
  const toggle = $("#paper-viewer-toggle");
  toggle.hidden = !pdf;
  toggle.textContent = conversation.viewerUnavailable ? "Restore PDF viewer" : "PDF not displaying?";
  if (!pdf) {
    body.append(paragraph("Select a paper from the search results to read its original PDF. No document is selected in this interface demonstration."));
    return;
  }
  const toolbar = document.createElement("div");
  toolbar.className = "reader-toolbar";
  toolbar.append(paragraph(conversation.real
    ? "Ask about this paper in Discuss" : "AI not connected · reading only", "reader-status"));
  toolbar.append(externalLink(pdf, "Open PDF ↗"));
  body.append(toolbar);
  const details = document.createElement("details");
  details.className = "reader-details";
  const summary = document.createElement("summary");
  summary.textContent = "Document & AI details";
  details.append(summary, paragraph(conversation.real
    ? "The AI reads the paper's text separately from this viewer. The note at the top of Discuss shows what it can see; figure images are not included."
    : "AI coverage: none. Viewing this PDF does not analyze it. AI discussion is not connected in this preview."));
  details.append(paragraph(paper.version == null
    ? "arXiv will serve its latest PDF. Its revision may differ from the indexed abstract."
    : `PDF revision: v${paper.version}.`));
  details.append(paragraph("The PDF loads directly from arxiv.org. Use your browser's PDF controls for pages, zoom and download. If the viewer stays blank, use PDF not displaying? or Open PDF."));
  for (const section of paper.outline ?? []) {
    const target = citationURL(section.href, paper);
    if (target) details.append(externalLink(target, section.label || section.id));
  }
  body.append(details);
  if (conversation.viewerUnavailable) {
    body.append(paragraph("Embedded viewer unavailable. Your browser or the source may block embedded PDFs. Use Open PDF above and keep the discussion here. No alternate source is fetched automatically.", "reader-fallback-title"));
  } else {
    const frame = document.createElement("iframe");
    frame.className = "paper-pdf-frame";
    frame.title = `Original PDF: ${paper.title}`;
    frame.referrerPolicy = "no-referrer";
    frame.src = pdf;
    body.append(frame);
  }
}
