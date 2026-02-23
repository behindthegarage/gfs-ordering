-- GFS Ordering Module Database Schema
-- SQLite for Command Center integration

-- Master product catalog built from invoice history
CREATE TABLE IF NOT EXISTS gfs_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gfs_item_code TEXT UNIQUE NOT NULL,      -- 582271
    description TEXT NOT NULL,                -- "APPLE GRANNY SMITH"
    brand TEXT,                               -- "Markon"
    pack_size TEXT,                           -- "113x1 EA"
    category_code TEXT,                       -- PR, GR, FR, DY, BV
    category_name TEXT,                       -- "Produce", "Grocery", etc.
    unit_price DECIMAL(10,2),                 -- most recent price
    price_history TEXT,                       -- JSON: [{"date": "2025-01-15", "price": 46.57}, ...]
    first_seen DATE,
    last_seen DATE,
    order_count INTEGER DEFAULT 0,            -- how many times ordered across all history
    preferred_programs TEXT,                  -- JSON: ["kinawa", "cornell", ...] if item is commonly ordered for specific programs
    tags TEXT,                                -- JSON: ["snack", "healthy", "allergen-free", ...]
    is_active BOOLEAN DEFAULT 1               -- 0 if discontinued/no longer available
);

-- Programs that can be ordered for
CREATE TABLE IF NOT EXISTS gfs_programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,                -- "Club Kinawa B/A"
    short_code TEXT UNIQUE NOT NULL,          -- "kinawa", "cornell", "cmontessori_ba", "cmontessori_prek"
    category TEXT,                            -- "before_after", "toddler", "infant", "gsrp"
    color TEXT,                               -- hex color for UI
    is_active BOOLEAN DEFAULT 1
);

-- Order lists (templates + submitted)
CREATE TABLE IF NOT EXISTS gfs_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,                                -- "Weekly Snack Order - Week of Feb 24"
    created_date DATE DEFAULT CURRENT_DATE,
    delivery_date DATE,                       -- when you need it delivered
    status TEXT DEFAULT 'draft',              -- draft, ready, submitted, completed
    total_estimate DECIMAL(10,2),
    notes TEXT,
    created_by TEXT,                          -- for audit trail
    submitted_date DATE,
    gfs_confirmation_number TEXT,
    actual_total DECIMAL(10,2)
);

-- Items in each order with per-item program allocation
CREATE TABLE IF NOT EXISTS gfs_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    programs TEXT,                            -- JSON: ["kinawa", "cornell"] - which programs this item is for
    is_gsrp BOOLEAN DEFAULT 0,                -- legacy flag, use programs array now
    notes TEXT,
    FOREIGN KEY (order_id) REFERENCES gfs_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES gfs_products(id)
);

-- Invoice history (for reference/reconciliation)
CREATE TABLE IF NOT EXISTS gfs_invoice_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,      -- 9032091307
    invoice_date DATE,
    delivery_date DATE,
    location TEXT,                            -- "EDGEWOOD ELEMENTARY SCHOOL"
    total_amount DECIMAL(10,2),
    item_count INTEGER,
    invoice_pdf_path TEXT,
    parsed_data TEXT,                         -- JSON of full parsed invoice
    processed_date DATE DEFAULT CURRENT_DATE
);

-- Items from historical invoices (linking products to invoices)
CREATE TABLE IF NOT EXISTS gfs_invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    extended_price DECIMAL(10,2),
    FOREIGN KEY (invoice_id) REFERENCES gfs_invoice_history(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES gfs_products(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_code ON gfs_products(gfs_item_code);
CREATE INDEX IF NOT EXISTS idx_products_category ON gfs_products(category_code);
CREATE INDEX IF NOT EXISTS idx_products_active ON gfs_products(is_active);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON gfs_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_invoice_history_date ON gfs_invoice_history(invoice_date);

-- Insert default programs
INSERT OR IGNORE INTO gfs_programs (name, short_code, category, color) VALUES
    ('Club Kinawa B/A', 'kinawa', 'before_after', '#FF6B6B'),
    ('Cornell B/A', 'cornell', 'before_after', '#4ECDC4'),
    ('Central Montesorri B/A', 'cmontessori_ba', 'before_after', '#45B7D1'),
    ('Bennett Woods B/A', 'bennett', 'before_after', '#96CEB4'),
    ('Hiawatha B/A', 'hiawatha', 'before_after', '#FFEAA7'),
    ('Toddler 1s (1 year olds)', 'toddler1', 'toddler', '#DDA0DD'),
    ('Toddler 2s', 'toddler2', 'toddler', '#DDA0DD'),
    ('Infants', 'infants', 'infant', '#98D8C8'),
    ('Central Montesorri Pre-K (GSRP)', 'cmontessori_prek', 'gsrp', '#F7DC6F'),
    ('GSRP Program 1', 'gsrp1', 'gsrp', '#BB8FCE'),
    ('GSRP Program 2', 'gsrp2', 'gsrp', '#BB8FCE'),
    ('GSRP Program 3', 'gsrp3', 'gsrp', '#BB8FCE'),
    ('GSRP Program 4', 'gsrp4', 'gsrp', '#BB8FCE'),
    ('GSRP Program 5', 'gsrp5', 'gsrp', '#BB8FCE');
