const ANALYTICS_PERIODS = [
  { value: '7d', label: '7 дней' },
  { value: '30d', label: '30 дней' },
  { value: '90d', label: '90 дней' },
  { value: 'month', label: 'Месяц' },
  { value: 'year', label: 'Год' },
  { value: 'all', label: 'Всё время' }
];

let analyticsPeriod = 'month';
let analyticsData = null;
let analyticsLoading = false;

function analyticsFormat(value) {
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  }).format(Number(value) || 0) + ' ₽';
}

function analyticsEmpty(text = 'Недостаточно данных') {
  return `<div class="analytics-empty">${text}</div>`;
}

function analyticsBars(items, key, valueKey, maxItems = 10) {
  const data = items.slice(0, maxItems);
  if (!data.length) return analyticsEmpty();

  const max = Math.max(1, ...data.map(x => Number(x[valueKey]) || 0));

  return `<div class="analytics-bars">${data.map(item => {
    const value = Number(item[valueKey]) || 0;
    const width = Math.max(0, value / max * 100);
    return `
      <div class="analytics-bar-row">
        <div class="analytics-bar-label">
          <span>${esc(String(item[key]))}</span>
          <strong>${analyticsFormat(value)}</strong>
        </div>
        <div class="analytics-track">
          <div class="analytics-fill" style="width:${width}%"></div>
        </div>
      </div>`;
  }).join('')}</div>`;
}

function analyticsLineChart(items) {
  if (!items.length) return analyticsEmpty('Пока нет операций за этот период');

  const width = 640, height = 220, pad = 24;
  const values = items.flatMap(x => [Number(x.income) || 0, Number(x.expense) || 0]);
  const max = Math.max(1, ...values);
  const x = i => pad + i * (width - pad * 2) / Math.max(1, items.length - 1);
  const y = v => height - pad - (v / max) * (height - pad * 2);

  function path(field) {
    return items.map((item, i) =>
      `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(Number(item[field]) || 0).toFixed(1)}`
    ).join(' ');
  }

  return `
    <svg viewBox="0 0 ${width} ${height}" class="analytics-svg" role="img"
         aria-label="График доходов и расходов">
      <line x1="${pad}" y1="${height-pad}" x2="${width-pad}" y2="${height-pad}"
            stroke="#ffffff22"/>
      <line x1="${pad}" y1="${height/2}" x2="${width-pad}" y2="${height/2}"
            stroke="#ffffff16" stroke-dasharray="4 6"/>
      <path d="${path('income')}" fill="none" stroke="#40d6a0"
            stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="${path('expense')}" fill="none" stroke="#a78bfa"
            stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      ${items.map((item, i) => `
        <circle cx="${x(i)}" cy="${y(Number(item.income) || 0)}"
          r="11" fill="transparent"
          data-analytics-day="${item.date}"
          data-analytics-kind="income"
          style="cursor:pointer"/>
        <circle cx="${x(i)}" cy="${y(Number(item.expense) || 0)}"
          r="11" fill="transparent"
          data-analytics-day="${item.date}"
          data-analytics-kind="expense"
          style="cursor:pointer"/>
      `).join('')}
    </svg>
    <div class="analytics-legend">
      <span>🟢 Доходы</span><span>🟣 Расходы</span>
    </div>`;
}

function analyticsDonut(items) {
  const data = items.filter(x => Number(x.amount) > 0).slice(0, 8);
  if (!data.length) return analyticsEmpty('Нет расходов по категориям');

  const total = data.reduce((sum, x) => sum + Number(x.amount), 0);
  const colors = ['#a78bfa','#38bdf8','#34d399','#fbbf24',
                  '#fb7185','#818cf8','#2dd4bf','#f472b6'];

  let current = 0;
  const stops = data.map((item, i) => {
    const start = current;
    current += Number(item.amount) / total * 100;
    return `${colors[i]} ${start}% ${current}%`;
  }).join(',');

  return `
    <div class="analytics-donut-wrap">
      <div class="analytics-donut" style="background:conic-gradient(${stops})">
        <div class="analytics-donut-inner">
          <small>Расходы</small>
          <strong>${analyticsFormat(total)}</strong>
        </div>
      </div>
    </div>
    <div class="analytics-category-legend">
      ${data.map((item, i) => `
        <div>
          <span data-analytics-category="${encodeURIComponent(item.name)}"
                style="cursor:pointer">
            <i style="background:${colors[i]}"></i>${esc(item.name)}
          </span>
          <b>${(Number(item.amount)/total*100).toFixed(1)}%</b>
        </div>`).join('')}
    </div>`;
}

function analyticsHeatmap(items) {
  if (!items.length) return analyticsEmpty('Пока нет расходов');

  const map = new Map(items.map(x => [x.date, Number(x.amount) || 0]));
  const max = Math.max(1, ...map.values());
  const days = [];

  const end = new Date();
  for (let i = 83; i >= 0; i--) {
    const day = new Date(end);
    day.setDate(end.getDate() - i);
    const key = [
      day.getFullYear(),
      String(day.getMonth() + 1).padStart(2, '0'),
      String(day.getDate()).padStart(2, '0')
    ].join('-');
    const value = map.get(key) || 0;
    const opacity = value ? (0.2 + 0.8 * value / max) : 0.07;
    days.push(`<div class="analytics-day"
      data-analytics-day="${key}"
      title="${key}: ${analyticsFormat(value)}"
      style="background:rgba(167,139,250,${opacity});cursor:pointer"></div>`);
  }

  return `<div class="analytics-heatmap">${days.join('')}</div>
    <div class="analytics-hint">Последние 12 недель · чем ярче, тем больше расходы</div>`;
}

function analyticsCard(title, content, subtitle = '') {
  return `<div class="analytics-panel">
    <div class="analytics-panel-title">${title}</div>
    ${subtitle ? `<div class="analytics-hint">${subtitle}</div>` : ''}
    ${content}
  </div>`;
}

function renderAnalyticsDashboard() {
  const root = document.getElementById('analytics');
  if (!root) return;

  const filters = `<div class="analytics-periods">
    ${ANALYTICS_PERIODS.map(p => `
      <button class="${analyticsPeriod === p.value ? 'selected' : ''}"
        onclick="changeAnalyticsPeriod('${p.value}')">${p.label}</button>
    `).join('')}
  </div>`;

  if (!analyticsData) {
    root.innerHTML = `<div class="top"><div class="brand">Аналитика</div></div>
      ${filters}${analyticsEmpty(analyticsLoading ? 'Загружаем статистику…' : 'Нет данных')}`;
    return;
  }

  const a = analyticsData;
  const s = a.summary;

  root.innerHTML = `
    <div class="top"><div class="brand">Аналитика</div></div>
    <p class="analytics-subtitle">Твоя финансовая картина в деталях</p>
    ${filters}
    <div class="analytics-summary">
      <div><small>Доходы</small><strong style="color:#34d399">${analyticsFormat(s.income)}</strong></div>
      <div><small>Расходы</small><strong style="color:#fb7185">${analyticsFormat(s.expense)}</strong></div>
      <div><small>Разница</small><strong>${analyticsFormat(s.net)}</strong></div>
      <div><small>Средний расход в день</small><strong>${analyticsFormat(s.average_daily_expense)}</strong></div>
    </div>
    ${analyticsCard('Структура расходов', analyticsDonut(a.categories))}
    ${analyticsCard('Доходы и расходы по дням', analyticsLineChart(a.daily))}
    ${analyticsCard('Топ категорий', analyticsBars(a.categories, 'name', 'amount'))}
    ${analyticsCard('Расходы по дням недели', analyticsBars(a.weekdays, 'day', 'amount', 7))}
    ${analyticsCard('Движение по месяцам',
      analyticsBars(a.monthly.map(x => ({
        name: x.month, amount: x.expense
      })), 'name', 'amount', 24))}
    ${analyticsCard('Расходы по счетам',
      analyticsBars(a.accounts.map(x => ({
        name: x.name, amount: x.expense
      })).sort((x,y) => y.amount - x.amount), 'name', 'amount'))}
    ${analyticsCard('Календарь расходов', analyticsHeatmap(a.calendar))}
    ${analyticsCard('Статистика операций', `
      <div class="analytics-stats">
        <div>Расходных операций <b>${s.expense_count}</b></div>
        <div>Средний чек <b>${analyticsFormat(s.average_transaction)}</b></div>
        <div>Самая большая трата <b>${analyticsFormat(s.biggest_expense)}</b></div>
        <div>Доходных операций <b>${s.income_count}</b></div>
      </div>`)}
  `;
}

async function changeAnalyticsPeriod(period) {
  analyticsPeriod = period;
  analyticsLoading = true;
  analyticsData = null;
  renderAnalyticsDashboard();

  try {
    analyticsData = await api('/api/analytics?period=' + encodeURIComponent(period));
  } catch (error) {
    toast('Аналитика: ' + error.message);
  } finally {
    analyticsLoading = false;
    renderAnalyticsDashboard();
  }
}

// FINLY — интерактивная детализация аналитики

async function openAnalyticsDetails(title, filters = {}) {
  const params = new URLSearchParams({
    period: analyticsPeriod,
    ...filters
  });

  let overlay = document.getElementById('finly-analytics-details');

  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'finly-analytics-details';
    document.body.appendChild(overlay);
  }

  overlay.style.cssText = `
    position:fixed;inset:0;z-index:99999;
    background:rgba(3,8,20,.76);
    display:flex;align-items:flex-end;justify-content:center;
    backdrop-filter:blur(7px);
  `;

  overlay.innerHTML = `
    <div style="background:linear-gradient(180deg,#fff4f5,#fff 32%);
      color:#111827;width:100%;max-width:520px;
      max-height:88vh;overflow:auto;
      border-radius:30px 30px 0 0;
      padding:20px 20px 36px;box-sizing:border-box;
      box-shadow:0 -15px 70px #0005;">

      <div style="width:42px;height:5px;background:#d1d5db;
        border-radius:10px;margin:0 auto 22px"></div>

      <div style="display:flex;align-items:center;
        justify-content:space-between;gap:12px">

        <div>
          <div style="font-size:21px;font-weight:800">
            ${esc(title)}
          </div>
          <div style="color:#94a3b8;font-size:12px;margin-top:5px">
            История операций FINLY
          </div>
        </div>

        <button id="finly-details-close"
          style="border:0;background:#f1f2f5;
          border-radius:50%;width:38px;height:38px;
          color:#111827;font-size:24px">×</button>
      </div>

      <div id="finly-details-content"
        style="margin-top:20px">
        Загружаем операции...
      </div>
    </div>
  `;

  const close = () => {
    overlay.style.display = 'none';
  };

  overlay.querySelector('#finly-details-close').onclick = close;
  overlay.onclick = e => {
    if (e.target === overlay) close();
  };

  try {
    const result = await api(
      '/api/analytics/transactions?' + params.toString()
    );

    const rows = result.transactions || [];
    const total = rows.reduce(
      (sum, t) => sum + Number(t.amount || 0), 0
    );

    const content = overlay.querySelector('#finly-details-content');

    content.innerHTML = `
      <div style="padding:19px;border-radius:22px;
        background:#fff;border:1px solid #f0e9eb;
        box-shadow:0 6px 25px #11182709">

        <div style="font-size:12px;color:#64748b">
          Сумма операций
        </div>

        <div style="font-size:30px;font-weight:850;
          letter-spacing:-1px;margin-top:5px">
          ${analyticsFormat(total)}
        </div>

        <div style="font-size:12px;color:#94a3b8;margin-top:5px">
          ${rows.length} операций
          ${rows.length === 200 ? ' · показаны первые 200' : ''}
        </div>
      </div>

      <div style="font-size:15px;font-weight:750;
        margin:25px 0 10px">
        Операции
      </div>

      ${rows.length ? rows.map(t => `
        <div style="background:#fff;border:1px solid #edf0f4;
          border-radius:18px;padding:15px;
          margin-bottom:10px;box-shadow:0 3px 12px #11182706">

          <div style="display:flex;gap:12px;align-items:center">
            <div style="width:43px;height:43px;
              border-radius:14px;background:#ffe7eb;
              color:#fa3655;display:flex;align-items:center;
              justify-content:center;font-size:21px;
              flex-shrink:0">
              ${t.type === 'income' ? '↗' : '🛒'}
            </div>

            <div style="flex:1;min-width:0">
              <div style="font-weight:750;font-size:14px;
                overflow:hidden;text-overflow:ellipsis">
                ${esc(t.category || (t.type === 'income' ? 'Доход' : 'Расход'))}
              </div>

              <div style="font-size:11px;color:#94a3b8;margin-top:5px">
                ${esc(t.account || '')} · ${esc(String(t.date || ''))}
              </div>
            </div>

            <div style="font-weight:800;font-size:15px;
              color:${t.type === 'income' ? '#16a34a' : '#f43f5e'}">
              ${t.type === 'income' ? '+' : '−'}${analyticsFormat(t.amount)}
            </div>
          </div>

          <button data-finly-edit="${Number(t.id)}"
            style="width:100%;margin-top:13px;
              background:#fff0f2;color:#e63250;
              border:0;border-radius:12px;padding:12px;
              font-weight:750;font-size:13px">
            ✎ Изменить операцию
          </button>
        </div>
      `).join('') : `
        <div style="text-align:center;padding:30px;color:#94a3b8">
          Операций нет
        </div>
      `}
    `;

    content.querySelectorAll('[data-finly-edit]').forEach(button => {
      button.onclick = async () => {
        const id = Number(button.dataset.finlyEdit);
        const tx = rows.find(item => Number(item.id) === id);

        if (!tx) return;

        close();

        // Use full dashboard transaction if available.
        const existing = (D.transactions || []).find(
          item => Number(item.id) === id
        );

        if (existing) {
          editTx(id);
          return;
        }

        // Refresh dashboard so the edit form can locate this transaction.
        try {
          D = await api('/api/dashboard');

          const found = (D.transactions || []).find(
            item => Number(item.id) === id
          );

          if (found) {
            editTx(id);
          } else {
            toast('Операция не входит в последние 30. Добавим поддержку истории.');
          }
        } catch (error) {
          toast(error.message);
        }
      };
    });

  } catch (error) {
    const content = overlay.querySelector('#finly-details-content');
    if (content) {
      content.textContent = 'Ошибка загрузки: ' + error.message;
    }
  }
}

document.addEventListener('click', function handleAnalyticsCategoryClick(event) {
  const target = event.target.closest('[data-analytics-category]');
  if (!target) return;

  const category = decodeURIComponent(
    target.getAttribute('data-analytics-category')
  );

  openAnalyticsDetails('Расходы: ' + category, {category});
});

document.addEventListener('click', function handleAnalyticsDayClick(event) {
  const target = event.target.closest('[data-analytics-day]');
  if (!target) return;

  const day = target.getAttribute('data-analytics-day');
  const kind = target.getAttribute('data-analytics-kind') || 'expense';
  const title = kind === 'income' ? 'Доходы за ' : 'Расходы за ';
  openAnalyticsDetails(title + day, {day, kind});
});
