#!/usr/bin/env python3
"""
GFS Invoice Parser - Robust Version
Extracts product catalog from historical GFS invoices
"""
import pdfplumber
import re
import json
from datetime import datetime
from pathlib import Path

# Category mapping from invoice codes
CATEGORY_MAP = {
    'PR': 'Produce',
    'GR': 'Grocery', 
    'FR': 'Frozen',
    'DY': 'Dairy',
    'BV': 'Beverage',
    'CN': 'Canned',
    'PA': 'Paper',
    'CH': 'Chemical/Cleaning',
    'EQ': 'Equipment',
    'PU': 'Packaging/Supply'
}

# Known brands for better parsing
KNOWN_BRANDS = {
    'Markon', 'Ready-', "Stacy'", "Annie'", 'Nutri-', 'Betty', 'Zee Ze', 'Cool C',
    'Kellog', 'Corn P', 'Ruffle', 'Pepper', 'Marzet', 'Horizo', 'Gordon',
    'Packer', 'Tru Fru', 'Amafru', 'Ken\'s', 'G.S.', 'Zee Ze'
}

def extract_price_fields(parts):
    """Extract the three price fields from the end of the line parts"""
    # Look for decimal numbers at the end
    prices = []
    for p in reversed(parts):
        if re.match(r'^\d+\.\d{2}$', p):
            prices.insert(0, float(p))
        elif prices:  # Stop when we hit non-price after finding prices
            break
    
    if len(prices) >= 3:
        return prices[-3], prices[-2], prices[-1]  # inv_val, unit_price, extended
    elif len(prices) >= 2:
        return 0.0, prices[-2], prices[-1]
    elif len(prices) >= 1:
        return 0.0, prices[-1], prices[-1]
    return 0.0, 0.0, 0.0

def parse_line_item(line):
    """Parse a single invoice line item"""
    parts = line.strip().split()
    if len(parts) < 8:
        return None
    
    # Must start with 6-digit item code
    if not re.match(r'^\d{6}$', parts[0]):
        return None
    
    item_code = parts[0]
    
    # Extract prices from the end
    inv_val, unit_price, extended = extract_price_fields(parts)
    
    # Find category code (2-letter code before the prices)
    category = None
    category_idx = None
    for i in range(len(parts) - 4, max(4, len(parts) - 10), -1):
        if i >= 0 and parts[i] in CATEGORY_MAP:
            category = parts[i]
            category_idx = i
            break
    
    if not category:
        return None
    
    # Quantity fields are usually positions 1 and 2
    try:
        qty_ordered = int(parts[1])
        qty_shipped = int(parts[2])
    except ValueError:
        return None
    
    # Unit is position 3 (CS, EA, etc)
    unit = parts[3] if len(parts) > 3 else 'CS'
    
    # Everything between unit and category needs to be parsed
    # Format: PackSize [Brand] Description
    middle_parts = parts[4:category_idx]
    
    # Try to identify pack size (usually contains 'x' or is numeric with unit)
    pack_size = ''
    brand = ''
    description = ''
    
    if middle_parts:
        # Pack size usually has 'x' in it or is like "1x30 LB"
        pack_end = 0
        for i, part in enumerate(middle_parts):
            if 'x' in part or part in ['EA', 'LB', 'OZ', 'FOZ', 'CO', 'CS']:
                pack_end = i + 1
        
        pack_size = ' '.join(middle_parts[:pack_end])
        remaining = middle_parts[pack_end:]
        
        # Try to identify brand from remaining
        if remaining:
            # Check if first word looks like a brand
            if remaining[0] in KNOWN_BRANDS or len(remaining[0]) < 8:
                brand = remaining[0]
                description = ' '.join(remaining[1:])
            else:
                description = ' '.join(remaining)
    
    return {
        'item_code': item_code,
        'quantity_ordered': qty_ordered,
        'quantity_shipped': qty_shipped,
        'unit': unit,
        'pack_size': pack_size,
        'brand': brand,
        'description': description,
        'category_code': category,
        'category_name': CATEGORY_MAP.get(category, category),
        'invoice_value': inv_val,
        'unit_price': unit_price,
        'extended_price': extended,
        'raw_line': line.strip()  # For debugging
    }

def parse_invoice(pdf_path):
    """Parse a GFS invoice PDF and extract structured data"""
    items = []
    invoice_info = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            
            # Extract invoice metadata from first page
            if page_num == 0:
                for line in lines:
                    if 'Invoice' in line and not invoice_info.get('number'):
                        m = re.search(r'Invoice\s+(\d+)', line)
                        if m:
                            invoice_info['number'] = m.group(1)
                    
                    if 'Invoice Date' in line:
                        m = re.search(r'Invoice Date\s+(\d{2}/\d{2}/\d{4})', line)
                        if m:
                            invoice_info['date'] = datetime.strptime(m.group(1), '%m/%d/%Y').date()
                    
                    if 'Ship To:' in line:
                        # Look ahead for location name
                        idx = lines.index(line)
                        for j in range(idx, min(idx+5, len(lines))):
                            loc_match = re.search(r'([A-Z][A-Z\s]+(?:SCHOOL|ELEMENTARY|CENTER))', lines[j])
                            if loc_match:
                                invoice_info['location'] = loc_match.group(1).strip()
                                break
            
            # Parse line items
            for line in lines:
                item = parse_line_item(line)
                if item:
                    items.append(item)
    
    return {
        'invoice_info': invoice_info,
        'items': items
    }

def batch_process_invoices(invoice_dir, db_path):
    """
    Process all PDF invoices in a directory and build product catalog
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from db_manager import DatabaseManager
    
    db = DatabaseManager(db_path)
    invoice_files = sorted(Path(invoice_dir).glob('*_gfs_invoice.pdf'))
    
    print(f"Found {len(invoice_files)} invoice files")
    
    for pdf_path in invoice_files:
        print(f"\nProcessing: {pdf_path.name}")
        try:
            result = parse_invoice(str(pdf_path))
            
            if result['invoice_info']:
                print(f"  Invoice: {result['invoice_info'].get('number')}")
                print(f"  Date: {result['invoice_info'].get('date')}")
                print(f"  Location: {result['invoice_info'].get('location')}")
            
            print(f"  Items found: {len(result['items'])}")
            
            # Store invoice and items
            invoice_id = db.add_invoice(result['invoice_info'])
            
            for item in result['items']:
                try:
                    product_id = db.upsert_product(item)
                    db.add_invoice_item(invoice_id, product_id, item)
                except Exception as e:
                    print(f"    Error storing item {item.get('item_code')}: {e}")
                
        except Exception as e:
            print(f"  ERROR processing file: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "="*50)
    print("Processing complete!")
    
    # Show summary
    stats = db.get_products_by_category()
    print(f"\nProduct Catalog Summary:")
    for cat in stats:
        print(f"  {cat['category_name']}: {cat['count']} products")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python invoice_parser.py <pdf_path>")
        print("   or: python invoice_parser.py --batch <invoice_dir> <db_path>")
        sys.exit(1)
    
    if sys.argv[1] == '--batch':
        batch_process_invoices(sys.argv[2], sys.argv[3])
    else:
        result = parse_invoice(sys.argv[1])
        print(json.dumps(result, indent=2, default=str))
