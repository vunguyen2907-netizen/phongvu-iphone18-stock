-- =========================================================================
-- SUPABASE SCHEMA: IPHONE 18 INVENTORY & STOCK TRANSFER (CKNB) SYSTEM
-- =========================================================================

-- 1. Bảng danh mục sản phẩm (Chỉ gồm iPhone 18 Series, ốp lưng, quà tặng)
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN ('iphone', 'case', 'gift')),
    model VARCHAR(64) NOT NULL,
    capacity VARCHAR(32),
    color VARCHAR(64),
    color_hex VARCHAR(16),
    image_url TEXT,
    retail_price NUMERIC(12, 0) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Bảng tồn kho thời gian thực (Tập trung kho 11001.01 & vị trí BIN)
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_sku VARCHAR(64) REFERENCES products(sku) ON DELETE CASCADE,
    warehouse_code VARCHAR(32) NOT NULL DEFAULT '11001.01',
    warehouse_name VARCHAR(128) DEFAULT 'Kho Tổng Miền Nam 11001.01',
    branch_code VARCHAR(32) DEFAULT 'CP01',
    bin_code VARCHAR(32) NOT NULL,
    bin_name VARCHAR(128) NOT NULL,
    on_hand_qty INTEGER NOT NULL DEFAULT 0,    -- Tồn thực tế trong kho
    held_qty INTEGER NOT NULL DEFAULT 0,       -- Tồn đang giữ theo đơn hàng
    available_qty INTEGER NOT NULL DEFAULT 0,  -- Khả dụng (on_hand - held + đơn cọc hợp lệ)
    last_synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Bảng danh sách đơn cọc từ Google Sheets "Pre-Order Iphone 18 HCM&BD"
CREATE TABLE IF NOT EXISTS preorder_deposits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_code VARCHAR(64) UNIQUE NOT NULL,
    customer_name VARCHAR(128),
    customer_phone VARCHAR(32),
    sku VARCHAR(64),
    deposit_amount NUMERIC(12, 0) DEFAULT 0,
    sheet_row_id INTEGER,
    is_valid BOOLEAN DEFAULT TRUE,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Bảng chi tiết đơn hàng đang giữ tồn (Từ nút xem tồn đang giữ trên ERP)
CREATE TABLE IF NOT EXISTS held_stock_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_sku VARCHAR(64) REFERENCES products(sku) ON DELETE CASCADE,
    order_code VARCHAR(64) NOT NULL,
    warehouse_code VARCHAR(32) DEFAULT '11001.01',
    quantity INTEGER NOT NULL DEFAULT 1,
    is_in_deposit_sheet BOOLEAN DEFAULT FALSE,
    availability_status VARCHAR(32) DEFAULT 'CHECK_ADMIN' CHECK (availability_status IN ('CAN_SELL', 'CHECK_ADMIN')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Bảng yêu cầu chuyển kho nội bộ (Request CKNB)
CREATE TABLE IF NOT EXISTS transfer_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_code VARCHAR(32) UNIQUE NOT NULL,
    source_warehouse VARCHAR(32) NOT NULL DEFAULT 'CP01',
    target_showroom VARCHAR(32) NOT NULL,     -- Ví dụ: CP07
    transfer_type VARCHAR(64) NOT NULL DEFAULT 'Hàng bảo hành',
    notes TEXT DEFAULT 'Hệ thống auto xin hàng Iphone 18 của VŨ AM',
    items JSONB NOT NULL,                     -- Array: [{"sku": "...", "name": "...", "qty": 1}]
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'PROCESSING', 'COMPLETED', 'FAILED')),
    erp_st_code VARCHAR(64),                  -- Mã phiếu ST-xxxxxx từ ERP Phong Vũ
    admin_approved_by VARCHAR(64),
    telegram_message_id BIGINT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes tối ưu tra cứu phản hồi tức thì
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory(product_sku);
CREATE INDEX IF NOT EXISTS idx_inventory_warehouse ON inventory(warehouse_code);
CREATE INDEX IF NOT EXISTS idx_preorder_code ON preorder_deposits(order_code);
CREATE INDEX IF NOT EXISTS idx_held_orders_sku ON held_stock_orders(product_sku);
CREATE INDEX IF NOT EXISTS idx_transfer_requests_code ON transfer_requests(request_code);

-- Enable Realtime trên Supabase
ALTER PUBLICATION supabase_realtime ADD TABLE transfer_requests;
ALTER PUBLICATION supabase_realtime ADD TABLE inventory;
