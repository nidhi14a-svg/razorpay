import os
import csv
import sys
import argparse
from datetime import datetime
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(description="Convert Olist dataset to RAZZZ customer schema.")
    parser.add_argument("input_dir", help="Directory containing Olist CSV files")
    parser.add_argument("--output", default="razzz_olist_customers.csv", help="Output CSV file path")
    
    args = parser.parse_args()
    input_dir = args.input_dir
    output_file = args.output
    
    # 1. Validate required files exist
    required_files = [
        "olist_customers_dataset.csv",
        "olist_orders_dataset.csv",
        "olist_order_payments_dataset.csv"
    ]
    
    for f in required_files:
        path = os.path.join(input_dir, f)
        if not os.path.exists(path):
            print(f"❌ Error: Required file missing: {f} in {input_dir}")
            sys.exit(1)
            
    print(f"Reading data from {input_dir}...")

    # 2. Parse Payments
    # order_id -> sum of payment_value
    order_payments = defaultdict(float)
    with open(os.path.join(input_dir, 'olist_order_payments_dataset.csv'), encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            order_payments[row['order_id']] += float(row['payment_value'])

    # 3. Parse Orders
    # customer_id -> list of orders
    customer_orders = defaultdict(list)
    max_global_timestamp = None
    
    with open(os.path.join(input_dir, 'olist_orders_dataset.csv'), encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['order_status'] == 'delivered':
                customer_id = row['customer_id']
                order_id = row['order_id']
                dt_str = row['order_purchase_timestamp']
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                payment = order_payments.get(order_id, 0.0)
                
                customer_orders[customer_id].append({
                    'order_id': order_id,
                    'timestamp': dt,
                    'payment': payment
                })
                
                if max_global_timestamp is None or dt > max_global_timestamp:
                    max_global_timestamp = dt
                    
    # 4. Parse Customers and aggregate by customer_unique_id
    # customer_unique_id -> stats
    unique_customers = {}
    with open(os.path.join(input_dir, 'olist_customers_dataset.csv'), encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            c_id = row['customer_id']
            u_id = row['customer_unique_id']
            
            if u_id not in unique_customers:
                unique_customers[u_id] = {
                    'purchase_count': 0,
                    'lifetime_value': 0.0,
                    'latest_purchase_dt': None,
                }
                
            if c_id in customer_orders:
                for order in customer_orders[c_id]:
                    unique_customers[u_id]['purchase_count'] += 1
                    unique_customers[u_id]['lifetime_value'] += order['payment']
                    
                    if unique_customers[u_id]['latest_purchase_dt'] is None or order['timestamp'] > unique_customers[u_id]['latest_purchase_dt']:
                        unique_customers[u_id]['latest_purchase_dt'] = order['timestamp']

    # 5. Build Final Records
    final_records = []
    merchant_id = "olist_merchant_001"
    
    metrics = {
        'total_ltv': 0.0,
        'completed_purchasers': 0,
        'no_purchase': 0,
        'cart_purchased': 0,
        'cart_empty': 0,
    }
    
    seen_ids = set()
    
    for u_id, stats in unique_customers.items():
        pc = stats['purchase_count']
        ltv = stats['lifetime_value']
        latest_dt = stats['latest_purchase_dt']
        
        aov = ltv / pc if pc > 0 else 0.0
        
        if pc > 0 and latest_dt is not None:
            days_since = (max_global_timestamp - latest_dt).days
            cart_status = "purchased"
            metrics['completed_purchasers'] += 1
            metrics['cart_purchased'] += 1
        else:
            days_since = 999
            cart_status = ""
            metrics['no_purchase'] += 1
            metrics['cart_empty'] += 1
            
        record = {
            'id': u_id,
            'merchant_id': merchant_id,
            'purchase_count': pc,
            'lifetime_value': round(ltv, 2),
            'days_since_last_purchase': days_since,
            'average_order_value': round(aov, 2),
            'cart_status': cart_status,
            'segment': "",
            'customer_id': u_id,
            'name': "",
            'email': ""
        }
        
        # Validation checks
        if record['id'] in seen_ids:
            print(f"❌ Error: Duplicate RAZZZ customer ID found: {record['id']}")
            sys.exit(1)
        seen_ids.add(record['id'])
        
        assert isinstance(record['id'], str) and record['id'] != ""
        assert record['purchase_count'] >= 0
        assert record['lifetime_value'] >= 0
        assert record['average_order_value'] >= 0
        assert record['days_since_last_purchase'] >= 0
        
        final_records.append(record)
        metrics['total_ltv'] += ltv

    # 6. Write output
    fieldnames = [
        'id', 'merchant_id', 'purchase_count', 'lifetime_value', 
        'days_since_last_purchase', 'average_order_value', 
        'cart_status', 'segment', 'customer_id', 'name', 'email'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_records)
        
    print(f"✓ Data successfully written to {output_file}")
    
    # 7. Print Summary
    print("\n" + "="*50)
    print(" CONVERSION SUMMARY ")
    print("="*50)
    print(f"Olist Source Customers Processed: {len(unique_customers)}")
    print(f"RAZZZ Customer Records Generated: {len(final_records)}")
    print(f"Total Lifetime Value: BRL {metrics['total_ltv']:,.2f}")
    if max_global_timestamp:
        print(f"Reference Date (Max Purchase Date): {max_global_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Customers with Completed Purchases: {metrics['completed_purchasers']}")
    print(f"Customers without Completed Purchases: {metrics['no_purchase']}")
    print(f"Records with Unavailable Name/Email: {len(final_records)} (100%)")
    print(f"Cart Status Distribution:")
    print(f"  - 'purchased': {metrics['cart_purchased']}")
    print(f"  - '' (empty) : {metrics['cart_empty']}")
    print("="*50)

if __name__ == "__main__":
    main()
