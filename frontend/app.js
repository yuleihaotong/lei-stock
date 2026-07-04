/**
 * app.js - A股短线决策辅助工具 前端逻辑
 * 通过API与后端Python服务通信
 */

// ─── API配置 ───────────────────────────────────────────────────────
const API_BASE = 'http://127.0.0.1:5000';

// ─── 工具函数 ───────────────────────────────────────────────────────

function $(id) { return document.getElementById(id); }

function apiGet(path) {
  return fetch(`${API_BASE}${path}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    timeout: 15000,
  }).then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  });
}

function apiPost(path, data) {
  return fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(r => r.json());
}

function formatPrice(v) {
  if (v === undefined || v === null) return '--';
  return v.toFixed(2);
}

function formatChange(v) {
  if (v === undefined || v === null) return '--';
  return (v > 0 ? '+' : '') + v.toFixed(2) + '%';
}

function formatLargeNum(v) {
  if (!v || v === 0) return '--';
  if (v >= 100000000) return (v / 100000000).toFixed(2) + '亿';
  if (v >= 10000) return (v / 10000).toFixed(2) + '万';
  return v.toFixed(2);
}

function getChangeClass(v) {
  if (v > 0) return 'up';
  if (v < 0) return 'down';
  return '';
}

// ─── 时钟 ───────────────────────────────────────────────────────────

function updateClock() {
  const now = new Date();
  const t = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  const el = $('status-time');
  if (el) el.textContent = t;
}
setInterval(updateClock, 10000);
updateClock();

// ─── Tab切换 ───────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const tab = this.dataset.tab;
    $(`page-${tab}`).classList.add('active');

    // 进入页面时刷新数据
    if (tab === 'home') refreshAll();
    if (tab === 'settings') loadSettings();
  });
});

// ─── 大盘概况 ───────────────────────────────────────────────────────

function refreshMarket() {
  apiGet('/api/market').then(data => {
    if (data.error) return;

    const updateItem = (id, price, chg) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.querySelector('.market-price').textContent = formatPrice(price);
      const chgEl = el.querySelector('.market-change');
      chgEl.textContent = formatChange(chg);
      chgEl.className = 'market-change ' + getChangeClass(chg);
    };

    updateItem('market-sh', data.sh_price, data.sh_change_pct);
    updateItem('market-sz', data.sz_price, data.sz_change_pct);
    updateItem('market-cy', data.cy_price, data.cy_change_pct);
  }).catch(() => {});
}

// ─── 自选股列表 ─────────────────────────────────────────────────────

function refreshWatchlist() {
  apiGet('/api/watchlist').then(items => {
    const container = $('watchlist-container');
    if (!container) return;

    if (!items || items.length === 0) {
      container.innerHTML = '<div class="hint">暂无自选股，去搜索页添加吧</div>';
      return;
    }

    let html = '';
    items.forEach((item, idx) => {
      const q = item.quote || {};
      const l = item.lamp || {};
      const cp = q.change_pct;

      html += `<div class="stock-card" onclick="showDetail('${item.code}')">
        <div class="row1">
          <span class="code">${item.code}</span>
          <span class="name">${item.name || q.name || '--'}</span>
        </div>
        <div class="row2">
          <span class="price ${getChangeClass(cp)}">${formatPrice(q.price)}</span>
          <span class="change ${getChangeClass(cp)}">${formatChange(cp)}</span>
        </div>
        <div class="lamp-row">
          ${renderLampItem('区间', l.qujian)}
          ${renderLampItem('走势', l.zoushi)}
          ${renderLampItem('板块', l.bankuai)}
          ${renderLampItem('量价', l.liangjia)}
          <span class="signal-badge ${l.all_red ? 'buy' : l.red_count >= 3 ? 'caution' : l.red_count >= 2 ? 'watch' : 'leave'}">
            ${l.signal || '--'}
          </span>
        </div>
      </div>`;
    });

    container.innerHTML = html;
  }).catch(err => {
    const container = $('watchlist-container');
    if (container) container.innerHTML = '<div class="error-msg">加载失败，请检查网络</div>';
  });
}

function renderLampItem(label, value) {
  const clazz = value ? 'red' : 'green';
  const dot = value ? '🔴' : '🟢';
  return `<span class="lamp-item ${clazz}"><span class="lamp-dot">${dot}</span>${label}</span>`;
}

// ─── 搜索 ───────────────────────────────────────────────────────────

let searchTimer = null;

function doSearch(keyword) {
  clearTimeout(searchTimer);
  if (!keyword || keyword.length < 1) {
    $('search-results').innerHTML = '<div class="hint">输入关键词开始搜索</div>';
    return;
  }

  searchTimer = setTimeout(() => {
    apiGet(`/api/search?keyword=${encodeURIComponent(keyword)}`).then(results => {
      const container = $('search-results');
      if (!results || results.length === 0) {
        container.innerHTML = `<div class="hint">未找到 "${keyword}" 相关股票</div>`;
        return;
      }

      let html = '';
      results.forEach(item => {
        html += `<div class="stock-card" onclick="showDetail('${item.code}')">
          <div class="row1">
            <span class="code">${item.code}</span>
            <span class="name">${item.name}</span>
          </div>
          <div class="row2">
            <span class="price">点击查看详情</span>
            <span class="change" style="font-size:11px;color:var(--text-muted);background:transparent;">${item.type || 'A股'}</span>
          </div>
        </div>`;
      });

      container.innerHTML = html;
    }).catch(() => {
      $('search-results').innerHTML = '<div class="error-msg">搜索失败</div>';
    });
  }, 300);
}

// ─── 详情页 ─────────────────────────────────────────────────────────

function showDetail(code) {
  // 切换到详情Tab
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('[data-tab="detail"]').classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  $('page-detail').classList.add('active');

  const container = $('detail-content');
  container.innerHTML = '<div class="loading">加载中...</div>';

  apiGet(`/api/detail?code=${code}`).then(data => {
    if (data.error) {
      container.innerHTML = `<div class="error-msg">${data.error}</div>`;
      return;
    }

    const q = data.quote || {};
    const kline = data.kline || [];
    const l = data.lamp || {};
    const ind = data.indicators || {};
    const cp = q.change_pct;

    let html = '';

    // 头部信息
    html += `<div class="detail-header">
      <div class="name-code">${q.name || '--'} (${q.code || code})</div>
      <div class="price-row">
        <span class="price ${getChangeClass(cp)}">${formatPrice(q.price)}</span>
        <span class="change ${getChangeClass(cp)}">${formatChange(cp)}</span>
      </div>
      <div class="info-grid">
        <span>最高 <b>${formatPrice(q.high)}</b></span>
        <span>最低 <b>${formatPrice(q.low)}</b></span>
        <span>开盘 <b>${formatPrice(q.open)}</b></span>
        <span>昨收 <b>${formatPrice(q.pre_close)}</b></span>
        <span>成交量 <b>${formatLargeNum(q.volume)}手</b></span>
        <span>成交额 <b>${formatLargeNum(q.amount)}</b></span>
        <span>换手率 <b>${q.turnover_rate ? q.turnover_rate.toFixed(2) + '%' : '--'}</b></span>
        <span>振幅 <b>${q.amplitude ? q.amplitude.toFixed(2) + '%' : '--'}</b></span>
        <span>市盈率 <b>${q.pe ? q.pe.toFixed(2) : '--'}</b></span>
      </div>
    </div>`;

    // K线图
    html += `<div class="kline-section">
      <h3>📈 K线简图（最近${kline.length}个交易日）</h3>
      <div id="kline-chart">${renderKlineChart(kline)}</div>
    </div>`;

    // 四灯
    html += `<div class="lamp-section">
      <h3>💡 四灯决策指示</h3>
      <div class="lamp-grid">
        <div class="lamp-cell ${l.qujian ? 'red' : 'green'}">
          <div class="lamp-icon">${l.qujian ? '🔴' : '🟢'}</div>
          <div class="lamp-label">区间</div>
        </div>
        <div class="lamp-cell ${l.zoushi ? 'red' : 'green'}">
          <div class="lamp-icon">${l.zoushi ? '🔴' : '🟢'}</div>
          <div class="lamp-label">走势</div>
        </div>
        <div class="lamp-cell ${l.bankuai ? 'red' : 'green'}">
          <div class="lamp-icon">${l.bankuai ? '🔴' : '🟢'}</div>
          <div class="lamp-label">板块</div>
        </div>
        <div class="lamp-cell ${l.liangjia ? 'red' : 'green'}">
          <div class="lamp-icon">${l.liangjia ? '🔴' : '🟢'}</div>
          <div class="lamp-label">量价</div>
        </div>
      </div>
      <div class="lamp-signal" style="color: ${l.all_red ? 'var(--red)' : l.red_count >= 3 ? 'var(--yellow)' : l.red_count >= 2 ? 'var(--blue)' : 'var(--green)'}">
        ${l.signal || '--'} (${l.red_count || 0}/4 红灯)
      </div>
    </div>`;

    // 技术指标
    html += `<div class="indicator-section">
      <h3>📐 技术指标摘要</h3>
      <div class="indicator-grid">
        <div class="indicator-item"><span class="label">MA5</span><span class="value">${ind.ma5 !== null && ind.ma5 !== undefined ? ind.ma5.toFixed(2) : '--'}</span></div>
        <div class="indicator-item"><span class="label">MA10</span><span class="value">${ind.ma10 !== null && ind.ma10 !== undefined ? ind.ma10.toFixed(2) : '--'}</span></div>
        <div class="indicator-item"><span class="label">MA20</span><span class="value">${ind.ma20 !== null && ind.ma20 !== undefined ? ind.ma20.toFixed(2) : '--'}</span></div>
        <div class="indicator-item"><span class="label">20日波动率</span><span class="value">${ind.volatility_20 !== null && ind.volatility_20 !== undefined ? ind.volatility_20.toFixed(2) + '%' : '--'}</span></div>
        <div class="indicator-item"><span class="label">日涨跌幅</span><span class="value" style="color: ${ind.daily_change > 0 ? 'var(--red)' : ind.daily_change < 0 ? 'var(--green)' : ''}">${ind.daily_change !== null && ind.daily_change !== undefined ? ind.daily_change.toFixed(2) + '%' : '--'}</span></div>
      </div>
    </div>`;

    // 操作按钮
    html += `<div class="detail-actions" id="detail-actions">
      <button class="btn-add-watch" onclick="toggleWatchlist('${code}', '${q.name || ''}')">☆ 加入自选股</button>
      <button class="btn-refresh-detail" onclick="showDetail('${code}')">🔄 刷新</button>
    </div>`;

    container.innerHTML = html;

    // 检查是否已在自选股
    apiGet(`/api/watchlist/check?code=${code}`).then(r => {
      const btn = document.querySelector('.btn-add-watch');
      if (btn && r.in_watchlist) {
        btn.textContent = '★ 已在自选股';
        btn.className = 'btn-remove-watch';
        btn.onclick = function() {
          apiPost('/api/watchlist/remove', { code }).then(() => {
            showDetail(code);
            refreshAll();
          });
        };
      }
    });
  }).catch(() => {
    container.innerHTML = '<div class="error-msg">获取详情失败，请检查网络连接</div>';
  });
}

// ─── 字符K线图渲染 ──────────────────────────────────────────────────

function renderKlineChart(kline) {
  if (!kline || kline.length < 2) {
    return '<div class="hint">数据不足</div>';
  }

  const W = Math.min(kline.length, 50);
  const H = 10;
  const data = kline.slice(-W);
  const n = data.length;

  // 计算价格范围
  let minP = Infinity, maxP = -Infinity;
  data.forEach(d => {
    if (d.low < minP) minP = d.low;
    if (d.high > maxP) maxP = d.high;
  });
  if (maxP - minP < 0.01) { minP -= 0.1; maxP += 0.1; }

  let chart = '';
  for (let row = 0; row < H; row++) {
    let line = '';
    const priceLevel = maxP - ((maxP - minP) * row / (H - 1));

    // Y轴标签
    if (row % 2 === 0) {
      line += priceLevel.toFixed(2).padStart(8) + ' ';
    } else {
      line += '         ';
    }

    for (let col = 0; col < n; col++) {
      const d = data[col];
      const high = d.high, low = d.low;
      const open = d.open, close = d.close;
      const isUp = close >= open;
      const candleTop = Math.max(open, close);
      const candleBot = Math.min(open, close);

      if (priceLevel <= high && priceLevel >= low) {
        if (priceLevel <= candleTop && priceLevel >= candleBot) {
          line += isUp ? '█' : '▓';
        } else {
          line += '│';
        }
      } else {
        line += ' ';
      }
    }
    chart += line + '\n';
  }

  // X轴日期
  let xAxis = '         ';
  const step = Math.max(1, Math.floor(n / 8));
  for (let i = 0; i < n; i++) {
    if (i % step === 0) {
      xAxis += data[i].date.slice(-5).replace('-', '/');
      xAxis += ' '.repeat(Math.max(1, step - 4));
    } else {
      xAxis += ' ';
    }
  }

  chart += xAxis;
  return `<pre>${chart}</pre>`;
}

// ─── 自选股管理 ─────────────────────────────────────────────────────

function toggleWatchlist(code, name) {
  apiGet(`/api/watchlist/check?code=${code}`).then(r => {
    if (r.in_watchlist) {
      apiPost('/api/watchlist/remove', { code }).then(() => {
        showDetail(code);
        refreshAll();
      });
    } else {
      apiPost('/api/watchlist/add', { code, name }).then(() => {
        showDetail(code);
        refreshAll();
      });
    }
  });
}

// ─── 设置页 ─────────────────────────────────────────────────────────

function loadSettings() {
  apiGet('/api/settings').then(data => {
    document.querySelectorAll('.interval-btn').forEach(btn => {
      btn.classList.toggle('active', parseInt(btn.dataset.interval) === data.refresh_interval);
    });
  });

  // 加载自选股管理列表
  apiGet('/api/watchlist').then(items => {
    const container = $('watchlist-manage');
    if (!items || items.length === 0) {
      container.innerHTML = '<div class="hint">暂无自选股</div>';
      return;
    }

    let html = '';
    items.forEach(item => {
      const q = item.quote || {};
      html += `<div class="watchlist-manage-item">
        <span class="info">${item.code} ${item.name || q.name || '--'}</span>
        <button class="btn-del" onclick="removeAndRefresh('${item.code}')">删除</button>
      </div>`;
    });
    container.innerHTML = html;
  });
}

function removeAndRefresh(code) {
  apiPost('/api/watchlist/remove', { code }).then(() => {
    refreshAll();
    loadSettings();
  });
}

function setInterval(sec) {
  apiPost('/api/settings/interval', { interval: sec }).then(() => {
    document.querySelectorAll('.interval-btn').forEach(btn => {
      btn.classList.toggle('active', parseInt(btn.dataset.interval) === sec);
    });
  });
}

// ─── 全局刷新 ───────────────────────────────────────────────────────

function refreshAll() {
  refreshMarket();
  refreshWatchlist();
}

// ─── 自动刷新 ───────────────────────────────────────────────────────

let autoRefreshTimer = null;

function startAutoRefresh() {
  // 每30秒刷新一次大盘和自选股（后台）
  autoRefreshTimer = setInterval(() => {
    refreshMarket();
    // 如果当前在首页，也刷新自选股
    if ($('page-home').classList.contains('active')) {
      refreshWatchlist();
    }
  }, 30000);
}

// ─── 初始化 ─────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
  refreshAll();
  startAutoRefresh();
  updateClock();
});
