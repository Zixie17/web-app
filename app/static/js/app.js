// Клиентская логика приложения TimeTracker

let activeTimersCache = [];
let liveInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initFormListeners();
  initPresetButtons();
  loadEmployees();
  loadActiveTimers();
  loadReport();

  // Запуск постоянного тикающего секундомера раз в секунду
  if (liveInterval) clearInterval(liveInterval);
  liveInterval = setInterval(updateLiveTimers, 1000);
});

// =======================
// УВЕДОМЛЕНИЯ (TOASTS)
// =======================
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const icon = type === "success" ? "✅" : (type === "error" ? "⚠️" : "ℹ️");
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// =======================
// НАВИГАЦИЯ ПО ВКЛАДКАМ
// =======================
function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));

      tab.classList.add("active");
      const targetPane = document.getElementById(tab.dataset.tab);
      if (targetPane) targetPane.classList.add("active");

      // При переходе на вкладку отчетов или сотрудников обновляем данные
      if (tab.dataset.tab === "tab-reports") {
        loadReport();
      } else if (tab.dataset.tab === "tab-employees") {
        loadEmployees();
      }
    });
  });
}

// =======================
// СОТРУДНИКИ
// =======================
async function loadEmployees() {
  try {
    const res = await fetch("/api/employees");
    if (!res.ok) throw new Error("Не удалось загрузить сотрудников");
    const employees = await res.json();

    // Обновляем счетчик
    document.getElementById("navEmployeesCount").textContent = employees.length;

    // Обновляем выпадающий список для запуска таймера
    const timerSelect = document.getElementById("timerEmployeeSelect");
    const currentTimerVal = timerSelect.value;
    timerSelect.innerHTML = '<option value="" disabled selected>-- Выберите сотрудника --</option>';

    // Обновляем выпадающий список в фильтре отчетов
    const filterSelect = document.getElementById("filterEmployeeSelect");
    const currentFilterVal = filterSelect.value;
    filterSelect.innerHTML = '<option value="">Все сотрудники</option>';

    employees.forEach(emp => {
      // Для таймера
      const opt = document.createElement("option");
      opt.value = emp.id;
      const statusText = emp.active_timer ? " [В РАБОТЕ]" : "";
      opt.textContent = `${emp.name} (${emp.position})${statusText}`;
      timerSelect.appendChild(opt);

      // Для фильтра
      const fOpt = document.createElement("option");
      fOpt.value = emp.id;
      fOpt.textContent = `${emp.name} (${emp.position})`;
      filterSelect.appendChild(fOpt);
    });

    if (currentTimerVal) timerSelect.value = currentTimerVal;
    if (currentFilterVal) filterSelect.value = currentFilterVal;

    // Отрисовка списка сотрудников на вкладке "Сотрудники"
    renderEmployeesList(employees);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderEmployeesList(employees) {
  const container = document.getElementById("employeesList");
  container.innerHTML = "";

  if (employees.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>Сотрудники пока не добавлены.</p></div>';
    return;
  }

  employees.forEach(emp => {
    const item = document.createElement("div");
    item.className = "employee-card-item";

    const initials = emp.name.split(" ").map(w => w[0]).join("").substring(0, 2).toUpperCase();
    const isActive = !!emp.active_timer;

    item.innerHTML = `
      <div class="emp-avatar">${initials}</div>
      <div class="emp-details">
        <div class="emp-title">${escapeHtml(emp.name)}</div>
        <div class="emp-sub">${escapeHtml(emp.position)}${emp.department ? " • " + escapeHtml(emp.department) : ""}</div>
      </div>
      <div>
        <span class="emp-status-badge ${isActive ? 'status-active' : 'status-idle'}">
          ${isActive ? '🟢 В работе: ' + escapeHtml(emp.active_timer.task_description) : '⚪ Свободен'}
        </span>
      </div>
    `;
    container.appendChild(item);
  });
}

// =======================
// АКТИВНЫЕ ТАЙМЕРЫ
// =======================
async function loadActiveTimers() {
  try {
    const res = await fetch("/api/timers/active");
    if (!res.ok) throw new Error("Не удалось загрузить таймеры");
    activeTimersCache = await res.json();

    document.getElementById("activeTimersCountBadge").textContent = 
      `🟢 ${activeTimersCache.length} активных`;

    renderActiveTimers();
  } catch (err) {
    console.error("Ошибка загрузки активных таймеров:", err);
  }
}

function renderActiveTimers() {
  const container = document.getElementById("activeTimersList");
  container.innerHTML = "";

  if (activeTimersCache.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">☕</div>
        <h3>Нет активных таймеров</h3>
        <p>Сейчас никто из сотрудников не ведёт учёт времени. Выберите сотрудника слева и запустите задачу.</p>
      </div>
    `;
    return;
  }

  activeTimersCache.forEach(timer => {
    const card = document.createElement("div");
    card.className = "active-timer-item";
    card.dataset.id = timer.id;
    card.dataset.startTime = timer.start_time;

    card.innerHTML = `
      <div class="active-timer-info">
        <div class="active-timer-name">${escapeHtml(timer.employee_name)}</div>
        <div class="active-timer-role">${escapeHtml(timer.employee_position)}</div>
        <div class="active-timer-task">
          <span>📌</span> <strong>${escapeHtml(timer.task_description)}</strong>
        </div>
      </div>
      <div class="active-timer-right">
        <span class="live-stopwatch" id="stopwatch-${timer.id}">00:00:00</span>
        <button class="btn btn-danger btn-sm" onclick="stopTimerHandler(${timer.id})">
          ⏹️ Завершить задачу
        </button>
      </div>
    `;
    container.appendChild(card);
  });

  updateLiveTimers();
}

function updateLiveTimers() {
  const now = new Date();
  activeTimersCache.forEach(t => {
    const elem = document.getElementById(`stopwatch-${t.id}`);
    if (elem) {
      const start = new Date(t.start_time);
      const diffSec = Math.max(0, Math.floor((now - start) / 1000));
      elem.textContent = formatSeconds(diffSec);
    }
  });
}

function formatSeconds(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// Остановка таймера
window.stopTimerHandler = async function(timerId) {
  try {
    const res = await fetch("/api/timers/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ time_entry_id: timerId })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Не удалось остановить таймер");
    }

    showToast(`Задача завершена! Затрачено: ${data.duration_formatted}`, "success");
    await loadActiveTimers();
    await loadEmployees();
    await loadReport();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// =======================
// ФОРМЫ (ДОБАВЛЕНИЕ И СТАРТ)
// =======================
function initFormListeners() {
  // Запуск таймера
  const startForm = document.getElementById("startTimerForm");
  startForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const empId = document.getElementById("timerEmployeeSelect").value;
    const taskDesc = document.getElementById("taskDescriptionInput").value.trim();

    if (!empId) {
      showToast("Пожалуйста, выберите сотрудника", "error");
      return;
    }
    if (!taskDesc) {
      showToast("Пожалуйста, укажите описание задачи", "error");
      return;
    }

    try {
      const res = await fetch("/api/timers/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          employee_id: parseInt(empId),
          task_description: taskDesc
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Не удалось запустить таймер");
      }

      showToast(`Таймер запущен для задачи: «${taskDesc}»`, "success");
      document.getElementById("taskDescriptionInput").value = "";
      await loadActiveTimers();
      await loadEmployees();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // Добавление сотрудника
  const addEmpForm = document.getElementById("addEmployeeForm");
  addEmpForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("empNameInput").value.trim();
    const pos = document.getElementById("empPositionInput").value.trim();
    const dept = document.getElementById("empDepartmentInput").value.trim();

    if (!name || !pos) {
      showToast("Заполните имя и должность", "error");
      return;
    }

    try {
      const res = await fetch("/api/employees", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name,
          position: pos,
          department: dept
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Не удалось добавить сотрудника");
      }

      showToast(`Сотрудник ${data.name} успешно добавлен!`, "success");
      addEmpForm.reset();
      await loadEmployees();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // Фильтрация отчетов
  const filterForm = document.getElementById("reportFilterForm");
  filterForm.addEventListener("submit", (e) => {
    e.preventDefault();
    document.querySelectorAll(".quick-preset-buttons button").forEach(btn => btn.classList.remove("active-preset"));
    loadReport();
  });

  // Сброс фильтра
  document.getElementById("btnResetFilter").addEventListener("click", () => {
    document.getElementById("filterStartDate").value = "";
    document.getElementById("filterEndDate").value = "";
    document.getElementById("filterEmployeeSelect").value = "";
    document.querySelectorAll(".quick-preset-buttons button").forEach(btn => btn.classList.remove("active-preset"));
    document.querySelector('.quick-preset-buttons button[data-preset="all"]').classList.add("active-preset");
    loadReport();
  });
}

// =======================
// БЫСТРЫЕ ПРЕСЕТЫ ПЕРИОДОВ
// =======================
function initPresetButtons() {
  const buttons = document.querySelectorAll(".quick-preset-buttons button");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active-preset"));
      btn.classList.add("active-preset");

      const preset = btn.dataset.preset;
      const startInput = document.getElementById("filterStartDate");
      const endInput = document.getElementById("filterEndDate");

      const now = new Date();
      const formatDate = (d) => {
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
      };

      if (preset === "today") {
        const todayStr = formatDate(now);
        startInput.value = todayStr;
        endInput.value = todayStr;
      } else if (preset === "yesterday") {
        const yest = new Date(now);
        yest.setDate(yest.getDate() - 1);
        const yestStr = formatDate(yest);
        startInput.value = yestStr;
        endInput.value = yestStr;
      } else if (preset === "week") {
        const curr = new Date(now);
        const day = curr.getDay();
        const diff = curr.getDate() - day + (day === 0 ? -6 : 1); // Понедельник
        const monday = new Date(curr.setDate(diff));
        startInput.value = formatDate(monday);
        endInput.value = formatDate(now);
      } else if (preset === "month") {
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        startInput.value = formatDate(firstDay);
        endInput.value = formatDate(now);
      } else if (preset === "all") {
        startInput.value = "";
        endInput.value = "";
      }

      loadReport();
    });
  });
}

// =======================
// ОТЧЁТЫ И АНАЛИТИКА
// =======================
async function loadReport() {
  const startDate = document.getElementById("filterStartDate").value;
  const endDate = document.getElementById("filterEndDate").value;
  const empId = document.getElementById("filterEmployeeSelect").value;

  const params = new URLSearchParams();
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  if (empId) params.append("employee_id", empId);

  try {
    const res = await fetch(`/api/reports?${params.toString()}`);
    if (!res.ok) throw new Error("Не удалось сформировать отчёт");
    const data = await res.json();

    // Обновляем KPI
    document.getElementById("kpiTotalTime").textContent = data.total_formatted;
    document.getElementById("kpiTotalTasks").textContent = data.total_tasks_count;
    document.getElementById("kpiActiveEmployeesCount").textContent = data.summary_by_employee.length;

    // Рендер сводной таблицы по сотрудникам
    renderSummaryTable(data.summary_by_employee);

    // Рендер детального журнала
    renderEntriesTable(data.entries);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderSummaryTable(summary) {
  const tbody = document.getElementById("reportSummaryTableBody");
  const emptyState = document.getElementById("reportSummaryEmpty");
  const table = document.getElementById("reportSummaryTable");

  tbody.innerHTML = "";

  if (!summary || summary.length === 0) {
    table.style.display = "none";
    emptyState.classList.remove("hidden");
    return;
  }

  table.style.display = "table";
  emptyState.classList.add("hidden");

  summary.forEach(item => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${escapeHtml(item.employee_name)}</strong></td>
      <td>${escapeHtml(item.position)}${item.department ? " (" + escapeHtml(item.department) + ")" : ""}</td>
      <td>${item.tasks_count}</td>
      <td><span class="time-pill">${item.total_formatted}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderEntriesTable(entries) {
  const tbody = document.getElementById("reportEntriesTableBody");
  const emptyState = document.getElementById("reportEntriesEmpty");
  const table = document.getElementById("reportEntriesTable");

  tbody.innerHTML = "";

  if (!entries || entries.length === 0) {
    table.style.display = "none";
    emptyState.classList.remove("hidden");
    return;
  }

  table.style.display = "table";
  emptyState.classList.add("hidden");

  entries.forEach(entry => {
    const tr = document.createElement("tr");

    const startFormatted = formatDateTimeLocal(entry.start_time);
    const endFormatted = formatDateTimeLocal(entry.end_time);

    tr.innerHTML = `
      <td><strong>${escapeHtml(entry.employee_name || "—")}</strong></td>
      <td>${escapeHtml(entry.task_description)}</td>
      <td>${startFormatted}</td>
      <td>${endFormatted}</td>
      <td><span class="time-pill">${entry.duration_formatted}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function formatDateTimeLocal(isoString) {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });
  } catch {
    return isoString;
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
