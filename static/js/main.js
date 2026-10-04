const REFRESH_INTERVAL_MS = 30000;

let allLots = [];
let selectedLotId = null;

function fetchLots() {
  return fetch('/api/parking-lots').then((response) => response.json());
}

function fetchSpacesForLot(lotId) {
  return fetch(`/api/parking-lots/${lotId}/spaces`).then((response) => response.json());
}

function buildSpaceCell(space) {
  const cell = document.createElement('button');
  cell.type = 'button';
  cell.className = `space-cell space-cell--${space.status}`;
  cell.textContent = space.space_number;
  cell.addEventListener('click', () => showSpaceInfo(space));
  return cell;
}

function buildLotPanel(lot, spaces) {
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
  spaces.forEach((space) => grid.appendChild(buildSpaceCell(space)));

  panel.appendChild(header);
  panel.appendChild(grid);
  panel.addEventListener('click', () => showLotInfo(lot, spaces));

  return panel;
}

function renderLots(filterText) {
  const grid = document.getElementById('lots-grid');
  grid.innerHTML = '';

  const query = (filterText || '').trim();
  const filteredLots = allLots.filter((entry) => {
    const haystack = `${entry.lot.name} ${entry.lot.address}`;
    return haystack.includes(query);
  });

  filteredLots.forEach((entry) => {
    grid.appendChild(buildLotPanel(entry.lot, entry.spaces));
  });
}

function loadAllLots() {
  fetchLots().then((lots) => {
    const requests = lots.map((lot) => fetchSpacesForLot(lot.id).then((spaces) => ({ lot, spaces })));
    return Promise.all(requests);
  }).then((entries) => {
    allLots = entries;
    renderLots(document.getElementById('lot-search').value);
  });
}

function showLotInfo(lot, spaces) {
  const vacantCount = spaces.filter((space) => space.status === 'vacant').length;
  const panel = document.getElementById('info-panel');
  const title = document.getElementById('info-panel-title');
  const body = document.getElementById('info-panel-body');

  title.textContent = lot.name;
  body.innerHTML = '';

  const rows = [
    ['العنوان', lot.address],
    ['إجمالي الأماكن', String(spaces.length)],
    ['الأماكن الشاغرة', String(vacantCount)]
  ];

  rows.forEach(([label, value]) => {
    const row = document.createElement('div');
    row.className = 'info-panel__row';
    const labelSpan = document.createElement('span');
    labelSpan.textContent = label;
    const valueSpan = document.createElement('span');
    valueSpan.textContent = value;
    row.appendChild(labelSpan);
    row.appendChild(valueSpan);
    body.appendChild(row);
  });

  panel.classList.add('is-visible');
}

function showSpaceInfo(space) {
  const panel = document.getElementById('info-panel');
  const title = document.getElementById('info-panel-title');
  const body = document.getElementById('info-panel-body');

  title.textContent = `مكان الوقوف ${space.space_number}`;
  body.innerHTML = '';

  const statusLabel = space.status === 'vacant' ? 'شاغر' : 'مشغول';
  const rows = [
    ['الحالة الحالية', statusLabel],
    ['آخر تحديث', space.updated_at]
  ];

  rows.forEach(([label, value]) => {
    const row = document.createElement('div');
    row.className = 'info-panel__row';
    const labelSpan = document.createElement('span');
    labelSpan.textContent = label;
    const valueSpan = document.createElement('span');
    valueSpan.textContent = value;
    row.appendChild(labelSpan);
    row.appendChild(valueSpan);
    body.appendChild(row);
  });

  panel.classList.add('is-visible');
}

function handleFindNearest() {
  const button = document.getElementById('find-nearest-button');
  const resultBox = document.getElementById('nearest-result');

  if (!navigator.geolocation) {
    window.alert('متصفحك لا يدعم خاصية تحديد الموقع الجغرافي');
    return;
  }

  button.disabled = true;

  navigator.geolocation.getCurrentPosition((position) => {
    const lat = position.coords.latitude;
    const lng = position.coords.longitude;

    fetch(`/api/nearest-parking?lat=${lat}&lng=${lng}`)
      .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
      .then(({ ok, data }) => {
        button.disabled = false;
        if (!ok) {
          window.alert(data.error || 'تعذر إيجاد موقف متاح حالياً');
          return;
        }
        document.getElementById('nearest-result-title').textContent = data.name;
        document.getElementById('nearest-result-meta').textContent =
          `${data.address}, يبعد تقريباً ${data.distance_km} كم, ${data.vacant_spaces} مكان شاغر`;
        resultBox.classList.add('is-visible');
      });
  }, () => {
    button.disabled = false;
    window.alert('تعذر الوصول إلى موقعك الحالي، يرجى السماح بذلك من إعدادات المتصفح');
  });
}

document.getElementById('find-nearest-button').addEventListener('click', handleFindNearest);
document.getElementById('dismiss-nearest-button').addEventListener('click', () => {
  document.getElementById('nearest-result').classList.remove('is-visible');
});
document.getElementById('lot-search').addEventListener('input', (event) => {
  renderLots(event.target.value);
});

loadAllLots();
setInterval(loadAllLots, REFRESH_INTERVAL_MS);
