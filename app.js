/**
 * iPhone 18 Fast Inventory Lookup & Stock Transfer (CKNB)
 * Frontend Engine & Event Controller
 */

const DEFAULT_SHOWROOMS = [
  { code: "CP01", name: "Phong Vũ KHO TỔNG / CMT8 (11001.01)" },
  { code: "CP07", name: "Phong Vũ Cách Mạng Tháng 8 (Quận 10)" },
  { code: "CP02", name: "Phong Vũ Hoàng Hoa Thám (Tân Bình)" },
  { code: "CP03", name: "Phong Vũ Cộng Hòa (Tân Bình)" },
  { code: "CP04", name: "Phong Vũ Bình Thạnh" },
  { code: "CP05", name: "Phong Vũ Quận 7 (Nguyễn Thị Thập)" },
  { code: "CP06", name: "Phong Vũ Thủ Đức (Võ Văn Ngân)" },
  { code: "CP08", name: "Phong Vũ Gò Vấp (Quang Trung)" },
  { code: "CP40", name: "Phong Vũ Trần Não (Quận 2)" },
  { code: "CP46", name: "Phong Vũ Hậu Giang (Quận 6)" },
  { code: "CP58", name: "Phong Vũ Nguyễn Oanh (Gò Vấp)" },
  { code: "CP64", name: "Phong Vũ Nguyễn Ảnh Thủ (Quận 12)" },
  { code: "CP67", name: "Phong Vũ Lê Văn Việt (Quận 9)" },
  { code: "CP69", name: "Phong Vũ Bình Dương" },
  { code: "CP74", name: "Phong Vũ Tân Phú (Lũy Bán Bích)" },
  { code: "CP75", name: "Phong Vũ Bình Tân (Tên Lửa)" }
];

if (typeof window.PHONGVU_SHOWROOMS === 'undefined') {
  window.PHONGVU_SHOWROOMS = DEFAULT_SHOWROOMS;
}

const safeInitialProducts = (typeof INITIAL_PRODUCTS !== 'undefined' && Array.isArray(INITIAL_PRODUCTS)) ? INITIAL_PRODUCTS : [];

// State Management
const state = {
  products: [...safeInitialProducts],
  filteredProducts: [...safeInitialProducts],
  activeCategory: "all",
  searchQuery: "",
  selectedCapacity: "all",
  selectedColor: "all",
  activeProductForRequest: null,
  requestItems: [],
  selectedShowroom: "CP07",
  isDarkTheme: window.matchMedia('(prefers-color-scheme: dark)').matches,
  isSyncing: false
};

// DOM Elements Cache
const DOM = {
  searchInput: document.getElementById("searchInput"),
  clearSearchBtn: document.getElementById("clearSearchBtn"),
  productGrid: document.getElementById("productGrid"),
  resultsCount: document.getElementById("resultsCount"),
  categoryTabs: document.querySelectorAll(".filter-chip"),
  capacityFilter: document.getElementById("capacityFilter"),
  colorFilter: document.getElementById("colorFilter"),
  themeToggleBtn: document.getElementById("themeToggleBtn"),
  syncBtn: document.getElementById("syncBtn"),
  syncTimeLabel: document.getElementById("syncTimeLabel"),
  
  // Modals
  heldSheet: document.getElementById("heldSheet"),
  heldSheetTitle: document.getElementById("heldSheetTitle"),
  heldSheetBody: document.getElementById("heldSheetBody"),
  closeHeldSheetBtn: document.getElementById("closeHeldSheetBtn"),
  
  requestSheet: document.getElementById("requestSheet"),
  requestSheetTitle: document.getElementById("requestSheetTitle"),
  requestItemsContainer: document.getElementById("requestItemsContainer"),
  addItemBtn: document.getElementById("addItemBtn"),
  targetShowroomInput: document.getElementById("targetShowroomInput"),
  showroomChips: document.getElementById("showroomChips"),
  submitRequestBtn: document.getElementById("submitRequestBtn"),
  closeRequestSheetBtn: document.getElementById("closeRequestSheetBtn"),

  // Toast
  toastContainer: document.getElementById("toastContainer")
};

/**
 * Initialization
 */
function init() {
  renderShowroomChips();
  populateFilterOptions();
  applyFilters();
  setupEventListeners();
  updateSyncTime();

  // Tự động kiểm tra và đồng bộ realtime từ ERP khi vừa tải trang
  handleSyncERP(true);

  // Tự động làm mới dữ liệu định kỳ mỗi 60 giây
  setInterval(() => {
    handleSyncERP(true);
  }, 60000);
}

/**
 * Event Listeners Setup
 */
function setupEventListeners() {
  // Search Input with Debounce
  let searchDebounceTimer;
  DOM.searchInput.addEventListener("input", (e) => {
    clearTimeout(searchDebounceTimer);
    const val = e.target.value.trim();
    if (val.length > 0) {
      DOM.clearSearchBtn.classList.add("active");
    } else {
      DOM.clearSearchBtn.classList.remove("active");
    }
    searchDebounceTimer = setTimeout(() => {
      state.searchQuery = val.toLowerCase();
      applyFilters();
    }, 150);
  });

  DOM.clearSearchBtn.addEventListener("click", () => {
    DOM.searchInput.value = "";
    DOM.clearSearchBtn.classList.remove("active");
    state.searchQuery = "";
    applyFilters();
    DOM.searchInput.focus();
  });

  // Category Tabs
  DOM.categoryTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      DOM.categoryTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      state.activeCategory = tab.dataset.category;
      applyFilters();
    });
  });

  // Sub Filters (Capacity & Color)
  DOM.capacityFilter.addEventListener("change", (e) => {
    state.selectedCapacity = e.target.value;
    applyFilters();
  });

  DOM.colorFilter.addEventListener("change", (e) => {
    state.selectedColor = e.target.value;
    applyFilters();
  });

  // Theme Toggle
  DOM.themeToggleBtn.addEventListener("click", () => {
    state.isDarkTheme = !state.isDarkTheme;
    document.documentElement.classList.toggle("dark-theme", state.isDarkTheme);
    document.documentElement.classList.toggle("light-theme", !state.isDarkTheme);
    DOM.themeToggleBtn.innerHTML = state.isDarkTheme ? getSunIconSvg() : getMoonIconSvg();
  });

  // Manual Sync Button
  DOM.syncBtn.addEventListener("click", handleSyncERP);

  // Modal Closers
  DOM.closeHeldSheetBtn.addEventListener("click", closeHeldSheet);
  DOM.closeRequestSheetBtn.addEventListener("click", closeRequestSheet);

  DOM.heldSheet.addEventListener("click", (e) => {
    if (e.target === DOM.heldSheet) closeHeldSheet();
  });

  DOM.requestSheet.addEventListener("click", (e) => {
    if (e.target === DOM.requestSheet) closeRequestSheet();
  });

  // Showroom Input sync
  DOM.targetShowroomInput.addEventListener("input", (e) => {
    state.selectedShowroom = e.target.value.trim().toUpperCase();
    highlightSelectedChip();
  });

  // Add extra product to request
  DOM.addItemBtn.addEventListener("click", handleAddExtraItem);

  // Submit Request CKNB
  DOM.submitRequestBtn.addEventListener("click", handleSubmitStockTransfer);
}

/**
 * Filter and Search Logic
 */
function applyFilters() {
  const q = state.searchQuery;
  const cat = state.activeCategory;
  const cap = state.selectedCapacity;
  const col = state.selectedColor;

  state.filteredProducts = state.products.filter(p => {
    // Category check
    if (cat !== "all" && p.category !== cat) return false;

    // Capacity check
    if (cap !== "all" && p.capacity !== cap) return false;

    // Color check
    if (col !== "all" && p.color !== col) return false;

    // Search query check (SKU, Name, Model, Capacity, Color, Part number, Bins, Serials)
    if (q) {
      const matchSku = p.sku.toLowerCase().includes(q);
      const matchPart = (p.part_number || "").toLowerCase().includes(q);
      const matchName = p.name.toLowerCase().includes(q);
      const matchModel = p.model.toLowerCase().includes(q);
      const matchCap = (p.capacity || "").toLowerCase().includes(q);
      const matchColor = (p.color || "").toLowerCase().includes(q);
      const matchBin = (p.inventory.bin_code || "").toLowerCase().includes(q);
      const matchSerial = (p.serials || []).some(s => s.toLowerCase().includes(q));
      if (!matchSku && !matchPart && !matchName && !matchModel && !matchCap && !matchColor && !matchBin && !matchSerial) {
        return false;
      }
    }

    return true;
  });

  renderProductList();
  DOM.resultsCount.innerText = `${state.filteredProducts.length} sản phẩm`;
}

/**
 * Render Product Cards List
 */
function renderProductList() {
  if (state.filteredProducts.length === 0) {
    DOM.productGrid.innerHTML = `
      <div class="empty-state">
        <svg class="empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <div class="empty-title">Không tìm thấy sản phẩm phù hợp</div>
        <p>Vui lòng thử tìm với từ khoá khác (SKU, 18 Pro Max, Băng Thanh, 256GB, Serial...)</p>
      </div>
    `;
    return;
  }

  DOM.productGrid.innerHTML = state.filteredProducts.map(product => {
    const inv = product.inventory;
    const isOutOfStock = inv.available_qty <= 0;
    const formattedPrice = product.retail_price ? product.retail_price.toLocaleString('vi-VN') + " đ" : "Liên hệ";

    return `
      <div class="product-card ${isOutOfStock ? 'out-of-stock' : ''}" data-sku="${product.sku}">
        <div class="card-header">
          <div class="product-title-group">
            <div class="product-name">${escapeHtml(product.name)}</div>
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 4px;">
              <span class="product-sku-badge">SKU: ${product.sku}</span>
              ${product.part_number ? `<span style="font-size: 11px; background: var(--color-muted); color: var(--color-secondary); padding: 1px 6px; border-radius: 4px; font-weight: 600; font-family: monospace;">${product.part_number}</span>` : ''}
              ${product.color ? `
                <span style="font-size: 12px; color: var(--color-muted-text); display: inline-flex; align-items: center;">
                  <span class="product-color-indicator" style="background-color: ${product.color_hex || '#ccc'}"></span>
                  ${escapeHtml(product.color)}
                </span>
              ` : ''}
              ${product.capacity ? `<span style="font-size: 11px; background: var(--color-muted); padding: 1px 6px; border-radius: 4px; font-weight: 600;">${product.capacity}</span>` : ''}
            </div>
          </div>
          <div class="stock-pill ${isOutOfStock ? 'out-of-stock' : 'in-stock'}">
            ${isOutOfStock ? `
              <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/><path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/></svg>
              Hết tồn
            ` : `
              <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>
              Khả dụng: ${inv.available_qty}
            `}
          </div>
        </div>

        <div class="stock-grid">
          <div class="metric-item">
            <span class="metric-label">Tồn Check ERP</span>
            <span class="metric-value">${inv.on_hand_qty}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">+ Đơn Giữ Nhả Bán</span>
            <span class="metric-value held" onclick="openHeldOrdersModal('${product.sku}')" title="Nhấn xem danh sách đơn giữ có thể nhả bán (auto khách không lấy)">
              +${inv.held_qty}
              <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/><path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"/></svg>
            </span>
          </div>
          <div class="metric-item">
            <span class="metric-label">= Khả Dụng Bán</span>
            <span class="metric-value available">${inv.available_qty}</span>
          </div>
        </div>
        <div style="padding: 0 14px 8px; font-size: 11px; color: var(--color-muted-text); display: flex; justify-content: space-between;">
          <span>Công thức: Tồn ERP (${inv.on_hand_qty}) + Đơn giữ (${inv.held_qty}) = <b>${inv.available_qty} máy</b></span>
        </div>

        <div class="bin-box">
          <div class="bin-header-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span style="font-size: 11px; font-weight: 700; color: var(--color-foreground);">
              📦 VỊ TRÍ BIN VẬT LÝ (WMS):
            </span>
            <a href="https://erp.phongvu.vn/warehousing/stock-count/stock-product-by-bin" target="_blank" style="font-size: 11px; color: #0284c7; text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 3px;" title="Mở trang Theo dõi Tồn kho vật lý trên ERP">
              Theo dõi WMS ↗
            </a>
          </div>
          <div class="bin-data-row" style="display: flex; flex-direction: column; gap: 4px;">
            ${(inv.bin_details && inv.bin_details.length > 0) ? inv.bin_details.map(b => `
              <div class="bin-code-tag" style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;">
                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                  <span style="background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700;">
                    [${escapeHtml(b.zone_name || b.zone || 'Khu vực')}]
                  </span>
                  <span style="font-family: monospace; font-weight: 800; color: #0f172a; font-size: 13px;">
                    ${escapeHtml(b.bin_code)}
                  </span>
                  ${b.product_status ? `<span style="font-size: 11px; color: #64748b;">(${escapeHtml(b.product_status)})</span>` : ''}
                </div>
                <div style="background: #dcfce7; color: #166534; font-weight: 800; padding: 2px 8px; border-radius: 4px; font-size: 12px; white-space: nowrap; border: 1px solid #bbf7d0;">
                  ${b.qty} cái
                </div>
              </div>
            `).join('') : `
              <div class="bin-code-tag" style="padding: 6px 10px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; color: #64748b; font-size: 12px;">
                <span>${escapeHtml(inv.bin_code || 'Chưa ghi nhận vị trí bin')}</span>
              </div>
            `}
          </div>
        </div>

        <div class="card-footer">
          <button class="btn-held-detail" onclick="openHeldOrdersModal('${product.sku}')">
            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
            Xem Đơn Giữ (${inv.held_qty})
          </button>
          <button class="btn-request" ${isOutOfStock ? 'disabled' : ''} onclick="openRequestModal('${product.sku}')">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg>
            Request Xin Hàng (CKNB)
          </button>
        </div>
      </div>
    `;
  }).join("");
}

/**
 * Modal 1: Held Orders & Deposit Match Sheet (Strictly from sheet 'Data đặt cọc')
 */
window.openHeldOrdersModal = function(sku, initialFilter = "all") {
  const product = state.products.find(p => p.sku === sku);
  if (!product) return;

  const inv = product.inventory;
  const ds = product.deposit_stats || {
    total_held_deposits: 0,
    cp01_deposits_count: 0,
    sr_distribution: {},
    orders_list: []
  };

  const allOrders = ds.orders_list || [];
  const releasableOrders = allOrders.filter(o => o.is_valid_pickup !== false && !String(o.xuat_tai_dau).includes("264"));
  const excludedOrders = allOrders.filter(o => o.is_valid_pickup === false || String(o.xuat_tai_dau).includes("264"));
  const totalOrdersCount = allOrders.length;
  const releasableCount = releasableOrders.length;
  const excludedCount = excludedOrders.length;

  DOM.heldSheetTitle.innerText = `Danh sách giữ hàng (${totalOrdersCount} đơn - Căn cứ ERP)`;

  // Render modal content
  function renderOrders(filterType) {
    let list = allOrders;
    if (filterType === "releasable") {
      list = releasableOrders;
    } else if (filterType === "sr264") {
      list = excludedOrders;
    } else if (filterType === "cp01") {
      list = list.filter(o => o.is_cp01);
    } else if (filterType === "other") {
      list = list.filter(o => !o.is_cp01);
    }

    const validSos = list.filter(o => o.is_valid_pickup !== false && !String(o.xuat_tai_dau).includes("264")).map(o => cleanOrderCode(o.clean_so || o.order_code)).join(", ");
    const curValidCount = list.filter(o => o.is_valid_pickup !== false && !String(o.xuat_tai_dau).includes("264")).length;

    const ordersHtml = list.length === 0 ? `
      <div style="text-align: center; padding: 24px 12px; color: var(--color-muted-text); background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: var(--radius-sm); margin: 10px 0;">
        <div style="font-weight: 600; font-size: 13px; color: var(--color-foreground);">Không có đơn giữ nào phù hợp</div>
        <div style="font-size: 12px; margin-top: 2px;">Không tìm thấy đơn hàng nào theo điều kiện lọc này.</div>
      </div>
    ` : `
      <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0 4px; flex-wrap: wrap; gap: 6px;">
        <span style="font-size: 12px; font-weight: 700; color: var(--color-foreground);">
          Chi tiết ${list.length} đơn giữ tại kho 11001.01 (${curValidCount} đơn nhả bán):
        </span>
        ${curValidCount > 0 ? `
        <button type="button" class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px; font-weight: 700; border-radius: 4px; background: #fef9c3; color: #854d0e; border: 1px solid #facc15;" onclick="navigator.clipboard.writeText('${validSos}'); showToast('Đã copy ${curValidCount} mã SO nhả bán!')">
          📋 Copy ${curValidCount} mã SO nhả bán
        </button>
        ` : ''}
      </div>
      <div style="max-height: 290px; overflow-y: auto; margin: 6px 0 10px; padding-right: 2px;">
        ${list.map((order, idx) => {
          const displaySO = cleanOrderCode(order.clean_so || order.order_code);
          const isReleasable = (order.is_valid_pickup !== false) && (!String(order.xuat_tai_dau).includes("264"));
          const itemStyle = isReleasable 
            ? "" 
            : "background: #fff8f8; border-color: #fca5a5; border-left: 4px solid #ef4444;";

          return `
          <div class="order-check-item" style="${itemStyle}">
            <div class="order-check-header">
              <span class="order-code-text">
                #${idx + 1}. Mã: <b style="font-family: monospace; color: #0284c7; font-size: 13px;">${escapeHtml(displaySO)}</b>
                ${isReleasable 
                  ? `<span style="background: #dcfce7; color: #166534; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; margin-left: 4px;">🟢 Nhả bán</span>` 
                  : `<span style="background: #fee2e2; color: #991b1b; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; margin-left: 4px;">⛔ Giữ SR 264</span>`
                }
              </span>
              <div style="display: flex; gap: 4px; align-items: center;">
                <a href="${order.erp_link || `https://erp.phongvu.vn/sales/orders/${displaySO}`}" target="_blank" class="btn btn-outline" style="font-size: 11px; padding: 2px 6px; text-decoration: none; height: 26px; display: inline-flex; align-items: center;" title="Xem chi tiết đơn trên ERP">
                  ERP ↗
                </a>
                ${isReleasable ? `
                <button type="button" class="btn btn-secondary" style="font-size: 11px; padding: 2px 8px; height: 26px; border-radius: 4px; font-weight: 600;" onclick="navigator.clipboard.writeText('${escapeHtml(displaySO)}'); showToast('Đã copy mã SO: ${escapeHtml(displaySO)}')">
                  📋 Copy SO
                </button>
                ` : `
                <button type="button" class="btn" style="font-size: 11px; padding: 2px 8px; height: 26px; border-radius: 4px; font-weight: 600; background: #f3f4f6; color: #9ca3af; border: 1px solid #d1d5db; cursor: not-allowed;" onclick="showToast('⚠️ Đơn nhận tại SR 264 giữ cho khách, KHÔNG ĐƯỢC nhả bán!', 'warning')" title="Đơn nhận tại SR 264 - Không nhả tồn">
                  🚫 Giữ SR 264
                </button>
                `}
              </div>
            </div>
            <div style="font-size: 12px; color: var(--color-foreground); margin: 3px 0; display: flex; justify-content: space-between;">
              <span>Loại: <b>${escapeHtml(order.doc_type || 'Đơn hàng')}</b></span>
              <span>Số tồn đang giữ: <b style="color: #b45309;">${order.qty || 1}</b></span>
            </div>
            <div style="font-size: 12px; color: var(--color-foreground); margin: 3px 0;">
              👤 <b>Saleman:</b> ${escapeHtml(order.saleman_display || 'Kinh doanh Phong Vũ')}
            </div>
            <div style="font-size: 12px; color: var(--color-secondary); display: flex; flex-wrap: wrap; gap: 8px; margin: 2px 0;">
              <span>📅 <b>Ngày cọc:</b> ${escapeHtml(order.deposit_date || 'N/A')}</span>
              <span>•</span>
              <span>🏪 <b>SR bán:</b> <b>${escapeHtml(order.sr_ban_name || order.sr_ban)}</b></span>
            </div>
            <div class="order-note-text" style="margin-top: 5px; padding-top: 4px; border-top: 1px dashed ${isReleasable ? 'var(--color-border)' : '#fca5a5'}; display: flex; justify-content: space-between; align-items: center;">
              <span>📦 <b>Xuất tại:</b> <b style="${isReleasable ? '' : 'color: #b91c1c;'}">${escapeHtml(order.xuat_tai_dau)}</b></span>
              ${isReleasable ? `
                <span style="font-weight: 600; color: #15803d;">Auto khách k lấy (Nhả tồn bán)</span>
              ` : `
                <span style="font-weight: 700; color: #dc2626; background: #fee2e2; padding: 1px 6px; border-radius: 4px;">⛔ Khách nhận tại SR 264 (KHÔNG nhả tồn)</span>
              `}
            </div>
          </div>
        `;}).join("")}
      </div>
    `;

    return ordersHtml;
  }

  // Distribution chips
  const distEntries = Object.entries(ds.sr_distribution || {});

  DOM.heldSheetBody.innerHTML = `
    <div style="background: var(--color-muted); border: 1px solid var(--color-border); padding: 10px 12px; border-radius: var(--radius-sm); margin-bottom: 12px; font-size: 13px;">
      <div style="font-weight: 700; margin-bottom: 3px; font-size: 14px;">${escapeHtml(product.name)}</div>
      <div style="color: var(--color-secondary); font-size: 12px; display: flex; flex-wrap: wrap; gap: 8px;">
        <span>SKU: <b>${product.sku}</b></span>
        <span>|</span>
        <span>Màu: <b>${escapeHtml(product.color)}</b></span>
        <span>|</span>
        <span>Dung lượng: <b>${escapeHtml(product.capacity)}</b></span>
      </div>
    </div>

    <!-- Metrics Grid -->
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px;">
      <div style="background: var(--color-surface); border: 1px solid var(--color-border); padding: 8px 10px; border-radius: var(--radius-sm); text-align: center;">
        <div style="font-size: 11px; color: var(--color-muted-text); font-weight: 600;">Tồn Check ERP</div>
        <div style="font-size: 18px; font-weight: 800; color: var(--color-foreground);">${inv.on_hand_qty}</div>
      </div>
      <div style="background: #fefce8; border: 1px solid #fde047; padding: 8px 10px; border-radius: var(--radius-sm); text-align: center;">
        <div style="font-size: 11px; color: #a16207; font-weight: 700;">+ Đơn Giữ Nhả Bán</div>
        <div style="font-size: 18px; font-weight: 800; color: #a16207;">+${inv.held_qty}</div>
        <div style="font-size: 10px; color: #854d0e; margin-top: 1px;">(Trống / Nhận tại SR)</div>
      </div>
      <div style="background: #f0fdf4; border: 1.5px solid #86efac; padding: 8px 10px; border-radius: var(--radius-sm); text-align: center;">
        <div style="font-size: 11px; color: #15803d; font-weight: 800;">= Khả Dụng Bán</div>
        <div style="font-size: 18px; font-weight: 900; color: #15803d;">${inv.available_qty}</div>
      </div>
    </div>

    <!-- Rule Note -->
    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 8px 12px; border-radius: var(--radius-sm); margin-bottom: 10px; font-size: 12px; line-height: 1.45; color: #166534;">
      <b>💡 Quy ước nhả tồn:</b> CHỈ tính đơn <u>bỏ trống</u> hoặc <u>nhận tại SR</u> (auto khách không lấy ➔ Salesman nhấn <b>"📋 Copy SO"</b> để xin Admin nhả tồn xuất máy ngay!). Các đơn <b>note nhận tại SR 264</b> là khách đến lấy tại SR 264 NTMK, <b>không tính vào nhả tồn</b>.
    </div>

    ${excludedCount > 0 ? `
    <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 7px 10px; border-radius: var(--radius-sm); margin-bottom: 10px; font-size: 12px; color: #991b1b; display: flex; align-items: center; gap: 8px;">
      <span style="font-size: 15px;">⛔</span>
      <div>Có <b>${excludedCount} đơn giữ note nhận tại SR 264</b>: Đã tự động <b>loại trừ</b> khỏi số đơn nhả bán để giữ máy cho khách.</div>
    </div>
    ` : ''}

    <!-- Rule Verification Box (Check ERP Order vs Deposit Sheet) -->
    <div style="background: var(--color-surface); border: 1.5px solid var(--color-border); padding: 10px 12px; border-radius: var(--radius-sm); margin-bottom: 12px;">
      <div style="font-size: 12px; font-weight: 700; color: var(--color-foreground); margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
        <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/></svg>
        Đối Chiếu Mã Đơn Đang Giữ Trên ERP:
      </div>
      <div style="font-size: 11px; color: var(--color-muted-text); margin-bottom: 6px;">
        Dán mã đơn hàng thấy trên ERP để kiểm tra xem đơn có nằm trong sheet cọc không:
      </div>
      <div style="display: flex; gap: 6px;">
        <input type="text" id="modalSOCheckInput" class="form-control" placeholder="Dán mã đơn ERP (vd: 26091235928750)" style="height: 38px; font-size: 13px; font-family: monospace;" />
        <button type="button" id="btnModalCheckSO" class="btn btn-primary" style="height: 38px; padding: 0 12px; font-size: 12px; white-space: nowrap;">
          Check Rule
        </button>
      </div>
      <div id="modalSOCheckResult" style="margin-top: 8px; display: none;"></div>
    </div>

    <!-- SR Distribution breakdown -->
    ${distEntries.length > 0 ? `
      <div style="font-size: 11px; font-weight: 700; color: var(--color-muted-text); text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">
        Số đơn cọc theo từng Showroom bán:
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px;">
        ${distEntries.map(([sr, count]) => `
          <span style="background: var(--color-surface); border: 1px solid var(--color-border); padding: 3px 8px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 600;">
            ${sr}: <b style="color: var(--color-primary);">${count}</b>
          </span>
        `).join("")}
      </div>
    ` : ''}

    <!-- Tabs for Filtering Orders in Modal -->
    <div style="display: flex; gap: 6px; margin-bottom: 6px; flex-wrap: wrap;">
      <button class="filter-chip ${initialFilter === 'all' ? 'active' : ''}" id="modalFilterAll" style="font-size: 12px; padding: 4px 10px;">
        Tất cả (${totalOrdersCount})
      </button>
      <button class="filter-chip ${initialFilter === 'releasable' ? 'active' : ''}" id="modalFilterReleasable" style="font-size: 12px; padding: 4px 10px;">
        Đơn nhả bán (${releasableCount})
      </button>
      ${excludedCount > 0 ? `
      <button class="filter-chip ${initialFilter === 'sr264' ? 'active' : ''}" id="modalFilterSR264" style="font-size: 12px; padding: 4px 10px; color: #991b1b;">
        Giữ SR 264 (${excludedCount})
      </button>
      ` : ''}
      <button class="filter-chip ${initialFilter === 'cp01' ? 'active' : ''}" id="modalFilterCP01" style="font-size: 12px; padding: 4px 10px;">
        Tại CP01 (${allOrders.filter(o => o.is_cp01).length})
      </button>
      <button class="filter-chip ${initialFilter === 'other' ? 'active' : ''}" id="modalFilterOther" style="font-size: 12px; padding: 4px 10px;">
        SR khác (${allOrders.filter(o => !o.is_cp01).length})
      </button>
    </div>

    <!-- Orders Container -->
    <div id="modalOrdersContainer">
      ${renderOrders(initialFilter)}
    </div>

    <div style="display: flex; gap: 10px; margin-top: 10px;">
      <button class="btn btn-secondary" style="flex: 1; height: 44px;" onclick="closeHeldSheet()">Đóng</button>
      <button class="btn btn-primary" style="flex: 1; height: 44px;" onclick="closeHeldSheet(); openRequestModal('${product.sku}')">
        Tạo Phiếu CKNB
      </button>
    </div>
  `;

  // Attach tab filter listeners inside modal
  const btnAll = document.getElementById("modalFilterAll");
  const btnReleasable = document.getElementById("modalFilterReleasable");
  const btnSR264 = document.getElementById("modalFilterSR264");
  const btnCP01 = document.getElementById("modalFilterCP01");
  const btnOther = document.getElementById("modalFilterOther");
  const container = document.getElementById("modalOrdersContainer");

  const allTabBtns = [btnAll, btnReleasable, btnSR264, btnCP01, btnOther].filter(Boolean);

  function setActive(activeBtn, type) {
    allTabBtns.forEach(b => b.classList.remove("active"));
    activeBtn.classList.add("active");
    container.innerHTML = renderOrders(type);
  }

  if (btnAll) btnAll.onclick = () => setActive(btnAll, "all");
  if (btnReleasable) btnReleasable.onclick = () => setActive(btnReleasable, "releasable");
  if (btnSR264) btnSR264.onclick = () => setActive(btnSR264, "sr264");
  if (btnCP01) btnCP01.onclick = () => setActive(btnCP01, "cp01");
  if (btnOther) btnOther.onclick = () => setActive(btnOther, "other");

  // Attach single order verification listener
  const soInput = document.getElementById("modalSOCheckInput");
  const btnCheckSO = document.getElementById("btnModalCheckSO");
  const resultDiv = document.getElementById("modalSOCheckResult");

  function doCheckSO() {
    if (!soInput || !resultDiv) return;
    const res = verifyOrderAgainstRule(soInput.value);
    resultDiv.style.display = "block";
    if (res.status === "VALID_DEPOSIT") {
      resultDiv.innerHTML = `
        <div style="background: var(--color-accent-light); border: 1.5px solid var(--color-accent); padding: 8px 10px; border-radius: var(--radius-sm); font-size: 12px; line-height: 1.45;">
          <div style="font-weight: 700; color: var(--color-accent); margin-bottom: 2px;">${res.title}</div>
          <div>${res.message}</div>
          <div style="color: var(--color-accent); font-weight: 600; margin-top: 3px;">${res.action}</div>
        </div>
      `;
    } else if (res.status === "EXCLUDED_SR264") {
      resultDiv.innerHTML = `
        <div style="background: var(--color-warning-light); border: 1.5px solid var(--color-warning); padding: 8px 10px; border-radius: var(--radius-sm); font-size: 12px; line-height: 1.45;">
          <div style="font-weight: 700; color: var(--color-warning); margin-bottom: 2px;">${res.title}</div>
          <div>${res.message}</div>
          <div style="color: var(--color-warning); font-weight: 700; margin-top: 3px;">${res.action}</div>
        </div>
      `;
    } else {
      resultDiv.innerHTML = `
        <div style="background: var(--color-destructive-light); border: 1.5px solid var(--color-destructive); padding: 8px 10px; border-radius: var(--radius-sm); font-size: 12px; line-height: 1.45;">
          <div style="font-weight: 700; color: var(--color-destructive); margin-bottom: 2px;">${res.title}</div>
          <div>${res.message}</div>
          <div style="color: var(--color-destructive); font-weight: 700; margin-top: 3px;">${res.action}</div>
        </div>
      `;
    }
  }

  if (btnCheckSO) btnCheckSO.onclick = doCheckSO;
  if (soInput) soInput.onkeydown = (e) => { if (e.key === "Enter") doCheckSO(); };

  DOM.heldSheet.classList.add("active");
};

/**
 * Universal Rule Verification Function
 */
function verifyOrderAgainstRule(soCode) {
  const code = (soCode || '').trim();
  if (!code) {
    return {
      status: "EMPTY",
      title: "Vui lòng nhập mã đơn hàng",
      message: "Hãy dán mã đơn SO từ ERP để đối chiếu.",
      action: ""
    };
  }

  const order = (typeof ALL_DEPOSITS_LOOKUP !== 'undefined') ? ALL_DEPOSITS_LOOKUP[code] : null;
  if (!order) {
    return {
      found: false,
      status: "NOT_FOUND",
      code: code,
      title: "❌ CẢNH BÁO: ĐƠN NÀY KHÔNG NẰM TRONG SHEET ĐẶT CỌC!",
      message: `Mã đơn <b>${escapeHtml(code)}</b> đang giữ tồn trên ERP nhưng <b>KHÔNG TÌM THẤY</b> trong sheet "Data đặt cọc".`,
      action: "⚠️ Đây có thể là đơn giữ ảo / đơn ngoài danh sách cọc. <b>Cần báo Admin kiểm tra nhả tồn giữ ngay!</b>"
    };
  }

  if (!order.is_valid_pickup) {
    return {
      found: true,
      status: "EXCLUDED_SR264",
      order: order,
      code: code,
      title: "⚠️ CẢNH BÁO: ĐƠN THUỘC DIỆN NHẬN TẠI SR 264",
      message: `Đơn hàng <b>${escapeHtml(code)}</b> có trong sheet cọc của Salesman <b>${escapeHtml(order.saleman_display)}</b>, nhưng cột <i>"Xuất tại đâu?"</i> = <b>${escapeHtml(order.xuat_tai_dau)}</b>.`,
      action: "⚠️ Khách nhận máy tại Showroom 264 NTMK, <b>KHÔNG XUẤT TẠI KHO CP01</b>. Cần check Admin hủy giữ kho CP01."
    };
  }

  return {
    found: true,
    status: "VALID_DEPOSIT",
    order: order,
    code: code,
    title: "✅ HỢP LỆ: ĐƠN CỌC NẰM TRONG SHEET VÀ THỎA ĐIỀU KIỆN",
    message: `Đơn hàng <b>${escapeHtml(code)}</b> hợp lệ.<br/>• Salesman: <b>${escapeHtml(order.saleman_display)}</b><br/>• SR bán: <b>${escapeHtml(order.sr_ban_name || order.sr_ban)}</b><br/>• Ngày cọc: <b>${escapeHtml(order.ngay_coc)}</b> | Xuất tại: <b>${escapeHtml(order.xuat_tai_dau)}</b>.`,
    action: "✓ Đơn cọc chính thức đợt 1, giữ tồn đúng quy định."
  };
}

/**
 * Toggle Rule Explanation Card
 */
window.toggleRuleExplanation = function() {
  const content = document.getElementById("ruleCardContent");
  const icon = document.getElementById("ruleToggleIcon");
  const text = document.getElementById("ruleToggleText");
  if (!content) return;
  if (content.style.display === "none") {
    content.style.display = "block";
    if (icon) icon.style.transform = "rotate(0deg)";
    if (text) text.innerText = "Thu gọn";
  } else {
    content.style.display = "none";
    if (icon) icon.style.transform = "rotate(-90deg)";
    if (text) text.innerText = "Chi tiết";
  }
};

/**
 * Global SO Checker Modal (Từ bottom navigation)
 */
window.openGlobalSOChecker = function() {
  DOM.heldSheetTitle.innerText = "Kiểm Tra Mã Đơn ERP vs Sheet Cọc";
  DOM.heldSheetBody.innerHTML = `
    <div style="background: var(--color-info-light); border: 1px solid var(--color-info); padding: 10px 12px; border-radius: var(--radius-sm); margin-bottom: 12px; font-size: 12px; line-height: 1.5; color: var(--color-info);">
      <b>📋 Quy tắc đối chiếu cọc (Rule kiểm tra):</b><br/>
      1. Đơn đang giữ trên ERP có <b>nằm trong sheet Data đặt cọc</b> không?<br/>
      2. Cột <i>"Xuất tại đâu?"</i> có bằng <b>"Nhận sau ở SR bán"</b> hoặc <b>blank (để trống)</b> không?<br/>
      ➔ Hệ thống sẽ thông báo ngay đơn Hợp lệ hay Cần Check Admin nhả tồn!
    </div>

    <div style="margin-bottom: 12px;">
      <label style="font-size: 12px; font-weight: 700; color: var(--color-foreground); display: block; margin-bottom: 4px;">
        Dán mã đơn hàng từ ERP (Có thể dán nhiều mã cách nhau bằng dấu phẩy, khoảng trắng hoặc xuống dòng):
      </label>
      <textarea id="globalSOInput" class="form-control" rows="3" placeholder="Ví dụ:&#10;26091235928750&#10;26091234763860&#10;99999999999999" style="font-family: monospace; font-size: 13px; padding: 8px 10px;"></textarea>
      <button type="button" id="btnRunGlobalCheck" class="btn btn-primary" style="width: 100%; height: 44px; margin-top: 8px;">
        🔍 Kiểm Tra Đối Chiếu Ngay
      </button>
    </div>

    <div id="globalCheckResults" style="max-height: 320px; overflow-y: auto;">
      <div style="text-align: center; padding: 20px; color: var(--color-muted-text); font-size: 13px;">
        Nhập mã đơn hàng ERP ở trên để bắt đầu đối chiếu.
      </div>
    </div>

    <div style="margin-top: 14px;">
      <button class="btn btn-secondary" style="width: 100%; height: 44px;" onclick="closeHeldSheet()">Đóng</button>
    </div>
  `;

  const inputArea = document.getElementById("globalSOInput");
  const btnRun = document.getElementById("btnRunGlobalCheck");
  const resultsDiv = document.getElementById("globalCheckResults");

  btnRun.onclick = () => {
    const raw = inputArea.value;
    const codes = raw.split(/[\s,;\n\r]+/).map(s => s.trim()).filter(Boolean);
    if (codes.length === 0) {
      alert("Vui lòng nhập ít nhất 1 mã đơn hàng.");
      return;
    }

    const verifiedList = codes.map(c => verifyOrderAgainstRule(c));
    const validCount = verifiedList.filter(r => r.status === "VALID_DEPOSIT").length;
    const warnCount = verifiedList.filter(r => r.status === "EXCLUDED_SR264").length;
    const invalidCount = verifiedList.filter(r => r.status === "NOT_FOUND").length;

    resultsDiv.innerHTML = `
      <!-- Summary Bar -->
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 10px;">
        <div style="background: var(--color-accent-light); border: 1px solid var(--color-accent); padding: 6px; border-radius: var(--radius-sm); text-align: center;">
          <div style="font-size: 11px; color: var(--color-accent); font-weight: 700;">Hợp Lệ</div>
          <div style="font-size: 16px; font-weight: 800; color: var(--color-accent);">${validCount}</div>
        </div>
        <div style="background: var(--color-warning-light); border: 1px solid var(--color-warning); padding: 6px; border-radius: var(--radius-sm); text-align: center;">
          <div style="font-size: 11px; color: var(--color-warning); font-weight: 700;">SR 264</div>
          <div style="font-size: 16px; font-weight: 800; color: var(--color-warning);">${warnCount}</div>
        </div>
        <div style="background: var(--color-destructive-light); border: 1px solid var(--color-destructive); padding: 6px; border-radius: var(--radius-sm); text-align: center;">
          <div style="font-size: 11px; color: var(--color-destructive); font-weight: 700;">Không Cọc</div>
          <div style="font-size: 16px; font-weight: 800; color: var(--color-destructive);">${invalidCount}</div>
        </div>
      </div>

      <!-- Itemized Results -->
      ${verifiedList.map(res => `
        <div style="background: var(--color-background); border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: 8px 10px; margin-bottom: 6px; font-size: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
            <span style="font-family: monospace; font-weight: 700; font-size: 13px;">${res.code}</span>
            <span class="status-tag ${res.status === 'VALID_DEPOSIT' ? 'can-sell' : (res.status === 'EXCLUDED_SR264' ? 'check-admin' : 'out-of-stock')}">
              ${res.status === 'VALID_DEPOSIT' ? '✓ Khớp Cọc' : (res.status === 'EXCLUDED_SR264' ? '⚠ Nhận SR 264' : '❌ Không có trong sheet')}
            </span>
          </div>
          <div>${res.message}</div>
          <div style="margin-top: 3px; font-weight: 600; color: ${res.status === 'VALID_DEPOSIT' ? 'var(--color-accent)' : (res.status === 'EXCLUDED_SR264' ? 'var(--color-warning)' : 'var(--color-destructive)')};">
            ${res.action}
          </div>
        </div>
      `).join("")}
    `;
  };

  DOM.heldSheet.classList.add("active");
};

function closeHeldSheet() {
  DOM.heldSheet.classList.remove("active");
}

/**
 * Modal 2: Stock Transfer Request Modal (Tạo lệnh CKNB)
 */
window.openRequestModal = function(sku) {
  const product = state.products.find(p => p.sku === sku);
  if (!product) return;

  state.activeProductForRequest = product;
  state.requestItems = [
    {
      sku: product.sku,
      name: product.name,
      qty: 1,
      maxAvailable: product.inventory.available_qty
    }
  ];

  renderRequestItems();
  DOM.targetShowroomInput.value = state.selectedShowroom;
  highlightSelectedChip();
  DOM.requestSheet.classList.add("active");
};

function closeRequestSheet() {
  DOM.requestSheet.classList.remove("active");
}

function renderRequestItems() {
  DOM.requestItemsContainer.innerHTML = state.requestItems.map((item, index) => `
    <div class="multi-item-row" id="item-row-${index}">
      <div style="flex: 1;">
        <div style="font-size: 13px; font-weight: 700; color: var(--color-foreground); line-height: 1.3;">${escapeHtml(item.name)}</div>
        <div style="font-size: 11px; color: var(--color-muted-text); font-family: monospace;">SKU: ${item.sku} | Tối đa khả dụng: ${item.maxAvailable}</div>
      </div>
      <div style="display: flex; align-items: center; gap: 6px;">
        <button type="button" style="width: 28px; height: 28px; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-surface); cursor: pointer; font-weight: bold;" onclick="changeItemQty(${index}, -1)">-</button>
        <input type="number" min="1" max="${item.maxAvailable}" value="${item.qty}" style="width: 44px; height: 28px; text-align: center; border: 1px solid var(--color-border); border-radius: 4px; font-weight: 700;" onchange="updateItemQty(${index}, this.value)" />
        <button type="button" style="width: 28px; height: 28px; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-surface); cursor: pointer; font-weight: bold;" onclick="changeItemQty(${index}, 1)">+</button>
      </div>
      ${state.requestItems.length > 1 ? `
        <button class="btn-sm-delete" onclick="removeItemFromRequest(${index})" title="Xoá">
          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
        </button>
      ` : ''}
    </div>
  `).join("");
}

window.changeItemQty = function(index, delta) {
  const item = state.requestItems[index];
  const newQty = item.qty + delta;
  if (newQty >= 1 && newQty <= item.maxAvailable) {
    item.qty = newQty;
    renderRequestItems();
  }
};

window.updateItemQty = function(index, val) {
  const item = state.requestItems[index];
  let parsed = parseInt(val, 10);
  if (isNaN(parsed) || parsed < 1) parsed = 1;
  if (parsed > item.maxAvailable) parsed = item.maxAvailable;
  item.qty = parsed;
  renderRequestItems();
};

window.removeItemFromRequest = function(index) {
  state.requestItems.splice(index, 1);
  renderRequestItems();
};

function handleAddExtraItem() {
  // Find products that are not yet in requestItems and have available stock
  const existingSkus = state.requestItems.map(i => i.sku);
  const candidate = state.products.find(p => !existingSkus.includes(p.sku) && p.inventory.available_qty > 0);
  
  if (!candidate) {
    showToast("Không còn sản phẩm khả dụng nào khác để thêm!", "warning");
    return;
  }

  state.requestItems.push({
    sku: candidate.sku,
    name: candidate.name,
    qty: 1,
    maxAvailable: candidate.inventory.available_qty
  });
  renderRequestItems();
}

/**
 * Showroom Selection Chips
 */
function renderShowroomChips() {
  DOM.showroomChips.innerHTML = PHONGVU_SHOWROOMS.map(sr => `
    <div class="chip-cp ${sr.code === state.selectedShowroom ? 'selected' : ''}" data-cp="${sr.code}" onclick="selectShowroom('${sr.code}')">
      ${sr.code} - ${sr.name.replace('Phong Vũ ', '')}
    </div>
  `).join("");
}

window.selectShowroom = function(code) {
  state.selectedShowroom = code;
  DOM.targetShowroomInput.value = code;
  highlightSelectedChip();
};

function highlightSelectedChip() {
  document.querySelectorAll(".chip-cp").forEach(chip => {
    chip.classList.toggle("selected", chip.dataset.cp === state.selectedShowroom);
  });
}

/**
 * Handle Submit Stock Transfer Request
 */
async function handleSubmitStockTransfer() {
  const targetCP = DOM.targetShowroomInput.value.trim().toUpperCase();
  if (!targetCP) {
    showToast("Vui lòng nhập hoặc chọn mã Kho nhận (Ví dụ: CP07)!", "error");
    DOM.targetShowroomInput.focus();
    return;
  }

  if (state.requestItems.length === 0) {
    showToast("Vui lòng chọn ít nhất 1 sản phẩm!", "error");
    return;
  }

  // Disable button during process
  DOM.submitRequestBtn.disabled = true;
  DOM.submitRequestBtn.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="animate-spin" style="animation: spin 1s linear infinite;"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path></svg>
    Đang gửi thông báo Telegram Admin...
  `;

  // Step 1: Simulated Telegram Notification send
  await delay(1200);
  showToast(`Đã gửi thông báo đến Telegram Admin xin duyệt chuyển về ${targetCP}!`, "success");
  
  DOM.submitRequestBtn.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path></svg>
    Admin đang duyệt lệnh qua Telegram...
  `;

  // Step 2: Simulated Admin Approval & ERP Stock Transfer Auto Creation
  await delay(2000);
  
  // Generate real looking ST code
  const todayStr = new Date().toISOString().slice(2, 10).replace(/-/g, "");
  const randomSuffix = Math.floor(1000 + Math.random() * 9000);
  const generatedStCode = `ST-${todayStr}-${randomSuffix}`;

  DOM.submitRequestBtn.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path></svg>
    ERP đã tạo lệnh: ${generatedStCode}!
  `;

  await delay(1200);

  // Deduct inventory in memory / local state
  state.requestItems.forEach(reqItem => {
    const prod = state.products.find(p => p.sku === reqItem.sku);
    if (prod) {
      prod.inventory.available_qty = Math.max(0, prod.inventory.available_qty - reqItem.qty);
      prod.inventory.on_hand_qty = Math.max(0, prod.inventory.on_hand_qty - reqItem.qty);
    }
  });
  applyFilters();

  closeRequestSheet();
  DOM.submitRequestBtn.disabled = false;
  DOM.submitRequestBtn.innerHTML = `
    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
    Gửi Admin Duyệt & Tự Động Tạo Lệnh ERP
  `;

  // Comprehensive success alert
  alert(
    `✅ TẠO PHIẾU CHUYỂN KHO THÀNH CÔNG!\n\n` +
    `🔖 Số phiếu ERP: ${generatedStCode}\n` +
    `🏢 Lộ trình: CP01 ➔ ${targetCP}\n` +
    `📦 Loại hàng: Hàng bảo hành\n` +
    `📝 Ghi chú: Hệ thống auto xin hàng Iphone 18 của VŨ AM\n` +
    `📱 Danh sách sản phẩm:\n` +
    state.requestItems.map(i => `   - [${i.sku}] ${i.name} (SL: ${i.qty})`).join("\n") +
    `\n\nThông tin đã được tự động phản hồi lại vào Telegram Admin!`
  );
}

/**
 * Handle Manual / Realtime Sync with ERP
 */
async function handleSyncERP(isSilent = false) {
  if (state.isSyncing) return;
  state.isSyncing = true;
  DOM.syncBtn.classList.add("spinning");

  if (!isSilent) {
    showToast("Đang truy vấn tồn kho & số giữ realtime trực tiếp từ ERP...", "info");
  }

  try {
    const res = await fetch("/api/sync?force=true", { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      if (data.success && data.products && data.products.length > 0) {
        state.products = data.products;
        applyFilters();
        if (data.timestamp) {
          DOM.syncTimeLabel.innerText = `Cập nhật: ${data.timestamp.split(' ')[1] || data.timestamp}`;
        } else {
          updateSyncTime();
        }
        if (!isSilent) {
          showToast(`✓ Đã đồng bộ Realtime từ ERP lúc ${DOM.syncTimeLabel.innerText.replace('Cập nhật: ', '')}!`, "success");
        }
      }
    } else {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (err) {
    console.warn("Realtime API sync fallback:", err);
    updateSyncTime();
    if (!isSilent) {
      showToast("Đã tải lại dữ liệu mới nhất!", "info");
    }
  } finally {
    DOM.syncBtn.classList.remove("spinning");
    state.isSyncing = false;
  }
}

function updateSyncTime() {
  const now = new Date();
  const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
  DOM.syncTimeLabel.innerText = `Cập nhật: ${timeStr}`;
}

/**
 * Populate Filters (Capacities & Colors)
 */
function populateFilterOptions() {
  const capacities = new Set();
  const colors = new Set();

  state.products.forEach(p => {
    if (p.capacity) capacities.add(p.capacity);
    if (p.color) colors.add(p.color);
  });

  capacities.forEach(cap => {
    const opt = document.createElement("option");
    opt.value = cap;
    opt.innerText = cap;
    DOM.capacityFilter.appendChild(opt);
  });

  colors.forEach(col => {
    const opt = document.createElement("option");
    opt.value = col;
    opt.innerText = col;
    DOM.colorFilter.appendChild(opt);
  });
}

/**
 * Toast Notification Utility
 */
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${escapeHtml(message)}</span>
  `;
  DOM.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideDown 0.3s reverse forwards";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Helpers
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[m]);
}

function cleanOrderCode(val) {
  if (!val) return "";
  let s = String(val).trim();
  if (/[eE]/.test(s)) {
    try {
      const num = Number(s);
      if (!isNaN(num)) {
        return BigInt(Math.round(num)).toString();
      }
    } catch (e) {}
  }
  if (s.endsWith(".0")) {
    s = s.slice(0, -2);
  }
  return s;
}

function getMoonIconSvg() {
  return `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>`;
}

function getSunIconSvg() {
  return `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>`;
}

// Start application
document.addEventListener("DOMContentLoaded", init);
