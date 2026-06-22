const state = { papers: [], topic: "all", sort: "score", date: null, query: "" };
const topicLabels = { pretraining: "预训练", "post-training": "后训练", reasoning: "推理扩展", serving: "推理系统", efficiency: "高效推理" };

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[character]));

function currentPapers() {
  const query = state.query.trim().toLocaleLowerCase();
  return state.papers.filter((paper) => {
    const topicMatches = state.topic === "all" || Object.hasOwn(paper.topic_scores || {}, state.topic);
    const haystack = `${paper.title} ${paper.abstract} ${(paper.authors || []).join(" ")} ${Object.keys(paper.topic_scores || {}).join(" ")}`.toLocaleLowerCase();
    return topicMatches && (!query || haystack.includes(query));
  }).sort((left, right) => state.sort === "updated" ? right.updated.localeCompare(left.updated) : right.score - left.score);
}

function render() {
  const papers = currentPapers();
  const grid = document.querySelector("#papers");
  const template = document.querySelector("#paper-template");
  grid.replaceChildren();
  papers.forEach((paper) => {
    const node = template.content.cloneNode(true);
    const card = node.querySelector(".paper-card");
    const topics = Object.keys(paper.topic_scores || {});
    card.querySelector(".topic").textContent = topics.map((topic) => topicLabels[topic] || topic).join(" / ") || "人工复核";
    card.querySelector(".score span").textContent = paper.score;
    card.querySelector("h2").textContent = paper.title;
    card.querySelector(".authors").textContent = (paper.authors || []).slice(0, 3).join(" · ");
    const labels = { relevance: "匹配", quality: "质量", novelty: "新颖", practical: "实用", credibility: "可信", personal: "偏好" };
    card.querySelector(".breakdown").innerHTML = Object.entries(paper.score_breakdown || {}).map(([name, value]) => `<span><b>${Math.round(value)}</b>${labels[name] || name}</span>`).join("");
    const confidence = Number(paper.confidence || 0);
    card.querySelector(".confidence").textContent = confidence ? `置信度 ${confidence >= 75 ? "高" : confidence >= 50 ? "中" : "低"} · ${Math.round(confidence)}` : "";
    card.querySelector(".abstract").textContent = paper.summary_zh || paper.abstract;
    const risk = card.querySelector(".risk");
    if (paper.risk_zh) { risk.hidden = false; risk.textContent = `注意：${paper.risk_zh}`; }
    card.querySelector(".paper-link").href = paper.pdf_url || paper.abs_url;
    card.querySelector(".reasons").innerHTML = (paper.score_reasons || []).map((reason) => `<span class="reason">${escapeHtml(reason)}</span>`).join("");
    const savedFeedback = localStorage.getItem(`paper-feedback:${paper.paper_id}`);
    card.querySelectorAll("button").forEach((button) => {
      const selected = savedFeedback === button.dataset.feedback;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-pressed", String(selected));
      button.addEventListener("click", () => sendFeedback(paper.paper_id, button.dataset.feedback, button));
    });
    grid.append(node);
  });
  document.querySelector("#paper-count").textContent = papers.length === state.papers.length ? `${papers.length} 篇入选` : `${papers.length} / ${state.papers.length} 篇`;
  const empty = document.querySelector("#empty");
  empty.textContent = state.query || state.topic !== "all" ? "没有符合当前筛选的论文。换个关键词或查看全部主题。" : "这期没有新的入选论文；历史推荐仍可在“全部历史”中查看。";
  empty.hidden = papers.length !== 0;
}

function rebuildTopicFilter() {
  const select = document.querySelector("#topic-filter");
  select.replaceChildren(new Option("全部主题", "all"));
  [...new Set(state.papers.flatMap((paper) => Object.keys(paper.topic_scores || {})))].sort().forEach((topic) => select.add(new Option(topicLabels[topic] || topic, topic)));
  state.topic = "all";
  select.value = "all";
}

async function loadEdition(date) {
  const path = date === "all" ? "data/catalog.json" : date ? `data/${date}.json` : "data/latest.json";
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`Daily paper data is unavailable: ${path}`);
  const payload = await response.json();
  state.date = payload.date;
  state.papers = payload.papers || [];
  document.querySelector("#edition").textContent = date === "all" ? "ALL EDITIONS / PAPER ARCHIVE" : `${payload.date} / DAILY EDITION`;
  const candidateCount = Number(payload.candidate_count || 0);
  document.querySelector("#summary").textContent = date === "all"
    ? `在 ${state.papers.length} 篇历史推荐中检索值得重访的方法。`
    : candidateCount
      ? `从 ${candidateCount} 篇未见候选中筛出 ${state.papers.length} 篇，比较研究质量、新颖性与实用价值。`
      : `从 ${state.papers.length} 篇入选论文中，比较匹配度、研究质量、新颖性与实用价值。`;
  rebuildTopicFilter();
  render();
}

function sendFeedback(paperId, action, button) {
  button.parentElement.querySelectorAll("button").forEach((item) => { item.classList.remove("is-selected"); item.setAttribute("aria-pressed", "false"); });
  button.classList.add("is-selected");
  button.setAttribute("aria-pressed", "true");
  localStorage.setItem(`paper-feedback:${paperId}`, action);
}

async function init() {
  const historyResponse = await fetch("data/history.json", { cache: "no-store" });
  const history = historyResponse.ok ? await historyResponse.json() : [];
  const dateSelect = document.querySelector("#date-filter");
  dateSelect.add(new Option("全部历史", "all"));
  [...history].sort().reverse().forEach((date) => dateSelect.add(new Option(date, date)));
  dateSelect.addEventListener("change", async (event) => {
    dateSelect.disabled = true;
    try { await loadEdition(event.target.value); }
    finally { dateSelect.disabled = false; }
  });
  document.querySelector("#topic-filter").addEventListener("change", (event) => { state.topic = event.target.value; render(); });
  document.querySelector("#sort-filter").addEventListener("change", (event) => { state.sort = event.target.value; render(); });
  document.querySelector("#search-input").addEventListener("input", (event) => { state.query = event.target.value; render(); });
  await loadEdition(history.at(-1) || null);
  if (state.date && [...dateSelect.options].some((option) => option.value === state.date)) dateSelect.value = state.date;
}

init().catch((error) => { document.querySelector("#summary").textContent = "尚未生成日报。请先运行采集任务。"; console.error(error); });
