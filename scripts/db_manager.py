#!/usr/bin/env python3
"""
Database Manager for GFS Ordering Module
Handles all SQLite operations
"""
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database with schema"""
        schema_path = Path(__file__).parent.parent / 'schema.sql'
        
        with self.get_connection() as conn:
            if schema_path.exists():
                with open(schema_path) as f:
                    conn.executescript(f.read())
            conn.commit()
    
    # Product Operations
    def upsert_product(self, item_data):
        """Add or update a product from invoice data"""
        with self.get_connection() as conn:
            # Check if product exists
            cursor = conn.execute(
                "SELECT id, price_history, order_count FROM gfs_products WHERE gfs_item_code = ?",
                (item_data['item_code'],)
            )
            existing = cursor.fetchone()
            
            today = date.today().isoformat()
            
            if existing:
                # Update existing product
                product_id = existing['id']
                price_history = json.loads(existing['price_history'] or '[]')
                order_count = existing['order_count'] + 1
                
                # Add new price point if different from last
                if not price_history or price_history[-1]['price'] != item_data['unit_price']:
                    price_history.append({
                        'date': today,
                        'price': item_data['unit_price']
                    })
                
                conn.execute("""
                    UPDATE gfs_products SET
                        unit_price = ?,
                        price_history = ?,
                        last_seen = ?,
                        order_count = ?
                    WHERE id = ?
                """, (
                    item_data['unit_price'],
                    json.dumps(price_history),
                    today,
                    order_count,
                    product_id
                ))
            else:
                # Insert new product
                cursor = conn.execute("""
                    INSERT INTO gfs_products (
                        gfs_item_code, description, brand, pack_size,
                        category_code, category_name, unit_price,
                        price_history, first_seen, last_seen, order_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_data['item_code'],
                    item_data.get('description', ''),
                    item_data.get('brand', ''),
                    item_data.get('pack_size', ''),
                    item_data.get('category_code', ''),
                    item_data.get('category_name', ''),
                    item_data['unit_price'],
                    json.dumps([{'date': today, 'price': item_data['unit_price']}]),
                    today,
                    today,
                    1
                ))
                product_id = cursor.lastrowid
            
            conn.commit()
            return product_id
    
    def get_product(self, product_id):
        """Get a single product by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM gfs_products WHERE id = ?",
                (product_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_product_by_code(self, item_code):
        """Get a product by GFS item code"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM gfs_products WHERE gfs_item_code = ?",
                (item_code,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def search_products(self, query=None, category=None, limit=50):
        """Search products with filters"""
        with self.get_connection() as conn:
            sql = "SELECT * FROM gfs_products WHERE is_active = 1"
            params = []
            
            if query:
                sql += " AND (description LIKE ? OR brand LIKE ? OR gfs_item_code LIKE ?)"
                like_query = f"%{query}%"
                params.extend([like_query, like_query, like_query])
            
            if category:
                sql += " AND category_code = ?"
                params.append(category)
            
            sql += " ORDER BY order_count DESC, description LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_products_by_category(self):
        """Get products grouped by category"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT category_code, category_name, COUNT(*) as count,
                       AVG(unit_price) as avg_price
                FROM gfs_products
                WHERE is_active = 1
                GROUP BY category_code
                ORDER BY count DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_frequently_ordered(self, limit=20):
        """Get most frequently ordered products"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM gfs_products
                WHERE is_active = 1
                ORDER BY order_count DESC, last_seen DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Order Operations
    def create_order(self, name, delivery_date=None, notes=None):
        """Create a new order"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO gfs_orders (name, delivery_date, notes, status)
                VALUES (?, ?, ?, 'draft')
            """, (name, delivery_date, notes))
            conn.commit()
            return cursor.lastrowid
    
    def get_order(self, order_id):
        """Get order with all items"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM gfs_orders WHERE id = ?",
                (order_id,)
            )
            order = cursor.fetchone()
            if not order:
                return None
            
            order_dict = dict(order)
            
            # Get order items with product details
            cursor = conn.execute("""
                SELECT oi.*, p.gfs_item_code, p.description, p.brand, 
                       p.pack_size, p.unit_price, p.category_name
                FROM gfs_order_items oi
                JOIN gfs_products p ON oi.product_id = p.id
                WHERE oi.order_id = ?
            """, (order_id,))
            
            order_dict['items'] = [dict(row) for row in cursor.fetchall()]
            return order_dict
    
    def get_orders(self, status=None, limit=20):
        """Get list of orders"""
        with self.get_connection() as conn:
            sql = "SELECT * FROM gfs_orders"
            params = []
            
            if status:
                sql += " WHERE status = ?"
                params.append(status)
            
            sql += " ORDER BY created_date DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_order_item(self, order_id, product_id, quantity=1, programs=None, notes=None):
        """Add an item to an order"""
        programs_json = json.dumps(programs) if programs else None
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO gfs_order_items (order_id, product_id, quantity, programs, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (order_id, product_id, quantity, programs_json, notes))
            conn.commit()
            
            self._update_order_total(order_id)
            return cursor.lastrowid
    
    def update_order_item(self, item_id, quantity=None, programs=None, notes=None):
        """Update an order item"""
        with self.get_connection() as conn:
            # Get order_id first
            cursor = conn.execute(
                "SELECT order_id FROM gfs_order_items WHERE id = ?",
                (item_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False
            
            order_id = row['order_id']
            
            if quantity is not None:
                conn.execute(
                    "UPDATE gfs_order_items SET quantity = ? WHERE id = ?",
                    (quantity, item_id)
                )
            
            if programs is not None:
                conn.execute(
                    "UPDATE gfs_order_items SET programs = ? WHERE id = ?",
                    (json.dumps(programs), item_id)
                )
            
            if notes is not None:
                conn.execute(
                    "UPDATE gfs_order_items SET notes = ? WHERE id = ?",
                    (notes, item_id)
                )
            
            conn.commit()
            self._update_order_total(order_id)
            return True
    
    def remove_order_item(self, item_id):
        """Remove an item from an order"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT order_id FROM gfs_order_items WHERE id = ?",
                (item_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False
            
            order_id = row['order_id']
            conn.execute("DELETE FROM gfs_order_items WHERE id = ?", (item_id,))
            conn.commit()
            
            self._update_order_total(order_id)
            return True
    
    def _update_order_total(self, order_id):
        """Recalculate order total estimate"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT SUM(oi.quantity * p.unit_price) as total
                FROM gfs_order_items oi
                JOIN gfs_products p ON oi.product_id = p.id
                WHERE oi.order_id = ?
            """, (order_id,))
            
            row = cursor.fetchone()
            total = row['total'] if row and row['total'] else 0
            
            conn.execute(
                "UPDATE gfs_orders SET total_estimate = ? WHERE id = ?",
                (total, order_id)
            )
            conn.commit()
    
    def update_order_status(self, order_id, status):
        """Update order status"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE gfs_orders SET status = ? WHERE id = ?",
                (status, order_id)
            )
            conn.commit()
    
    def duplicate_order(self, order_id, new_name=None):
        """Duplicate an existing order as a new draft"""
        with self.get_connection() as conn:
            # Get original order
            cursor = conn.execute(
                "SELECT * FROM gfs_orders WHERE id = ?",
                (order_id,)
            )
            original = cursor.fetchone()
            if not original:
                return None
            
            # Create new order
            name = new_name or f"Copy of {original['name']}"
            cursor = conn.execute("""
                INSERT INTO gfs_orders (name, notes, status)
                VALUES (?, ?, 'draft')
            """, (name, original['notes']))
            new_order_id = cursor.lastrowid
            
            # Copy items
            cursor = conn.execute(
                "SELECT * FROM gfs_order_items WHERE order_id = ?",
                (order_id,)
            )
            for item in cursor.fetchall():
                conn.execute("""
                    INSERT INTO gfs_order_items (order_id, product_id, quantity, programs, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_order_id,
                    item['product_id'],
                    item['quantity'],
                    item['programs'],
                    item['notes']
                ))
            
            conn.commit()
            self._update_order_total(new_order_id)
            return new_order_id
    
    # Invoice History Operations
    def add_invoice(self, invoice_info):
        """Add an invoice record"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO gfs_invoice_history 
                (invoice_number, invoice_date, location, total_amount)
                VALUES (?, ?, ?, ?)
            """, (
                invoice_info.get('number'),
                invoice_info.get('date'),
                invoice_info.get('location'),
                invoice_info.get('total')
            ))
            conn.commit()
            return cursor.lastrowid
    
    def add_invoice_item(self, invoice_id, product_id, item_data):
        """Add an item to an invoice"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO gfs_invoice_items 
                (invoice_id, product_id, quantity, unit_price, extended_price)
                VALUES (?, ?, ?, ?, ?)
            """, (
                invoice_id,
                product_id,
                item_data.get('quantity_shipped'),
                item_data['unit_price'],
                item_data['extended_price']
            ))
            conn.commit()
    
    # Program Operations
    def get_programs(self, active_only=True):
        """Get all programs"""
        with self.get_connection() as conn:
            sql = "SELECT * FROM gfs_programs"
            if active_only:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY category, name"
            
            cursor = conn.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_programs_by_category(self):
        """Get programs grouped by category"""
        programs = self.get_programs()
        categories = {}
        for p in programs:
            cat = p['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)
        return categories

if __name__ == '__main__':
    # Test the database
    db = DatabaseManager('/tmp/test_gfs.db')
    print("Database initialized successfully")
    
    # Test programs
    programs = db.get_programs()
    print(f"\nPrograms loaded: {len(programs)}")
    for p in programs[:5]:
        print(f"  - {p['name']} ({p['short_code']})")
