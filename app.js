// ============================================================
// SECTION 1 — GLOBAL STATE
// ============================================================
let allArticles = [];
let activeFilter = "all";
let activeMapCountry = null;
let searchQuery = "";
let map = null;
let mapMarkers = [];
let trendChart = null;
let doughnutChart = null;
let refreshTimer = null;
let countdownInterval = null;
let countdownSeconds = 60;
let currentSource = CONFIG.ACTIVE_SOURCE;
let mapSearchQuery = "";

// ============================================================
// SECTION 2 — COUNTRY DATA
// ============================================================
const COUNTRY_COORDS = {
  us: { coords: [37.09, -95.71], name: "United States" },
  gb: { coords: [55.37, -3.43], name: "United Kingdom" },
  in: { coords: [20.59, 78.96], name: "India" },
  cn: { coords: [35.86, 104.19], name: "China" },
  ru: { coords: [61.52, 105.31], name: "Russia" },
  de: { coords: [51.16, 10.45], name: "Germany" },
  fr: { coords: [46.22, 2.21], name: "France" },
  br: { coords: [-14.23, -51.92], name: "Brazil" },
  au: { coords: [-25.27, 133.77], name: "Australia" },
  ca: { coords: [56.13, -106.34], name: "Canada" },
  jp: { coords: [36.2, 138.25], name: "Japan" },
  za: { coords: [-30.55, 22.93], name: "South Africa" },
  ng: { coords: [9.08, 8.67], name: "Nigeria" },
  eg: { coords: [26.82, 30.8], name: "Egypt" },
  pk: { coords: [30.37, 69.34], name: "Pakistan" },
  ir: { coords: [32.42, 53.68], name: "Iran" },
  iq: { coords: [33.22, 43.67], name: "Iraq" },
  sy: { coords: [34.8, 38.99], name: "Syria" },
  ua: { coords: [48.37, 31.16], name: "Ukraine" },
  il: { coords: [31.04, 34.85], name: "Israel" },
  sa: { coords: [23.88, 45.07], name: "Saudi Arabia" },
  tr: { coords: [38.96, 35.24], name: "Turkey" },
  mx: { coords: [23.63, -102.55], name: "Mexico" },
  af: { coords: [33.93, 67.7], name: "Afghanistan" },
  et: { coords: [9.14, 40.48], name: "Ethiopia" },
  sd: { coords: [12.86, 30.21], name: "Sudan" },
  ly: { coords: [26.33, 17.22], name: "Libya" },
  ye: { coords: [15.55, 48.51], name: "Yemen" },
  kp: { coords: [40.33, 127.51], name: "North Korea" },
  mm: { coords: [21.91, 95.95], name: "Myanmar" },
  so: { coords: [5.15, 46.19], name: "Somalia" },
  ps: { coords: [31.95, 35.23], name: "Palestine" },
  lb: { coords: [33.85, 35.86], name: "Lebanon" }
};

// ============================================================
// SECTION 3 — PEACE SCORE ENGINE
// ============================================================
const CONFLICT_KEYWORDS = [
  "war", "attack", "bomb", "explosion", "killed", "dead", "death", "missile",
  "airstrike", "shooting", "violence", "riot", "clash", "conflict", "fighting",
  "troops", "invasion", "coup", "protest", "unrest", "crisis", "hostage",
  "terror", "terrorist", "genocide", "massacre", "casualties", "wounded",
  "destroyed", "refugee", "siege", "blockade", "sanctions", "nuclear",
  "chemical weapon", "ethnic cleansing", "displacement", "insurgency",
  "militant", "gunfire", "shelling", "artillery", "drone strike", "ambush",
  "kidnapping", "execution", "torture", "war crime", "famine", "starvation"
];

const PEACE_KEYWORDS = [
  "peace", "ceasefire", "agreement", "treaty", "diplomacy", "talks",
  "negotiation", "cooperation", "aid", "relief", "reconstruction",
  "democracy", "election", "vote", "freedom", "human rights",
  "development", "trade", "partnership", "alliance", "reconciliation",
  "dialogue", "humanitarian", "donation", "recovery", "stability",
  "truce", "resolution", "accord", "summit", "bilateral", "multilateral",
  "diplomatic", "mediation", "peacekeeping", "solidarity", "reform"
];

function calculatePeaceScore(title, description) {
  const text = ((title || "") + " " + (description || "")).toLowerCase();
  let score = 5;
  let conflictCount = 0;
  CONFLICT_KEYWORDS.forEach((kw) => { if (text.includes(kw)) conflictCount += 1; });
  score -= Math.min(conflictCount * 0.4, 4.5);

  let peaceCount = 0;
  PEACE_KEYWORDS.forEach((kw) => { if (text.includes(kw)) peaceCount += 1; });
  score += Math.min(peaceCount * 0.35, 4);

  const titleLower = (title || "").toLowerCase();
  if (CONFLICT_KEYWORDS.some((kw) => titleLower.includes(kw))) score -= 0.5;
  if (PEACE_KEYWORDS.some((kw) => titleLower.includes(kw))) score += 0.5;
  score = Math.max(0.1, Math.min(9.9, score));
  return Math.round(score * 10) / 10;
}

function classifyScore(score) {
  if (score >= 6.5) return { category: "PEACE", color: "#1D9E75", cls: "peace" };
  if (score >= 4.0) return { category: "NEUTRAL", color: "#888888", cls: "neutral" };
  return { category: "CONFLICT", color: "#E24B4A", cls: "conflict" };
}

// ============================================================
// SECTION 4 — API FETCHERS
// ============================================================
async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function normalizeCountry(raw, title = "") {
  if (!raw) return detectCountryFromText(title);
  const c = Array.isArray(raw) ? raw[0] : raw;
  const val = String(c || "").toLowerCase().trim();
  if (val.length === 2) return val;
  return detectCountryFromText(val || title);
}

async function fetchFromNewsData() {
  const cfg = CONFIG.APIs.newsdata;
  if (!cfg.enabled || !cfg.key || cfg.key.includes("YOUR_")) throw new Error("NewsData key not set");
  const url = `${cfg.url}?apikey=${cfg.key}&language=en&category=top&size=10`;
  const data = await fetchJSON(url);
  if (!data.results) throw new Error("NewsData: no results");
  return data.results.map((a) => ({
    title: a.title || "",
    description: a.description || "",
    source: a.source_id || "NewsData",
    country: normalizeCountry(a.country, a.title),
    pubDate: a.pubDate || new Date().toISOString(),
    link: a.link || "#",
    apiSource: "NewsData.io"
  }));
}

async function fetchFromGNews() {
  const cfg = CONFIG.APIs.gnews;
  if (!cfg.enabled || !cfg.key || cfg.key.includes("YOUR_")) throw new Error("GNews key not set");
  const url = `${cfg.url}?category=world&lang=en&max=10&apikey=${cfg.key}`;
  const data = await fetchJSON(url);
  if (!data.articles) throw new Error("GNews: no articles");
  return data.articles.map((a) => ({
    title: a.title || "",
    description: a.description || "",
    source: (a.source && a.source.name) || "GNews",
    country: detectCountryFromText(a.title || ""),
    pubDate: a.publishedAt || new Date().toISOString(),
    link: a.url || "#",
    apiSource: "GNews"
  }));
}

async function fetchFromNewsAPI() {
  const cfg = CONFIG.APIs.newsapi;
  if (!cfg.enabled || !cfg.key || cfg.key.includes("YOUR_")) throw new Error("NewsAPI key not set");
  const url = `${cfg.url}?category=general&language=en&pageSize=10&apiKey=${cfg.key}`;
  const data = await fetchJSON(url);
  if (!data.articles) throw new Error("NewsAPI: no articles");
  return data.articles.map((a) => ({
    title: a.title || "",
    description: a.description || "",
    source: (a.source && a.source.name) || "NewsAPI",
    country: detectCountryFromText(a.title || ""),
    pubDate: a.publishedAt || new Date().toISOString(),
    link: a.url || "#",
    apiSource: "NewsAPI"
  }));
}

async function fetchFromGuardian() {
  const cfg = CONFIG.APIs.guardian;
  if (!cfg.enabled || !cfg.key || cfg.key.includes("YOUR_")) throw new Error("Guardian key not set");
  const url = `${cfg.url}?section=world&show-fields=headline,trailText,bodyText&page-size=10&api-key=${cfg.key}`;
  const data = await fetchJSON(url);
  if (!data.response || !data.response.results) throw new Error("Guardian: no results");
  return data.response.results.map((a) => ({
    title: a.webTitle || "",
    description: a.fields?.trailText || a.fields?.bodyText?.slice(0, 220) || "",
    source: "The Guardian",
    country: detectCountryFromText(a.webTitle || ""),
    pubDate: a.webPublicationDate || new Date().toISOString(),
    link: a.webUrl || "#",
    apiSource: "The Guardian"
  }));
}

async function fetchFromMediastack() {
  const cfg = CONFIG.APIs.mediastack;
  if (!cfg.enabled || !cfg.key || cfg.key.includes("YOUR_")) throw new Error("Mediastack key not set");
  const url = `${cfg.url}?access_key=${cfg.key}&languages=en&categories=general,politics&limit=10`;
  const data = await fetchJSON(url);
  if (!data.data) throw new Error("Mediastack: no data");
  return data.data.map((a) => ({
    title: a.title || "",
    description: a.description || "",
    source: a.source || "Mediastack",
    country: normalizeCountry(a.country, a.title),
    pubDate: a.published_at || new Date().toISOString(),
    link: a.url || "#",
    apiSource: "Mediastack"
  }));
}

async function fetchFromCurrents() {
  const cfg = CONFIG.APIs.currents;
  if (!cfg.enabled || !cfg.key || cfg.key.includes("YOUR_")) throw new Error("Currents key not set");
  const url = `${cfg.url}?language=en&apiKey=${cfg.key}`;
  const data = await fetchJSON(url);
  if (!data.news) throw new Error("Currents: no news");
  return data.news.slice(0, 10).map((a) => ({
    title: a.title || "",
    description: a.description || "",
    source: a.author || "Currents",
    country: detectCountryFromText(a.title || ""),
    pubDate: a.published || new Date().toISOString(),
    link: a.url || "#",
    apiSource: "Currents"
  }));
}

async function fetchFromGDELT() {
  const query = "peace OR conflict OR war OR protest OR ceasefire OR diplomacy";
  const url = `${CONFIG.APIs.gdelt.url}?query=${encodeURIComponent(query)}&mode=artlist&maxrecords=30&format=json&sourcelang=english`;
  const data = await fetchJSON(url);
  if (!data.articles) throw new Error("GDELT: no articles");
  return data.articles.map((a) => ({
    title: a.title || "",
    description: "",
    source: a.domain || "GDELT",
    country: detectCountryFromText(a.title || ""),
    pubDate: formatGDELTDate(a.seendate) || new Date().toISOString(),
    link: a.url || "#",
    tone: a.socialimage ? "available" : "",
    location: "",
    apiSource: "GDELT"
  }));
}

async function fetchRssViaRss2Json(feedUrl) {
  const url = `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(feedUrl)}`;
  return fetchJSON(url);
}

async function fetchFromRSS() {
  const cfg = CONFIG.APIs.rss;
  if (!cfg.enabled) throw new Error("RSS disabled");
  const results = await Promise.allSettled(cfg.feeds.map((f) => fetchRssViaRss2Json(f.url)));
  let rows = [];
  results.forEach((res, idx) => {
    if (res.status !== "fulfilled") return;
    const sourceName = cfg.feeds[idx].name;
    const items = res.value.items || [];
    rows = rows.concat(items.slice(0, 10).map((item) => ({
      title: item.title || "",
      description: item.description || "",
      source: sourceName,
      country: detectCountryFromText(item.title || ""),
      pubDate: item.pubDate || new Date().toISOString(),
      link: item.link || "#",
      apiSource: `RSS:${sourceName}`
    })));
  });
  if (!rows.length) throw new Error("RSS: no items");
  return rows;
}

async function fetchFromAllSources() {
  const fetchers = [
    fetchFromGDELT,
    fetchFromRSS,
    fetchFromNewsData,
    fetchFromGNews,
    fetchFromGuardian,
    fetchFromCurrents,
    fetchFromNewsAPI,
    fetchFromMediastack
  ];
  const results = await Promise.allSettled(fetchers.map((f) => f()));
  let combined = [];
  results.forEach((r) => {
    if (r.status === "fulfilled") combined = combined.concat(r.value);
  });
  if (!combined.length) throw new Error("All sources failed");
  const dedup = new Map();
  combined.forEach((article) => {
    const key = (article.title || "").trim().toLowerCase();
    if (!key || dedup.has(key)) return;
    dedup.set(key, article);
  });
  return Array.from(dedup.values());
}

// ============================================================
// SECTION 5 — MAIN FETCH ORCHESTRATOR
// ============================================================
async function fetchLiveNews() {
  showLoading(true);
  showSourceStatus("Fetching...", "orange");

  const sourceOrder = currentSource === "all"
    ? ["all"]
    : [currentSource, "gdelt", "rss", "newsdata", "gnews", "guardian", "currents"];

  let rawArticles = null;
  let usedSource = null;

  for (const src of sourceOrder) {
    try {
      if (src === "all") rawArticles = await fetchFromAllSources();
      else if (src === "newsdata") rawArticles = await fetchFromNewsData();
      else if (src === "gnews") rawArticles = await fetchFromGNews();
      else if (src === "newsapi") rawArticles = await fetchFromNewsAPI();
      else if (src === "guardian") rawArticles = await fetchFromGuardian();
      else if (src === "mediastack") rawArticles = await fetchFromMediastack();
      else if (src === "currents") rawArticles = await fetchFromCurrents();
      else if (src === "gdelt") rawArticles = await fetchFromGDELT();
      else if (src === "rss") rawArticles = await fetchFromRSS();
      usedSource = src;
      break;
    } catch (err) {
      console.warn(`Source ${src} failed:`, err.message);
      if (!CONFIG.AUTO_FALLBACK) break;
    }
  }

  if (!rawArticles || !rawArticles.length) {
    rawArticles = FALLBACK_ARTICLES;
    usedSource = "fallback";
    showErrorToast("Live APIs unavailable. Showing sample data.");
  }

  allArticles = rawArticles.map((a) => {
    const score = calculatePeaceScore(a.title, a.description);
    const cls = classifyScore(score);
    return { ...a, score, ...cls };
  });

  renderNewsFeed(applyFilters());
  updateMetrics(allArticles);
  updateChart(allArticles);
  updateMapMarkers(allArticles);
  updateTimestamp();
  showSourceStatus(`✓ ${CONFIG.APIs[usedSource]?.name || usedSource} · ${allArticles.length} articles`, "green");
  document.getElementById("feed-source-label").textContent = `${CONFIG.APIs[usedSource]?.name || "Sample"} · Auto-classified`;

  showLoading(false);
  resetCountdown();
}

// ============================================================
// SECTION 6 — RENDER NEWS FEED
// ============================================================
function renderNewsFeed(articles) {
  const container = document.getElementById("news-feed");
  if (!articles || !articles.length) {
    container.innerHTML = '<div class="empty-state">No articles match your filter.</div>';
    return;
  }
  container.innerHTML = articles.slice(0, CONFIG.MAX_ARTICLES).map((a) => `
    <div class="news-item" onclick="window.open('${a.link}','_blank')">
      <div class="news-header">
        <span class="badge badge-${a.cls}">${a.category}</span>
        <span class="news-time">${timeAgo(a.pubDate)}</span>
      </div>
      <div class="news-headline">${truncate(a.title, 90)}</div>
      <div class="news-meta">${a.source} · ${(a.country || "global").toUpperCase()}
        ${a.apiSource ? `<span class="api-tag">via ${a.apiSource}</span>` : ""}
      </div>
      <div class="score-row">
        <div class="score-bar-bg">
          <div class="score-bar-fill" style="width:${a.score * 10}%;background:${a.color}"></div>
        </div>
        <span class="score-num" style="color:${a.color}">${a.score}</span>
      </div>
    </div>
  `).join("");
}

// ============================================================
// SECTION 7 — FILTERS & SEARCH
// ============================================================
function applyFilters() {
  let result = [...allArticles];
  if (activeMapCountry) result = result.filter((a) => a.country === activeMapCountry);
  if (activeFilter !== "all") result = result.filter((a) => a.cls === activeFilter);
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    result = result.filter((a) => a.title.toLowerCase().includes(q) || a.source.toLowerCase().includes(q));
  }
  return result;
}

function setFilter(f, btn) {
  activeFilter = f;
  document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  renderNewsFeed(applyFilters());
}

function filterNewsFeed() {
  searchQuery = document.getElementById("search-input").value;
  renderNewsFeed(applyFilters());
}

function clearMapFilter() {
  activeMapCountry = null;
  document.getElementById("map-filter-bar").style.display = "none";
  mapMarkers.forEach((m) => m.setStyle({ weight: 1.5, color: m.options.fillColor }));
  renderNewsFeed(applyFilters());
}

// ============================================================
// SECTION 8 — METRICS UPDATE
// ============================================================
function updateMetrics(articles) {
  const total = articles.length;
  const peaceArr = articles.filter((a) => a.cls === "peace");
  const conflArr = articles.filter((a) => a.cls === "conflict");
  const avgScore = total > 0 ? (articles.reduce((s, a) => s + a.score, 0) / total).toFixed(1) : "--";

  const gpiEl = document.getElementById("metric-gpi");
  animateValue(gpiEl, avgScore);
  gpiEl.style.color = avgScore >= 6 ? "#1D9E75" : avgScore >= 4 ? "#EF9F27" : "#E24B4A";

  animateValue(document.getElementById("metric-articles"), total);
  animateValue(document.getElementById("metric-conflicts"), conflArr.length);
  animateValue(document.getElementById("metric-peace"), peaceArr.length);

  const sources = [...new Set(articles.map((a) => a.apiSource).filter(Boolean))];
  document.getElementById("metric-articles-sub").textContent = sources.length ? `from ${sources.join(", ")}` : "Last fetch";
}

function animateValue(el, newVal) {
  el.textContent = newVal;
  el.classList.remove("flash");
  void el.offsetWidth;
  el.classList.add("flash");
}

// ============================================================
// SECTION 9 — CHART.JS CHARTS
// ============================================================
function updateChart(articles) {
  const data = articles.slice(0, 20);
  const labels = data.map((_, i) => i + 1);
  const scores = data.map((a) => a.score);
  const colors = data.map((a) => a.color);

  if (trendChart) trendChart.destroy();
  const ctx = document.getElementById("trendChart").getContext("2d");
  trendChart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets: [{ data: scores, backgroundColor: colors, borderRadius: 4, borderSkipped: false }] },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: "#333" }, ticks: { color: "#666", font: { size: 10 } } },
        y: { min: 0, max: 10, grid: { color: "#333" }, ticks: { color: "#666", font: { size: 10 } } }
      },
      animation: { duration: 400 }
    }
  });

  const peace = articles.filter((a) => a.cls === "peace").length;
  const neutral = articles.filter((a) => a.cls === "neutral").length;
  const conflict = articles.filter((a) => a.cls === "conflict").length;
  const total = articles.length || 1;
  document.getElementById("peace-pct").textContent = `${Math.round(peace / total * 100)}%`;
  document.getElementById("neutral-pct").textContent = `${Math.round(neutral / total * 100)}%`;
  document.getElementById("conflict-pct").textContent = `${Math.round(conflict / total * 100)}%`;

  if (doughnutChart) doughnutChart.destroy();
  const dCtx = document.getElementById("doughnutChart").getContext("2d");
  doughnutChart = new Chart(dCtx, {
    type: "doughnut",
    data: {
      labels: ["Peace", "Neutral", "Conflict"],
      datasets: [{ data: [peace, neutral, conflict], backgroundColor: ["#1D9E75", "#888888", "#E24B4A"], borderWidth: 0 }]
    },
    options: { responsive: false, cutout: "65%", plugins: { legend: { display: false } }, animation: { duration: 400 } }
  });
}

// ============================================================
// SECTION 10 — LEAFLET MAP
// ============================================================
function initMap() {
  map = L.map("map", { zoomControl: true, scrollWheelZoom: false });
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { attribution: "© CartoDB", maxZoom: 18 }).addTo(map);
  map.setView([20, 10], 2);
}

function updateMapMarkers(articles) {
  mapMarkers.forEach((m) => map.removeLayer(m));
  mapMarkers = [];
  const byCountry = {};
  articles.forEach((a) => {
    const cc = (a.country || "us").toLowerCase();
    if (!byCountry[cc]) byCountry[cc] = [];
    byCountry[cc].push(a);
  });

  Object.entries(byCountry).forEach(([cc, arts]) => {
    const info = COUNTRY_COORDS[cc];
    if (!info) return;
    const avg = arts.reduce((s, a) => s + a.score, 0) / arts.length;
    const score = Math.round(avg * 10) / 10;
    const cls = classifyScore(score);
    const marker = L.circleMarker(info.coords, {
      radius: Math.min(16, 8 + arts.length),
      fillColor: cls.color,
      fillOpacity: 0.75,
      color: cls.color,
      weight: 1.5
    });
    marker.bindPopup(`
      <b>${info.name}</b><br>
      Peace Score: <b style="color:${cls.color}">${score}</b><br>
      Articles: ${arts.length}<br>
      Status: <b>${cls.category}</b>
    `);
    marker.on("click", () => {
      activeMapCountry = cc;
      document.getElementById("map-filter-bar").style.display = "flex";
      document.getElementById("map-filter-label").textContent = `Showing: ${info.name}`;
      mapMarkers.forEach((m) => m.setStyle({ weight: 1.5, color: m.options.fillColor }));
      marker.setStyle({ weight: 3, color: "#ffffff" });
      const input = document.getElementById("country-search-input");
      if (input) input.value = info.name;
      renderNewsFeed(applyFilters());
    });
    marker._countryCode = cc;
    marker.addTo(map);
    mapMarkers.push(marker);
  });
}

// ============================================================
// SECTION 11 — SOURCE SWITCHER
// ============================================================
function switchSource(src) {
  currentSource = src;
  CONFIG.ACTIVE_SOURCE = src;
  document.querySelectorAll(".source-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.source === src);
  });
  fetchLiveNews();
}

function getCountrySearchList() {
  return Object.entries(COUNTRY_COORDS)
    .map(([code, info]) => ({ code, ...info }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function renderCountrySearchResults(items) {
  const resultsEl = document.getElementById("country-search-results");
  if (!resultsEl) return;
  if (!items.length) {
    resultsEl.innerHTML = "";
    resultsEl.style.display = "none";
    return;
  }
  resultsEl.innerHTML = items.map((item) => `
    <div class="country-search-item" data-code="${item.code}">
      ${item.name}
    </div>
  `).join("");
  resultsEl.style.display = "block";
}

function focusCountryByCode(code) {
  const info = COUNTRY_COORDS[code];
  if (!info || !map) return;
  activeMapCountry = code;
  map.setView(info.coords, 4);
  document.getElementById("map-filter-bar").style.display = "flex";
  document.getElementById("map-filter-label").textContent = `Showing: ${info.name}`;
  mapMarkers.forEach((m) => m.setStyle({ weight: 1.5, color: m.options.fillColor }));
  const selected = mapMarkers.find((m) => m._countryCode === code);
  if (selected) {
    selected.setStyle({ weight: 3, color: "#ffffff" });
    selected.openPopup();
  }
  renderNewsFeed(applyFilters());
}

function resetCountrySearch() {
  mapSearchQuery = "";
  const input = document.getElementById("country-search-input");
  if (input) input.value = "";
  renderCountrySearchResults([]);
  clearMapFilter();
  if (map) map.setView([20, 10], 2);
}

// ============================================================
// SECTION 12 — UI HELPERS
// ============================================================
function switchTab(_tab, el) {
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
  if (el) el.classList.add("active");
}

function showLoading(show) {
  document.getElementById("loading-overlay").style.display = show ? "flex" : "none";
}

function showErrorToast(msg) {
  const t = document.getElementById("error-toast");
  t.textContent = msg;
  t.classList.add("toast-show");
  setTimeout(() => t.classList.remove("toast-show"), 4000);
}

function showSuccessToast(msg) {
  const t = document.getElementById("success-toast");
  t.textContent = msg;
  t.classList.add("toast-show");
  setTimeout(() => t.classList.remove("toast-show"), 2500);
}

function showSourceStatus(msg, color) {
  const el = document.getElementById("source-status");
  el.textContent = msg;
  el.style.color = color === "green" ? "#1D9E75" : color === "orange" ? "#EF9F27" : "#E24B4A";
}

function updateTimestamp() {
  const now = new Date();
  document.getElementById("last-updated").textContent =
    `Last updated: ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

function resetCountdown() {
  clearInterval(countdownInterval);
  countdownSeconds = CONFIG.REFRESH_INTERVAL / 1000;
  document.getElementById("countdown-timer").textContent = `Next: ${countdownSeconds}s`;
  countdownInterval = setInterval(() => {
    countdownSeconds -= 1;
    document.getElementById("countdown-timer").textContent = `Next: ${countdownSeconds}s`;
    if (countdownSeconds <= 0) {
      clearInterval(countdownInterval);
      fetchLiveNews();
    }
  }, 1000);
}

function manualRefresh() {
  clearInterval(countdownInterval);
  fetchLiveNews();
}

function toggleTheme() {
  document.body.classList.toggle("light-mode");
  document.getElementById("theme-toggle").textContent = document.body.classList.contains("light-mode") ? "🌙" : "☀";
}

function timeAgo(dateStr) {
  if (!dateStr) return "recently";
  const d = new Date(dateStr).getTime();
  if (Number.isNaN(d)) return "recently";
  const diff = (Date.now() - d) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function truncate(str, n) {
  return str && str.length > n ? `${str.slice(0, n)}...` : (str || "");
}

function detectCountryFromText(text) {
  const mapCountry = {
    ukraine: "ua", russia: "ru", israel: "il", gaza: "ps", palestine: "ps",
    iran: "ir", iraq: "iq", syria: "sy", yemen: "ye", afghanistan: "af",
    china: "cn", india: "in", pakistan: "pk", myanmar: "mm", sudan: "sd",
    ethiopia: "et", nigeria: "ng", libya: "ly", somalia: "so", lebanon: "lb",
    usa: "us", "united states": "us", america: "us", uk: "gb", britain: "gb",
    france: "fr", germany: "de", australia: "au", canada: "ca", japan: "jp"
  };
  const t = (text || "").toLowerCase();
  for (const [word, code] of Object.entries(mapCountry)) {
    if (t.includes(word)) return code;
  }
  return "us";
}

function formatGDELTDate(str) {
  if (!str || str.length < 8) return null;
  try {
    return new Date(
      `${str.slice(0, 4)}-${str.slice(4, 6)}-${str.slice(6, 8)}T${str.slice(8, 10) || "00"}:${str.slice(10, 12) || "00"}:00Z`
    ).toISOString();
  } catch {
    return null;
  }
}

function copyReport() {
  const peace = allArticles.filter((a) => a.cls === "peace").length;
  const conflict = allArticles.filter((a) => a.cls === "conflict").length;
  const neutral = allArticles.filter((a) => a.cls === "neutral").length;
  const avg = allArticles.length ? (allArticles.reduce((s, a) => s + a.score, 0) / allArticles.length).toFixed(1) : "N/A";
  const report = `
GLOBAL PEACE DASHBOARD REPORT
Generated: ${new Date().toLocaleString()}
Source: ${CONFIG.ACTIVE_SOURCE}
----------------------------------------
Global Peace Index:  ${avg} / 10
Articles Analyzed:   ${allArticles.length}
Peace Events:        ${peace}
Neutral Events:      ${neutral}
Conflict Alerts:     ${conflict}
----------------------------------------
Top Conflict Headlines:
${allArticles.filter((a) => a.cls === "conflict").slice(0, 3).map((a) => `• ${a.title}`).join("\n")}

Top Peace Headlines:
${allArticles.filter((a) => a.cls === "peace").slice(0, 3).map((a) => `• ${a.title}`).join("\n")}
  `.trim();

  navigator.clipboard.writeText(report)
    .then(() => showSuccessToast("Report copied to clipboard!"))
    .catch(() => showErrorToast("Copy failed. Try manually."));
}

// ============================================================
// SECTION 13 — FALLBACK DATA
// ============================================================
const FALLBACK_ARTICLES = [
  {
    title: "UN brokered ceasefire holds for third consecutive day in conflict region",
    description: "Peace talks continue as diplomatic efforts show positive results for stability",
    source: "Reuters", country: "gb", pubDate: new Date().toISOString(), link: "#", apiSource: "Sample"
  },
  {
    title: "Missile strikes and artillery fire reported overnight killing dozens",
    description: "Armed conflict escalates as international community condemns attacks",
    source: "BBC", country: "ua", pubDate: new Date().toISOString(), link: "#", apiSource: "Sample"
  },
  {
    title: "G20 summit opens focusing on global economic cooperation and development",
    description: "World leaders gather to discuss trade, climate and sustainable development goals",
    source: "Al Jazeera", country: "us", pubDate: new Date().toISOString(), link: "#", apiSource: "Sample"
  },
  {
    title: "Humanitarian aid convoy finally reaches conflict zone after negotiations",
    description: "Relief organizations deliver food and medicine to thousands of displaced people",
    source: "Guardian", country: "ye", pubDate: new Date().toISOString(), link: "#", apiSource: "Sample"
  }
];

// ============================================================
// SECTION 14 — INIT
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  const countryInput = document.getElementById("country-search-input");
  const countryResults = document.getElementById("country-search-results");

  if (countryInput && countryResults) {
    countryInput.addEventListener("input", (event) => {
      mapSearchQuery = event.target.value.trim().toLowerCase();
      if (!mapSearchQuery) {
        renderCountrySearchResults([]);
        return;
      }
      const matches = getCountrySearchList()
        .filter((item) => item.name.toLowerCase().includes(mapSearchQuery))
        .slice(0, 8);
      renderCountrySearchResults(matches);
    });

    countryResults.addEventListener("click", (event) => {
      const item = event.target.closest(".country-search-item");
      if (!item) return;
      const code = item.dataset.code;
      const selected = COUNTRY_COORDS[code];
      if (!selected) return;
      countryInput.value = selected.name;
      renderCountrySearchResults([]);
      focusCountryByCode(code);
    });

    document.addEventListener("click", (event) => {
      const wrap = document.getElementById("country-search-wrap");
      if (wrap && !wrap.contains(event.target)) {
        renderCountrySearchResults([]);
      }
    });
  }

  fetchLiveNews();
  refreshTimer = setInterval(fetchLiveNews, CONFIG.REFRESH_INTERVAL);
});
