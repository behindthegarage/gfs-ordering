"""
GFS Ordering Blueprint for Kinawa Command Center
"""
from flask import Blueprint, render_template, request, jsonify, current_app
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add scripts path for imports
scripts_path = Path(__file__).parent / 'scripts'
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

from db_manager import DatabaseManager

gfs_bp = Blueprint('gfs_ordering', __name__, 
                   template_folder='templates',
                   url_prefix='/gfs-ordering')

DB_PATH = Path(__file__).parent / 'data' / 'gfs_catalog.db'

def get_db():
    return DatabaseManager(DB_PATH)

@gfs_bp.route('/')
def index():
    """Main GFS ordering dashboard"""
    db = get_db()
    
    # Get stats
    categories = db.get_products_by_category()
    recent_orders = db.get_orders(limit=5)
    frequent_products = db.get_frequently_ordered(limit=10)
    programs = db.get_programs()
    
    return render_template('gfs_ordering.html',
                         categories=categories,
                         recent_orders=recent_orders,
                         frequent_products=frequent_products,
                         programs=programs)

@gfs_bp.route('/products')
def products():
    """Product catalog browser"""
    db = get_db()
    
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    
    products = db.search_products(query=query, category=category, limit=100)
    categories = db.get_products_by_category()
    
    return render_template('gfs_products.html',
                         products=products,
                         categories=categories,
                         current_category=category,
                         query=query)

@gfs_bp.route('/products/<int:product_id>')
def product_detail(product_id):
    """Single product detail view"""
    db = get_db()
    product = db.get_product(product_id)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify(product)

@gfs_bp.route('/orders')
def orders():
    """Order history list"""
    db = get_db()
    status = request.args.get('status', '')
    
    orders = db.get_orders(status=status or None, limit=50)
    
    return render_template('gfs_orders.html',
                         orders=orders,
                         current_status=status)

@gfs_bp.route('/orders/new', methods=['GET', 'POST'])
def new_order():
    """Create new order"""
    db = get_db()
    
    if request.method == 'POST':
        name = request.form.get('name')
        delivery_date = request.form.get('delivery_date')
        notes = request.form.get('notes')
        
        order_id = db.create_order(name, delivery_date, notes)
        return jsonify({'success': True, 'order_id': order_id})
    
    # GET - show new order form
    programs = db.get_programs()
    frequent = db.get_frequently_ordered(limit=20)
    
    # Calculate suggested delivery date (next Tuesday)
    today = datetime.now()
    days_until_tuesday = (1 - today.weekday()) % 7  # 1 = Tuesday
    if days_until_tuesday == 0:
        days_until_tuesday = 7
    suggested_date = (today + timedelta(days=days_until_tuesday)).strftime('%Y-%m-%d')
    
    return render_template('gfs_new_order.html',
                         programs=programs,
                         frequent_products=frequent,
                         suggested_date=suggested_date)

@gfs_bp.route('/orders/<int:order_id>')
def order_detail(order_id):
    """View/edit single order"""
    db = get_db()
    order = db.get_order(order_id)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    programs = db.get_programs()
    
    return render_template('gfs_order_detail.html',
                         order=order,
                         programs=programs)

@gfs_bp.route('/orders/<int:order_id>/items', methods=['POST'])
def add_order_item(order_id):
    """Add item to order"""
    db = get_db()
    
    data = request.get_json() or request.form
    
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    programs = data.get('programs', [])
    notes = data.get('notes', '')
    
    if isinstance(programs, str):
        programs = json.loads(programs)
    
    item_id = db.add_order_item(order_id, product_id, quantity, programs, notes)
    
    return jsonify({'success': True, 'item_id': item_id})

@gfs_bp.route('/orders/<int:order_id>/items/<int:item_id>', methods=['PUT', 'DELETE'])
def update_order_item(order_id, item_id):
    """Update or delete order item"""
    db = get_db()
    
    if request.method == 'DELETE':
        db.remove_order_item(item_id)
        return jsonify({'success': True})
    
    # PUT - update
    data = request.get_json() or request.form
    quantity = data.get('quantity')
    programs = data.get('programs')
    
    if quantity is not None:
        quantity = int(quantity)
    
    db.update_order_item(item_id, quantity=quantity, programs=programs)
    
    return jsonify({'success': True})

@gfs_bp.route('/orders/<int:order_id>/duplicate', methods=['POST'])
def duplicate_order(order_id):
    """Duplicate an order"""
    db = get_db()
    
    new_name = request.form.get('name')
    new_order_id = db.duplicate_order(order_id, new_name)
    
    return jsonify({'success': True, 'order_id': new_order_id})

@gfs_bp.route('/orders/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    """Update order status"""
    db = get_db()
    
    status = request.form.get('status')
    db.update_order_status(order_id, status)
    
    return jsonify({'success': True})

@gfs_bp.route('/api/search')
def api_search():
    """AJAX product search"""
    db = get_db()
    
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    limit = int(request.args.get('limit', 20))
    
    products = db.search_products(query=query, category=category, limit=limit)
    
    return jsonify(products)

@gfs_bp.route('/api/programs')
def api_programs():
    """Get all programs"""
    db = get_db()
    programs = db.get_programs()
    return jsonify(programs)
