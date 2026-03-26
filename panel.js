const STORAGE_KEY = 'disciplinePanelState';

const defaultState = {
  news: [],
  checks: {
    hasNews: false,
    aboveMA5: false,
    isLeader: false,
    notFallingKnife: false,
    notOverextended: false,
    uncertain: false,
  },
};

const newsForm = document.getElementById('news-form');
const newsText = document.getElementById('news-text');
const newsRank = document.getElementById('news-rank');
const newsList = document.getElementById('news-list');
const checklistForm = document.getElementById('checklist-form');
const uncertainCheckbox = document.getElementById('uncertain');
const decision = document.getElementById('decision');
const newsItemTemplate = document.getElementById('news-item-template');

let state = structuredClone(defaultState);

init().catch((error) => {
  console.error('初始化失败', error);
});

async function init() {
  const stored = await chrome.storage.local.get(STORAGE_KEY);
  if (stored?.[STORAGE_KEY]) {
    state = {
      ...structuredClone(defaultState),
      ...stored[STORAGE_KEY],
      checks: {
        ...defaultState.checks,
        ...stored[STORAGE_KEY].checks,
      },
    };
  }

  hydrateChecklist();
  renderNews();
  updateDecision();
}

newsForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const text = newsText.value.trim();
  const rank = Number.parseInt(newsRank.value, 10);

  if (!text || Number.isNaN(rank) || rank < 1) {
    return;
  }

  state.news.push({ id: crypto.randomUUID(), text, rank });
  state.news.sort((a, b) => a.rank - b.rank);

  newsText.value = '';
  newsRank.value = String(Math.max(1, state.news.length));

  await persist();
  renderNews();
});

newsList.addEventListener('click', async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) {
    return;
  }

  const id = target.dataset.id;
  state.news = state.news.filter((item) => item.id !== id);
  await persist();
  renderNews();
});

checklistForm.addEventListener('change', async () => {
  state.checks = {
    hasNews: checklistForm.elements.hasNews.checked,
    aboveMA5: checklistForm.elements.aboveMA5.checked,
    isLeader: checklistForm.elements.isLeader.checked,
    notFallingKnife: checklistForm.elements.notFallingKnife.checked,
    notOverextended: checklistForm.elements.notOverextended.checked,
    uncertain: uncertainCheckbox.checked,
  };

  await persist();
  updateDecision();
});

function hydrateChecklist() {
  checklistForm.elements.hasNews.checked = state.checks.hasNews;
  checklistForm.elements.aboveMA5.checked = state.checks.aboveMA5;
  checklistForm.elements.isLeader.checked = state.checks.isLeader;
  checklistForm.elements.notFallingKnife.checked = state.checks.notFallingKnife;
  checklistForm.elements.notOverextended.checked = state.checks.notOverextended;
  uncertainCheckbox.checked = state.checks.uncertain;
}

function renderNews() {
  newsList.innerHTML = '';

  for (const item of state.news) {
    const node = newsItemTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector('.news-rank').textContent = `#${item.rank}`;
    node.querySelector('.news-text').textContent = item.text;

    const deleteButton = node.querySelector('.delete-btn');
    deleteButton.dataset.id = item.id;

    newsList.appendChild(node);
  }
}

function updateDecision() {
  const { uncertain, ...mustPassChecks } = state.checks;
  const allPass = Object.values(mustPassChecks).every(Boolean);

  if (uncertain) {
    setDecision('❌ 有“不确定”，直接不下单。', 'blocked');
    return;
  }

  if (!allPass) {
    setDecision('⛔ 违反规则：今天立即停止交易。', 'blocked');
    return;
  }

  setDecision('✅ 全部满足，可以考虑按计划执行。', 'ready');
}

function setDecision(text, type) {
  decision.className = `decision ${type}`;
  decision.textContent = text;
}

function persist() {
  return chrome.storage.local.set({
    [STORAGE_KEY]: state,
  });
}
