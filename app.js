const STORAGE_KEY = "family_sadaqa_counter_v1";

const state = {
  recitations: 0,
  sadaqa: 0,
  members: {},
  activity: [],
};

const reminders = [
  "Take 5 minutes today for recitation or one small act of sadaqa.",
  "Even a small daily deed can become a lasting charity.",
  "One recitation today, together as a family.",
  "A short prayer and one kind act can go far.",
  "Consistency matters more than quantity. Do one good deed today.",
];

const recitationCountEl = document.getElementById("recitationCount");
const sadaqaCountEl = document.getElementById("sadaqaCount");
const memberListEl = document.getElementById("memberList");
const activityListEl = document.getElementById("activityList");
const reminderTextEl = document.getElementById("reminderText");

function loadState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;

  try {
    const parsed = JSON.parse(raw);
    state.recitations = Number(parsed.recitations) || 0;
    state.sadaqa = Number(parsed.sadaqa) || 0;
    state.members = parsed.members || {};
    state.activity = Array.isArray(parsed.activity) ? parsed.activity : [];
  } catch (_err) {
    // Ignore corrupted local data.
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function addActivity(text) {
  const item = {
    text,
    when: new Date().toLocaleString(),
  };
  state.activity.unshift(item);
  state.activity = state.activity.slice(0, 20);
}

function renderMembers() {
  const names = Object.keys(state.members);
  memberListEl.innerHTML = "";

  if (!names.length) {
    memberListEl.innerHTML = "<li><span>No contributions yet.</span></li>";
    return;
  }

  names
    .sort((a, b) => a.localeCompare(b))
    .forEach((name) => {
      const info = state.members[name];
      const li = document.createElement("li");
      li.textContent = `${name}: ${info.recitation || 0} recitations, ${info.sadaqa || 0} sadaqa`;
      memberListEl.appendChild(li);
    });
}

function renderActivity() {
  activityListEl.innerHTML = "";
  if (!state.activity.length) {
    activityListEl.innerHTML = "<li><span>No activity yet.</span></li>";
    return;
  }

  state.activity.forEach((entry) => {
    const li = document.createElement("li");
    li.textContent = `${entry.text} `;
    const meta = document.createElement("span");
    meta.textContent = `(${entry.when})`;
    li.appendChild(meta);
    activityListEl.appendChild(li);
  });
}

function render() {
  recitationCountEl.textContent = String(state.recitations);
  sadaqaCountEl.textContent = String(state.sadaqa);
  renderMembers();
  renderActivity();
}

function increment(type, who = "Family") {
  if (type === "recitation") {
    state.recitations += 1;
  }

  if (type === "sadaqa") {
    state.sadaqa += 1;
  }

  const name = who.trim();
  if (!state.members[name]) {
    state.members[name] = { recitation: 0, sadaqa: 0 };
  }
  state.members[name][type] += 1;

  addActivity(`${name} added 1 ${type}`);
  saveState();
  render();
}

function pickReminder() {
  const index = Math.floor(Math.random() * reminders.length);
  reminderTextEl.textContent = reminders[index];
}

document.getElementById("addRecitationBtn").addEventListener("click", () => {
  increment("recitation");
});

document.getElementById("addSadaqaBtn").addEventListener("click", () => {
  increment("sadaqa");
});

document.getElementById("memberForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const nameInput = document.getElementById("memberName");
  const typeInput = document.getElementById("contributionType");
  const name = nameInput.value.trim();

  if (!name) return;

  increment(typeInput.value, name);
  nameInput.value = "";
  nameInput.focus();
});

document.getElementById("newReminderBtn").addEventListener("click", pickReminder);

document.getElementById("resetBtn").addEventListener("click", () => {
  const ok = window.confirm("Reset all counts and activity? This cannot be undone.");
  if (!ok) return;

  state.recitations = 0;
  state.sadaqa = 0;
  state.members = {};
  state.activity = [];

  saveState();
  render();
});

loadState();
render();
