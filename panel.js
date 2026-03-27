const STORAGE_KEY = 'disciplinePanelState';

const defaultState = {
  news: [],
  checks: {
    hasNews: false,
    aboveMA5: false,
    isLeader: false,
    notFallingKnife: false,
    notOverextended: false,
  },
};

const newsForm = document.getElementById('news-form');
const newsText = document.getElementById('news-text');
const newsList = document.getElementById('news-list');
const checklistForm = document.getElementById('checklist-form');
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

  normalizeNewsOrder();
  hydrateChecklist();
  renderNews();
  updateDecision();
}

newsForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const text = newsText.value.trim();
  if (!text) {
    return;
  }

  state.news.push({ id: crypto.randomUUID(), text, rank: state.news.length + 1 });
  normalizeNewsOrder();

  newsText.value = '';
  await persist();
  renderNews();
});

newsList.addEventListener('click', async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) {
    return;
  }

  const id = target.dataset.id;
  if (!id) {
    return;
  }

  if (target.classList.contains('delete-btn')) {
    state.news = state.news.filter((item) => item.id !== id);
  }

  if (target.classList.contains('move-btn')) {
    const direction = target.dataset.direction;
    moveNews(id, direction === 'up' ? -1 : 1);
  }

  normalizeNewsOrder();
  await persist();
  renderNews();
});

newsList.addEventListener('change', async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement) || !target.classList.contains('rank-input')) {
    return;
  }

  const id = target.dataset.id;
  const nextRank = Number.parseInt(target.value, 10);

  if (!id || Number.isNaN(nextRank)) {
    renderNews();
    return;
  }

  reinsertByRank(id, nextRank);
  normalizeNewsOrder();
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
}

function renderNews() {
  newsList.innerHTML = '';

  for (const item of state.news) {
    const node = newsItemTemplate.content.firstElementChild.cloneNode(true);
    const rankInput = node.querySelector('.rank-input');
    rankInput.value = item.rank;
    rankInput.dataset.id = item.id;

    node.querySelector('.news-text').textContent = item.text;

    const buttons = node.querySelectorAll('button');
    for (const button of buttons) {
      button.dataset.id = item.id;
    }

    newsList.appendChild(node);
  }
}

function moveNews(id, offset) {
  const currentIndex = state.news.findIndex((item) => item.id === id);
  if (currentIndex < 0) {
    return;
  }

  const targetIndex = Math.min(state.news.length - 1, Math.max(0, currentIndex + offset));
  if (targetIndex === currentIndex) {
    return;
  }

  const [item] = state.news.splice(currentIndex, 1);
  state.news.splice(targetIndex, 0, item);
}

function reinsertByRank(id, nextRank) {
  const currentIndex = state.news.findIndex((item) => item.id === id);
  if (currentIndex < 0) {
    return;
  }

  const [item] = state.news.splice(currentIndex, 1);
  const targetIndex = Math.min(state.news.length, Math.max(0, nextRank - 1));
  state.news.splice(targetIndex, 0, item);
}

function normalizeNewsOrder() {
  state.news = state.news.map((item, index) => ({
    ...item,
    rank: index + 1,
  }));
}

function updateDecision() {
  const allPass = Object.values(state.checks).every(Boolean);

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
