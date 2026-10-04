const ADMIN_REFRESH_INTERVAL_MS = 30000;

function formatDateTime(isoString) {
  const parsed = new Date(isoString.replace(' ', 'T'));
  const year = parsed.getFullYear();
  const month = parsed.getMonth() + 1;
  const day = parsed.getDate();
  let hours = parsed.getHours();
  const minutes = parsed.getMinutes();
  const suffix = hours >= 12 ? 'م' : 'ص';
  hours = hours % 12;
  if (hours === 0) { hours = 12; }
  const minutesText = String(minutes).padStart(2, '0');
  const datePart = `${year}/${month}/${day}م`;
  const timePart = `${hours}:${minutesText}${suffix}`;
  return `<span dir="ltr">${datePart}</span> <span dir="ltr">${timePart}</span>`;
}

function setupLoginForm() {
  const form = document.getElementById('login-form');
  if (!form) { return; }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const errorBox = document.getElementById('login-error');
    errorBox.classList.remove('is-visible');

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const csrfToken = document.getElementById('csrf-token').value;

    fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, csrf_token: csrfToken })
    })
      .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          errorBox.textContent = data.error || 'تعذر تسجيل الدخول';
          errorBox.classList.add('is-visible');
          return;
        }
        window.location.href = '/admin';
      });
  });
}

function setupLogoutButton() {
  const button = document.getElementById('logout-button');
  if (!button) { return; }

  button.addEventListener('click', () => {
    fetch('/api/logout', { method: 'POST' }).then(() => {
      window.location.href = '/login';
    });
  });
}

function loadStats() {
  fetch('/api/admin/stats').then((response) => response.json()).then((stats) => {
    document.getElementById('stat-total').textContent = stats.total_spaces;
    document.getElementById('stat-occupied').textContent = stats.occupied_spaces;
    document.getElementById('stat-vacant').textContent = stats.vacant_spaces;
    document.getElementById('stat-rate').textContent = `${stats.occupancy_rate}%`;
  });
}

function toggleSpaceStatus(space, onDone) {
  const nextStatus = space.status === 'vacant' ? 'occupied' : 'vacant';
  const confirmed = window.confirm(`هل تريد تجاوز حالة المكان ${space.space_number} إلى ${nextStatus === 'vacant' ? 'شاغر' : 'مشغول'}؟`);
  if (!confirmed) { return; }

  fetch(`/api/parking-spaces/${space.id}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: nextStatus })
  }).then((response) => response.json()).then(() => {
    onDone();
  });
}

function buildAdminSpaceCell(space, onChanged) {
  const cell = document.createElement('button');
  cell.type = 'button';
  cell.className = `space-cell space-cell--${space.status}`;
  cell.textContent = space.space_number;
  cell.addEventListener('click', () => toggleSpaceStatus(space, onChanged));
  return cell;
}

function buildAdminLotPanel(lot, spaces, onChanged) {
  const vacantCount = spaces.filter((space) => space.status === 'vacant').length;

  const panel = document.createElement('article');
  panel.className = 'lot-panel';

  const header = document.createElement('div');
  header.className = 'lot-panel__header';

  const titleBlock = document.createElement('div');
  const name = document.createElement('div');
  name.className = 'lot-panel__name';
  name.textContent = lot.name;
  const address = document.createElement('div');
  address.className = 'lot-panel__address';
  address.textContent = lot.address;
  titleBlock.appendChild(name);
  titleBlock.appendChild(address);

  const badge = document.createElement('div');
  badge.className = 'lot-panel__badge';
  badge.textContent = `شاغر ${vacantCount} من ${spaces.length}`;

  header.appendChild(titleBlock);
  header.appendChild(badge);

  const grid = document.createElement('div');
  grid.className = 'spaces-grid';
  spaces.forEach((space) => grid.appendChild(buildAdminSpaceCell(space, onChanged)));

  panel.appendChild(header);
  panel.appendChild(grid);

  return panel;
}

function loadAdminLots() {
  const grid = document.getElementById('admin-lots-grid');
  if (!grid) { return; }

  fetch('/api/parking-lots').then((response) => response.json()).then((lots) => {
    const requests = lots.map((lot) => fetch(`/api/parking-lots/${lot.id}/spaces`)
      .then((response) => response.json())
      .then((spaces) => ({ lot, spaces })));
    return Promise.all(requests);
  }).then((entries) => {
    grid.innerHTML = '';
    entries.forEach((entry) => {
      grid.appendChild(buildAdminLotPanel(entry.lot, entry.spaces, refreshDashboard));
    });
  });
}

function loadLogs() {
  const tableBody = document.getElementById('log-table-body');
  if (!tableBody) { return; }

  fetch('/api/admin/logs').then((response) => response.json()).then((logs) => {
    tableBody.innerHTML = '';
    logs.forEach((log) => {
      const row = document.createElement('tr');

      const timeCell = document.createElement('td');
      timeCell.innerHTML = formatDateTime(log.changed_at);

      const spaceCell = document.createElement('td');
      spaceCell.textContent = log.space_number;

      const statusCell = document.createElement('td');
      const statusLabel = log.new_status === 'vacant' ? 'شاغر' : 'مشغول';
      statusCell.innerHTML = `<span class="status-tag status-tag--${log.new_status}">${statusLabel}</span>`;

      const sourceCell = document.createElement('td');
      sourceCell.textContent = log.changed_by === 'cv_module' ? 'وحدة الرؤية الحاسوبية' : log.changed_by;

      row.appendChild(timeCell);
      row.appendChild(spaceCell);
      row.appendChild(statusCell);
      row.appendChild(sourceCell);
      tableBody.appendChild(row);
    });
  });
}

function drawOccupancyChart(history) {
  const canvas = document.getElementById('occupancy-chart');
  if (!canvas) { return; }

  const context = canvas.getContext('2d');
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = width;
  canvas.height = height;
  context.clearRect(0, 0, width, height);

  if (history.length === 0) {
    context.fillStyle = '#5B6B7A';
    context.font = '14px "IBM Plex Sans Arabic"';
    context.fillText('لا توجد بيانات كافية بعد لعرض الرسم البياني', 10, height / 2);
    return;
  }

  const maxAbsoluteDelta = Math.max(...history.map((point) => Math.abs(point.delta)), 1);
  const barWidth = width / history.length;

  history.forEach((point, index) => {
    const barHeight = (Math.abs(point.delta) / maxAbsoluteDelta) * (height / 2 - 10);
    const x = index * barWidth + 4;
    const barColor = point.delta >= 0 ? '#C23B32' : '#1F9D55';
    context.fillStyle = barColor;

    if (point.delta >= 0) {
      context.fillRect(x, height / 2 - barHeight, barWidth - 8, barHeight);
    } else {
      context.fillRect(x, height / 2, barWidth - 8, barHeight);
    }
  });

  context.strokeStyle = '#D8E0E6';
  context.beginPath();
  context.moveTo(0, height / 2);
  context.lineTo(width, height / 2);
  context.stroke();
}

function loadOccupancyHistory() {
  const canvas = document.getElementById('occupancy-chart');
  if (!canvas) { return; }

  fetch('/api/admin/occupancy-history').then((response) => response.json()).then((history) => {
    drawOccupancyChart(history);
  });
}

function refreshDashboard() {
  loadStats();
  loadAdminLots();
  loadLogs();
  loadOccupancyHistory();
}

setupLoginForm();
setupLogoutButton();

if (document.getElementById('stats-grid')) {
  refreshDashboard();
  setInterval(refreshDashboard, ADMIN_REFRESH_INTERVAL_MS);
}
