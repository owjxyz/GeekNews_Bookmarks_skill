import { spawnSync } from "node:child_process";

const HELPER = "/home/lukeoh/.agents/skills/hada-bookmarks/scripts/hada_bookmark.py";
const PAGE_SIZE = 5;
const CALLBACK_NAMESPACE = "hada_bookmarks";

const emptyConfigSchema = {
  safeParse(value) {
    if (value === undefined) return { success: true, data: undefined };
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return { success: false, error: { issues: [{ path: [], message: "expected config object" }] } };
    }
    return { success: true, data: value };
  },
  jsonSchema: { type: "object", additionalProperties: true }
};

function runHelper(args) {
  const result = spawnSync("python3", [HELPER, ...args], {
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    const stderr = result.stderr?.trim();
    const stdout = result.stdout?.trim();
    throw new Error(stderr || stdout || `hada_bookmark.py exited with status ${result.status}`);
  }
  return result.stdout.trim();
}

function loadBookmarks() {
  const output = runHelper(["list", "--json"]);
  const parsed = JSON.parse(output || "[]");
  return Array.isArray(parsed) ? parsed : [];
}

function loadBookmarkDetail(query) {
  const output = runHelper(["show", String(query), "--json"]);
  return JSON.parse(output || "{}");
}

function deleteBookmark(query) {
  const output = runHelper(["delete", String(query), "--json"]);
  return JSON.parse(output || "{}");
}

function plainText(value) {
  return String(value ?? "");
}

function truncate(value, max) {
  const text = String(value ?? "").trim();
  if (text.length <= max) return text;
  return `${text.slice(0, Math.max(0, max - 1)).trimEnd()}…`;
}

function cleanSummaryChunk(value) {
  return String(value ?? "")
    .replace(/^TL;DR\s*/i, "")
    .replace(/^[\s•\-–—:：/]+/, "")
    .replace(/[\s/]+$/, "")
    .trim();
}

function removeNoisyDetails(value) {
  return String(value ?? "")
    .replace(/\([^)]{28,}\)/g, "")
    .replace(/\s+—\s+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function splitSummaryChunks(value) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return [];

  const markerPattern = /(광고 대행사가|명령 실행 시|플랫폼별|v\d+(?:\.\d+)?에서|결과물은|일반적으로|문제|해결|특징|활용|효과|결과|장점|단점|예시|지원|구성|작동|실행 시)/g;
  return text
    .replace(markerPattern, "\n$1")
    .split(/\n+|[。.!?]\s+/)
    .map((chunk) => cleanSummaryChunk(removeNoisyDetails(chunk)))
    .filter(Boolean);
}

function sentenceFromChunk(chunk, maxChars = 125) {
  let text = cleanSummaryChunk(removeNoisyDetails(chunk));
  if (text.length > maxChars) {
    let cut = Math.max(
      text.lastIndexOf(" ", maxChars),
      text.lastIndexOf(",", maxChars),
      text.lastIndexOf("·", maxChars),
      text.lastIndexOf("/", maxChars)
    );
    if (cut < Math.floor(maxChars * 0.65)) cut = maxChars;
    text = text.slice(0, cut).trim();
  }
  text = text.replace(/[.…]+$/, "");
  if (!/[.!?。]$/.test(text)) text = `${text}.`;
  return text;
}

function summarizeForDetail(value, maxSentences = 5) {
  const chunks = splitSummaryChunks(value);
  if (chunks.length === 0) return "";

  const selected = [];
  const seen = new Set();
  for (const chunk of chunks) {
    if (selected.length >= maxSentences) break;
    if (/^\d+개\(/.test(chunk)) continue;
    if (/→|왜 리뷰 하네스에 페르소나 깊이가 필요한가/.test(chunk)) continue;
    const sentence = sentenceFromChunk(chunk);
    const key = sentence.slice(0, 32);
    if (seen.has(key)) continue;
    seen.add(key);
    selected.push(sentence);
  }
  return selected.join(" ");
}

function resolvePage(rawPage, totalPages) {
  const page = Number.parseInt(String(rawPage ?? "1"), 10);
  if (!Number.isFinite(page) || page < 1) return 1;
  return Math.min(page, Math.max(1, totalPages));
}

function makeButton(text, callbackData) {
  return { text, callback_data: callbackData };
}

function renderList(page = 1) {
  const bookmarks = loadBookmarks();
  if (bookmarks.length === 0) {
    return {
      text: "📚 저장된 Hada 북마크가 아직 없습니다.",
      buttons: []
    };
  }

  const totalPages = Math.max(1, Math.ceil(bookmarks.length / PAGE_SIZE));
  const currentPage = resolvePage(page, totalPages);
  const start = (currentPage - 1) * PAGE_SIZE;
  const items = bookmarks.slice(start, start + PAGE_SIZE);

  const lines = [
    "📚 Hada 북마크",
    "",
    "보고 싶은 글 제목을 눌러주세요."
  ];
  if (totalPages > 1) lines.push(`페이지 ${currentPage}/${totalPages}`);

  const buttons = items.map((item, idx) => {
    const number = start + idx + 1;
    const title = truncate(item.title || item.id || `북마크 ${number}`, 48);
    return [makeButton(title, `${CALLBACK_NAMESPACE}:show:${number}`)];
  });

  if (totalPages > 1) {
    const nav = [];
    if (currentPage > 1) nav.push(makeButton("‹ 이전", `${CALLBACK_NAMESPACE}:list:${currentPage - 1}`));
    if (currentPage < totalPages) nav.push(makeButton("다음 ›", `${CALLBACK_NAMESPACE}:list:${currentPage + 1}`));
    if (nav.length > 0) buttons.push(nav);
  }

  return { text: lines.join("\n"), buttons };
}

function renderDetail(query) {
  const detail = loadBookmarkDetail(query);
  const title = plainText(detail.title || `북마크 ${query}`);
  const topicUrl = detail.topicUrl || "";
  const sourceUrl = detail.url && detail.url !== detail.topicUrl ? detail.url : "";
  const summary = detail.summary ? plainText(summarizeForDetail(detail.summary, 5)) : "";

  const lines = [
    "━━━━━━━━━━━━━━",
    `📌 ${title}`
  ];
  if (topicUrl) lines.push(`🔗 ${plainText(topicUrl)}`);
  if (sourceUrl) lines.push(`원문: ${plainText(sourceUrl)}`);
  if (summary) lines.push("", summary);

  const deleteKey = detail.id || query;

  return {
    text: lines.join("\n"),
    buttons: [
      [
        makeButton("← 목록", `${CALLBACK_NAMESPACE}:list:1`),
        makeButton("🗑 삭제", `${CALLBACK_NAMESPACE}:delete:${deleteKey}`)
      ]
    ]
  };
}

function renderDeleteConfirm(query) {
  const detail = loadBookmarkDetail(query);
  const title = plainText(detail.title || `북마크 ${query}`);
  const deleteKey = detail.id || query;
  return {
    text: [
      "이 북마크를 삭제할까요?",
      "",
      `🗑 ${title}`
    ].join("\n"),
    buttons: [
      [makeButton("취소", `${CALLBACK_NAMESPACE}:show:${deleteKey}`)],
      [makeButton("삭제 확인", `${CALLBACK_NAMESPACE}:delete_confirm:${deleteKey}`)]
    ]
  };
}

function renderDeleted(query) {
  const removed = deleteBookmark(query);
  const title = plainText(removed.title || `북마크 ${query}`);
  const topicUrl = removed.topicUrl || "";
  const lines = [
    "북마크를 삭제했습니다.",
    "",
    "━━━━━━━━━━━━━━",
    `🗑 ${title}`
  ];
  if (topicUrl) lines.push(`🔗 ${plainText(topicUrl)}`);
  return {
    text: lines.join("\n"),
    buttons: [[makeButton("← 목록", `${CALLBACK_NAMESPACE}:list:1`)]]
  };
}

function withTelegramButtons(rendered) {
  return {
    text: rendered.text,
    channelData: {
      telegram: {
        buttons: rendered.buttons
      }
    }
  };
}

async function handleCommand(ctx) {
  const args = ctx.args?.trim();
  try {
    if (args) return withTelegramButtons(renderDetail(args));
    return withTelegramButtons(renderList(1));
  } catch (error) {
    return { text: `⚠️ Hada 북마크를 불러오지 못했습니다: ${plainText(error.message || error)}` };
  }
}

async function handleInteractive(ctx) {
  const payload = String(ctx.callback?.payload ?? "").trim();
  const [action = "list", ...rest] = payload.split(":");
  try {
    if (action === "show") {
      const query = rest.join(":").trim();
      if (!query) return { handled: true };
      const rendered = renderDetail(query);
      await ctx.respond.editMessage({ text: rendered.text, buttons: rendered.buttons });
      return { handled: true };
    }
    if (action === "list") {
      const page = rest[0] || "1";
      const rendered = renderList(page);
      await ctx.respond.editMessage({ text: rendered.text, buttons: rendered.buttons });
      return { handled: true };
    }
    if (action === "delete") {
      const query = rest.join(":").trim();
      if (!query) return { handled: true };
      const rendered = renderDeleteConfirm(query);
      await ctx.respond.editMessage({ text: rendered.text, buttons: rendered.buttons });
      return { handled: true };
    }
    if (action === "delete_confirm") {
      const query = rest.join(":").trim();
      if (!query) return { handled: true };
      const rendered = renderDeleted(query);
      await ctx.respond.editMessage({ text: rendered.text, buttons: rendered.buttons });
      return { handled: true };
    }
    return { handled: true };
  } catch (error) {
    await ctx.respond.reply({ text: `⚠️ Hada 북마크를 처리하지 못했습니다: ${plainText(error.message || error)}` });
    return { handled: true };
  }
}

export default {
  id: "hada-bookmarks-telegram",
  name: "Hada Bookmarks Telegram UI",
  description: "Native Telegram inline command UI for saved Hada/GeekNews bookmarks.",
  kind: "command",
  configSchema: emptyConfigSchema,
  register(api) {
    api.registerCommand({
      name: "hada_bookmarks",
      description: "저장된 Hada/GeekNews 북마크를 Telegram 버튼으로 봅니다.",
      acceptsArgs: true,
      requireAuth: true,
      handler: handleCommand
    });

    api.registerInteractiveHandler({
      channel: "telegram",
      namespace: CALLBACK_NAMESPACE,
      handler: handleInteractive
    });
  }
};
