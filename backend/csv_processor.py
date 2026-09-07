import csv
import io
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from segmentation import segment_customer

# Column Aliases Mapping (normalized lowercase without spaces/underscores)
COLUMN_ALIASES = {
    "customer_id": [
        "customer_id", "customerid", "id", "custid", "cust_id", 
        "clientid", "client_id", "userid", "user_id", "customer"
    ],
    "customer_unique_id": [
        "customer_unique_id", "unique_id", "customeruniqueid"
    ],
    "order_id": [
        "order_id", "orderid", "orderno", "order_no", 
        "invoiceno", "invoice_no", "invoiceid", "invoice_id", 
        "transactionid", "transaction_id", "order_number", "trans_id"
    ],
    "invoice_id": [
        "invoiceno", "invoice_no", "invoiceid", "invoice_id", 
        "orderno", "order_no", "orderid", "order_id", 
        "transactionid", "transaction_id", "order_number", "trans_id"
    ],
    "date": [
        "invoicedate", "invoice_date", "purchasedate", "purchase_date", 
        "date", "order_purchase_timestamp", "timestamp", "created_at",
        "order_date", "trans_date"
    ],
    "quantity": [
        "quantity", "qty", "order_item_id", "items_count", "item_count"
    ],
    "unit_price": [
        "unitprice", "unit_price", "price", "item_price", "item_unit_price", "rate"
    ],
    "amount": [
        "amount", "revenue", "total", "payment_value", "subtotal", 
        "grand_total", "total_amount", "line_total", "order_value"
    ],
    # Pre-calculated customer summary columns
    "purchase_count": [
        "purchase_count", "orders", "total_orders", "orders_count", "frequency"
    ],
    "lifetime_value": [
        "lifetime_value", "ltv", "total_spend", "total_revenue", "monetary", "clv"
    ],
    "days_since_last_purchase": [
        "days_since_last_purchase", "recency", "days_since_last", "days_since_purchase", "recency_days"
    ],
    "average_order_value": [
        "average_order_value", "aov", "avg_order_value", "avg_spend"
    ],
    # Metadata
    "name": [
        "name", "customer_name", "full_name", "client_name"
    ],
    "email": [
        "email", "customer_email", "email_address"
    ],
    "cart_status": [
        "cart_status", "status"
    ]
}

def normalize_col(name: str) -> str:
    """Strip whitespace and lowercase string."""
    return re.sub(r'[\s_]+', '_', name.strip()).lower()

def detect_column_mappings(fieldnames: List[str]) -> Dict[str, str]:
    """
    Given actual CSV headers, map standard conceptual keys to actual header names.
    """
    mapping = {}
    normalized_headers = {normalize_col(f): f for f in fieldnames if f}

    for standard_key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            clean_alias = normalize_col(alias)
            if clean_alias in normalized_headers:
                mapping[standard_key] = normalized_headers[clean_alias]
                break
            # Also check if actual header without underscore matches
            clean_no_und = clean_alias.replace("_", "")
            for nh, orig_h in normalized_headers.items():
                if nh.replace("_", "") == clean_no_und:
                    mapping[standard_key] = orig_h
                    break
            if standard_key in mapping:
                break

    return mapping

def parse_date_safely(date_str: str) -> Optional[datetime]:
    """Parses various date strings safely."""
    if not date_str or not str(date_str).strip():
        return None
    d = str(date_str).strip()
    
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y",
        "%m/%d/%Y"
    ]
    
    # Try ISO format
    try:
        return datetime.fromisoformat(d.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        pass

    for fmt in formats:
        try:
            return datetime.strptime(d, fmt)
        except ValueError:
            continue
    return None

def parse_numeric(val: Any, default: float = 0.0) -> float:
    """Parses numeric float values safely, handling currency symbols and commas."""
    if val is None:
        return default
    s = str(val).strip().replace("$", "").replace("₹", "").replace(",", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return default

def process_csv_stream(reader: csv.DictReader, col_map: Dict[str, str]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parses and aggregates CSV rows into customer documents.
    Supports:
      1. Pre-aggregated customer datasets (with purchase_count, lifetime_value, etc.)
      2. Transactional datasets (order/invoice lines grouped by customer_id)
    Returns (processed_customers, metadata)
    """
    cust_id_col = col_map.get("customer_id")
    if not cust_id_col:
        raise ValueError("CSV must contain a customer identifier column (e.g., customer_id, id, CustomerID).")

    is_preaggregated = ("purchase_count" in col_map or "lifetime_value" in col_map)
    has_transaction_data = ("amount" in col_map or "unit_price" in col_map or "invoice_id" in col_map)

    total_rows = 0
    invalid_rows = 0

    if is_preaggregated and not ("unit_price" in col_map and "invoice_id" in col_map):
        # --- Mode 1: Summary Customer Dataset ---
        customers = []
        seen_ids = set()

        for row in reader:
            total_rows += 1
            cid = row.get(cust_id_col, "").strip() if row.get(cust_id_col) else ""
            if not cid:
                invalid_rows += 1
                continue
            if cid in seen_ids:
                invalid_rows += 1
                continue
            seen_ids.add(cid)

            p_count = int(parse_numeric(row.get(col_map.get("purchase_count", "")), 0))
            ltv = round(parse_numeric(row.get(col_map.get("lifetime_value", "")), 0.0), 2)
            days_since = int(parse_numeric(row.get(col_map.get("days_since_last_purchase", "")), 0))
            aov = parse_numeric(row.get(col_map.get("average_order_value", "")), 0.0)
            if aov <= 0 and p_count > 0:
                aov = round(ltv / p_count, 2)
            else:
                aov = round(aov, 2)

            name = row.get(col_map.get("name", ""), "").strip() if col_map.get("name") else ""
            email = row.get(col_map.get("email", ""), "").strip() if col_map.get("email") else ""
            cart_status = row.get(col_map.get("cart_status", ""), "").strip() if col_map.get("cart_status") else ("purchased" if p_count > 0 else "")

            cust_doc = {
                "id": cid,
                "name": name,
                "email": email,
                "purchase_count": p_count,
                "days_since_last_purchase": days_since,
                "lifetime_value": ltv,
                "average_order_value": aov,
                "cart_status": cart_status
            }
            cust_doc["segment"] = segment_customer(cust_doc)
            customers.append(cust_doc)

        metadata = {
            "dataset_type": "summary",
            "total_rows": total_rows,
            "total_unique_customers": len(customers),
            "total_transactions": sum(c["purchase_count"] for c in customers),
            "invalid_rows": invalid_rows,
            "detected_columns": col_map
        }
        return customers, metadata

    elif has_transaction_data or "date" in col_map:
        # --- Mode 2: Transactional Dataset ---
        # Group by customer ID and calculate behavioral metrics
        customer_groups = {}
        all_dates = []

        inv_col = col_map.get("invoice_id")
        date_col = col_map.get("date")
        qty_col = col_map.get("quantity")
        price_col = col_map.get("unit_price")
        amt_col = col_map.get("amount")
        name_col = col_map.get("name")
        email_col = col_map.get("email")

        for row in reader:
            total_rows += 1
            cid = row.get(cust_id_col, "").strip() if row.get(cust_id_col) else ""
            if not cid:
                invalid_rows += 1
                continue

            # Calculate line revenue
            rev = 0.0
            if amt_col and row.get(amt_col) is not None and str(row.get(amt_col)).strip() != "":
                rev = parse_numeric(row.get(amt_col), 0.0)
            elif price_col and row.get(price_col) is not None:
                unit_p = parse_numeric(row.get(price_col), 0.0)
                qty = parse_numeric(row.get(qty_col), 1.0) if qty_col else 1.0
                rev = unit_p * qty

            # Parse transaction date
            dt = parse_date_safely(row.get(date_col)) if date_col else None
            if dt:
                all_dates.append(dt)

            # Invoice/Order ID
            order_id = row.get(inv_col, "").strip() if (inv_col and row.get(inv_col)) else f"tx_{total_rows}"

            if cid not in customer_groups:
                customer_groups[cid] = {
                    "id": cid,
                    "orders": set(),
                    "total_revenue": 0.0,
                    "dates": [],
                    "name": row.get(name_col, "").strip() if (name_col and row.get(name_col)) else "",
                    "email": row.get(email_col, "").strip() if (email_col and row.get(email_col)) else ""
                }

            group = customer_groups[cid]
            group["orders"].add(order_id)
            group["total_revenue"] += rev
            if dt:
                group["dates"].append(dt)

        if not customer_groups:
            raise ValueError("No valid customer transactions could be parsed from the CSV.")

        # Determine reference date for days_since_last_purchase
        dataset_max_date = max(all_dates) if all_dates else datetime.now()
        
        # Calculate dynamic thresholds for deterministic segmentation across this dataset
        all_ltvs = [round(g["total_revenue"], 2) for g in customer_groups.values()]
        all_ltvs_sorted = sorted(all_ltvs)
        p75_ltv = all_ltvs_sorted[int(len(all_ltvs_sorted) * 0.75)] if all_ltvs_sorted else 100.0
        p50_ltv = all_ltvs_sorted[int(len(all_ltvs_sorted) * 0.50)] if all_ltvs_sorted else 50.0

        thresholds = {
            "p75_ltv": max(p75_ltv, 150.0),
            "p50_ltv": max(p50_ltv, 50.0)
        }

        customers = []
        for cid, g in customer_groups.items():
            purchase_count = len(g["orders"])
            ltv = round(max(0.0, g["total_revenue"]), 2)
            aov = round(ltv / max(1, purchase_count), 2)

            if g["dates"]:
                last_dt = max(g["dates"])
                days_since = max(0, (dataset_max_date - last_dt).days)
                last_purchase_str = last_dt.strftime("%Y-%m-%d")
            else:
                days_since = 30
                last_purchase_str = ""

            cust_doc = {
                "id": cid,
                "name": g["name"],
                "email": g["email"],
                "purchase_count": purchase_count,
                "days_since_last_purchase": days_since,
                "lifetime_value": ltv,
                "average_order_value": aov,
                "last_purchase_date": last_purchase_str,
                "cart_status": "purchased" if purchase_count > 0 else ""
            }
            cust_doc["segment"] = segment_customer(cust_doc, thresholds=thresholds)
            customers.append(cust_doc)

        total_orders = sum(len(g["orders"]) for g in customer_groups.values())

        metadata = {
            "dataset_type": "transactional",
            "total_rows": total_rows,
            "total_unique_customers": len(customers),
            "total_transactions": total_orders,
            "invalid_rows": invalid_rows,
            "detected_columns": col_map,
            "dataset_max_date": dataset_max_date.strftime("%Y-%m-%d") if all_dates else None
        }
        return customers, metadata
    else:
        # Lacks both transactional columns and pre-aggregated columns
        raise ValueError(
            "Customer records exist, but purchase history could not be calculated because the "
            "uploaded CSV does not contain valid transaction amount, quantity/price, or order information."
        )

def validate_and_preview_csv(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Validates CSV file content and returns metadata + preview of first 5-10 records.
    """
    if not filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files are allowed (.csv extension required).")

    text_stream = io.StringIO(file_content.decode("utf-8-sig", errors="replace"))
    reader = csv.DictReader(text_stream)

    if not reader.fieldnames:
        raise ValueError("CSV is empty or missing header row.")

    col_map = detect_column_mappings(reader.fieldnames)
    if "customer_id" not in col_map:
        raise ValueError(
            "Could not identify a Customer ID column. Please ensure your CSV contains "
            "a column such as 'customer_id', 'CustomerID', or 'id'."
        )

    # Check if there are any monetary or order indicators
    has_metrics = any(k in col_map for k in [
        "amount", "unit_price", "purchase_count", "lifetime_value", "invoice_id"
    ])
    if not has_metrics:
        raise ValueError(
            "Uploaded CSV contains customer IDs but lacks transaction amount, unit price, quantity, "
            "or order information. Customer behavioral metrics cannot be calculated."
        )

    customers, metadata = process_csv_stream(reader, col_map)

    preview_records = []
    for c in customers[:10]:
        preview_records.append({
            "customer_id": c["id"],
            "name": c.get("name", ""),
            "email": c.get("email", ""),
            "purchase_count": c["purchase_count"],
            "lifetime_value": c["lifetime_value"],
            "average_order_value": c["average_order_value"],
            "days_since_last_purchase": c["days_since_last_purchase"],
            "segment": c["segment"]
        })

    # Segment distribution breakdown for preview
    seg_counts = {}
    for c in customers:
        s = c["segment"]
        seg_counts[s] = seg_counts.get(s, 0) + 1

    return {
        "status": "valid",
        "filename": filename,
        "dataset_type": metadata["dataset_type"],
        "total_rows_detected": metadata["total_rows"],
        "total_unique_customers": metadata["total_unique_customers"],
        "total_transactions": metadata["total_transactions"],
        "invalid_rows_count": metadata["invalid_rows"],
        "detected_column_mapping": col_map,
        "segment_distribution": seg_counts,
        "preview": preview_records
    }

def import_processed_csv(file_content: bytes, filename: str, merchant_id: str, mode: str = "replace") -> Dict[str, Any]:
    """
    Parses and imports processed customer data into MongoDB for merchant_id.
    mode: 'replace' (default, wipes existing customers for merchant_id) or 'append'.
    """
    import time
    from database import customers_collection, merchants_collection

    if merchant_id == "demo_merchant_001":
        raise ValueError("Forbidden: Cannot overwrite the Demo Dataset via CSV upload. Please use a different merchant ID.")

    if not filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files are allowed (.csv extension required).")

    text_stream = io.StringIO(file_content.decode("utf-8-sig", errors="replace"))
    reader = csv.DictReader(text_stream)

    if not reader.fieldnames:
        raise ValueError("CSV is empty or missing header row.")

    col_map = detect_column_mappings(reader.fieldnames)
    if "customer_id" not in col_map:
        raise ValueError(
            "Could not identify a Customer ID column. Please ensure your CSV contains "
            "a column such as 'customer_id', 'CustomerID', or 'id'."
        )

    has_metrics = any(k in col_map for k in [
        "amount", "unit_price", "purchase_count", "lifetime_value", "invoice_id"
    ])
    if not has_metrics:
        raise ValueError(
            "Customer records exist, but purchase history could not be calculated because the "
            "uploaded CSV does not contain valid transaction amount, quantity/price, or order information."
        )

    customers, metadata = process_csv_stream(reader, col_map)
    if not customers:
        raise ValueError("No valid customer records could be processed from the CSV.")

    start_time = time.time()

    # Merchant isolation:
    # If replace, strictly delete only this merchant's customers
    if mode == "replace":
        customers_collection.delete_many({"merchant_id": merchant_id})
    elif mode == "append":
        new_ids = [c["id"] for c in customers]
        chunk_size = 1000
        for i in range(0, len(new_ids), chunk_size):
            chunk = new_ids[i:i + chunk_size]
            customers_collection.delete_many({"merchant_id": merchant_id, "id": {"$in": chunk}})

    # Batch insert
    batch = []
    batch_size = 1000
    imported = 0
    seg_counts = {}

    for c in customers:
        c["merchant_id"] = merchant_id
        s = c.get("segment", "regular")
        seg_counts[s] = seg_counts.get(s, 0) + 1
        batch.append(c)

        if len(batch) >= batch_size:
            customers_collection.insert_many(batch)
            imported += len(batch)
            batch = []

    if batch:
        customers_collection.insert_many(batch)
        imported += len(batch)

    # Check onboarding completion requirements:
    # Set onboarding_completed = true ONLY after:
    # - Merchant profile exists (business_name)
    # - Guardrails are configured (max_discount_percentage and min_margin_percentage)
    # - CSV data is successfully validated and processed (imported > 0)
    merchant_doc = merchants_collection.find_one({"merchant_id": merchant_id})
    has_business_info = bool(merchant_doc and merchant_doc.get("business_name"))
    has_guardrails = bool(
        merchant_doc and 
        merchant_doc.get("rules") and 
        merchant_doc.get("rules", {}).get("max_discount_percentage") is not None and
        merchant_doc.get("rules", {}).get("min_margin_percentage") is not None
    )
    is_completed = bool(has_business_info and has_guardrails and imported > 0)

    merchants_collection.update_one(
        {"merchant_id": merchant_id},
        {"$set": {
            "onboarding_completed": is_completed,
            "onboarding_step": "completed" if is_completed else ("guardrails_setup" if not has_guardrails else "data_setup")
        }}
    )

    duration = time.time() - start_time

    return {
        "status": "success",
        "merchant_id": merchant_id,
        "mode": mode,
        "rows_processed": metadata["total_rows"],
        "rows_imported": imported,
        "total_transactions": metadata["total_transactions"],
        "segments_calculated": seg_counts,
        "duration_seconds": round(duration, 2),
        "onboarding_completed": is_completed
    }


# ==============================================================================
# MODE B: MULTIPLE RELATED CSV FILES (CUSTOMERS, ORDERS, ORDER ITEMS)
# ==============================================================================

def decode_csv_bytes(file_bytes: bytes) -> str:
    """Decodes CSV bytes trying utf-8-sig, utf-8, and latin-1."""
    for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            return file_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return file_bytes.decode('utf-8', errors='replace')


def inspect_and_map_headers(fieldnames: List[str], required_keys: List[str], file_label: str) -> Dict[str, str]:
    """
    Auto-detects column mappings and verifies that all required keys are present.
    Raises ValueError with a clear, specific message if any required key is missing.
    """
    col_map = detect_column_mappings(fieldnames)
    missing = [req for req in required_keys if req not in col_map]
    if missing:
        missing_desc = ", ".join(missing)
        raise ValueError(
            f"{file_label} file could not be processed because required column(s) ({missing_desc}) "
            f"could not be detected. Available headers: {', '.join(fieldnames[:10])}"
        )
    return col_map


def process_relational_dataset(
    customers_content: bytes,
    orders_content: bytes,
    order_items_content: bytes
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Joins Olist-style relational dataset:
      1. order_items (order_id, price) -> aggregates order total revenue
      2. orders (order_id, customer_id, timestamp) -> joins to order_items, groups by customer_id
      3. customers (customer_id, customer_unique_id, ...) -> joins customer metrics
    Returns (processed_customers, metadata)
    """
    # 1. Parse Order Items
    items_text = decode_csv_bytes(order_items_content)
    items_reader = csv.reader(io.StringIO(items_text))
    try:
        items_headers = next(items_reader)
    except StopIteration:
        raise ValueError("Order Items CSV is empty or missing headers.")

    items_map = inspect_and_map_headers(items_headers, ["order_id", "unit_price"], "Order Items")
    item_order_id_col = items_map["order_id"]
    item_price_col = items_map["unit_price"]

    # Also detect optional freight_value
    freight_aliases = ["freight_value", "freight", "shipping"]
    freight_idx = -1
    for i, h in enumerate(items_headers):
        if normalize_col(h) in freight_aliases:
            freight_idx = i
            break

    item_order_id_idx = items_headers.index(item_order_id_col)
    item_price_idx = items_headers.index(item_price_col)

    order_revenue: Dict[str, float] = {}
    order_item_counts: Dict[str, int] = {}
    total_order_items = 0

    for row in items_reader:
        if not row or len(row) <= max(item_order_id_idx, item_price_idx):
            continue
        oid = row[item_order_id_idx].strip()
        if not oid:
            continue
        price = parse_numeric(row[item_price_idx])
        order_revenue[oid] = order_revenue.get(oid, 0.0) + price
        order_item_counts[oid] = order_item_counts.get(oid, 0) + 1
        total_order_items += 1

    # 2. Parse Orders
    orders_text = decode_csv_bytes(orders_content)
    orders_reader = csv.reader(io.StringIO(orders_text))
    try:
        orders_headers = next(orders_reader)
    except StopIteration:
        raise ValueError("Orders CSV is empty or missing headers.")

    # In orders, we need order_id, customer_id, and date
    orders_map = inspect_and_map_headers(orders_headers, ["order_id", "customer_id"], "Orders")
    orders_order_id_col = orders_map["order_id"]
    orders_cust_id_col = orders_map["customer_id"]
    orders_date_col = orders_map.get("date")

    orders_order_id_idx = orders_headers.index(orders_order_id_col)
    orders_cust_id_idx = orders_headers.index(orders_cust_id_col)
    orders_date_idx = orders_headers.index(orders_date_col) if orders_date_col else -1

    customer_orders: Dict[str, Dict[str, Any]] = {}
    total_orders = 0
    all_dates: List[datetime] = []

    for row in orders_reader:
        if not row or len(row) <= max(orders_order_id_idx, orders_cust_id_idx):
            continue
        oid = row[orders_order_id_idx].strip()
        cid = row[orders_cust_id_idx].strip()
        if not cid or not oid:
            continue

        total_orders += 1
        rev = order_revenue.get(oid, 0.0)

        dt = None
        if orders_date_idx != -1 and len(row) > orders_date_idx:
            dt = parse_date_safely(row[orders_date_idx])
            if dt:
                all_dates.append(dt)

        if cid not in customer_orders:
            customer_orders[cid] = {
                "order_ids": set(),
                "revenue": 0.0,
                "dates": []
            }

        customer_orders[cid]["order_ids"].add(oid)
        customer_orders[cid]["revenue"] += rev
        if dt:
            customer_orders[cid]["dates"].append(dt)

    dataset_reference_date = max(all_dates) if all_dates else datetime.now()

    # 3. Parse Customers
    customers_text = decode_csv_bytes(customers_content)
    customers_reader = csv.reader(io.StringIO(customers_text))
    try:
        customers_headers = next(customers_reader)
    except StopIteration:
        raise ValueError("Customers CSV is empty or missing headers.")

    cust_map = inspect_and_map_headers(customers_headers, ["customer_id"], "Customers")
    cust_id_col = cust_map["customer_id"]
    cust_id_idx = customers_headers.index(cust_id_col)

    # Optional metadata indices
    unique_id_idx = -1
    city_idx = -1
    state_idx = -1
    for i, h in enumerate(customers_headers):
        nh = normalize_col(h)
        if "unique" in nh:
            unique_id_idx = i
        elif "city" in nh:
            city_idx = i
        elif "state" in nh:
            state_idx = i

    processed_customers: List[Dict[str, Any]] = []
    seen_customer_ids = set()
    total_customer_rows = 0
    matched_customers_count = 0
    unmatched_customers_count = 0

    for row in customers_reader:
        if not row or len(row) <= cust_id_idx:
            continue
        cid = row[cust_id_idx].strip()
        if not cid or cid in seen_customer_ids:
            continue

        seen_customer_ids.add(cid)
        total_customer_rows += 1

        unique_id = row[unique_id_idx].strip() if unique_id_idx != -1 and len(row) > unique_id_idx else ""
        city = row[city_idx].strip() if city_idx != -1 and len(row) > city_idx else ""
        state = row[state_idx].strip() if state_idx != -1 and len(row) > state_idx else ""

        if cid in customer_orders:
            matched_customers_count += 1
            ord_data = customer_orders[cid]
            p_count = len(ord_data["order_ids"])
            ltv = round(ord_data["revenue"], 2)
            aov = round(ltv / p_count, 2) if p_count > 0 else 0.0

            dates = ord_data["dates"]
            last_date = max(dates) if dates else None
            days_since = (dataset_reference_date - last_date).days if last_date else 0
            if days_since < 0:
                days_since = 0

            last_date_str = last_date.strftime("%Y-%m-%d %H:%M:%S") if last_date else ""
            has_orders = True
        else:
            unmatched_customers_count += 1
            p_count = 0
            ltv = 0.0
            aov = 0.0
            days_since = 999
            last_date_str = ""
            has_orders = False

        processed_customers.append({
            "id": cid,
            "customer_unique_id": unique_id,
            "name": unique_id or f"Customer {cid[:8]}",
            "email": "",
            "city": city,
            "state": state,
            "purchase_count": p_count,
            "lifetime_value": ltv,
            "average_order_value": aov,
            "last_purchase_date": last_date_str,
            "days_since_last_purchase": days_since,
            "has_orders": has_orders,
            "cart_status": "purchased" if p_count > 0 else "no_orders"
        })

    # 4. Calculate dynamic percentile thresholds for segmentation
    active_ltvs = [c["lifetime_value"] for c in processed_customers if c["has_orders"] and c["lifetime_value"] > 0]
    if active_ltvs:
        active_ltvs.sort()
        idx_80 = int(len(active_ltvs) * 0.80)
        vip_threshold = max(250.0, float(active_ltvs[idx_80]))
    else:
        vip_threshold = 500.0

    # 5. Deterministic Segmentation
    segment_distribution: Dict[str, int] = {}
    for c in processed_customers:
        if not c["has_orders"]:
            seg = "inactive"
        else:
            seg = segment_customer(c, vip_threshold=vip_threshold)
        c["segment"] = seg
        segment_distribution[seg] = segment_distribution.get(seg, 0) + 1

    metadata = {
        "dataset_type": "relational_olist",
        "total_customer_rows": total_customer_rows,
        "total_unique_customers": len(processed_customers),
        "total_orders": total_orders,
        "total_order_items": total_order_items,
        "matched_customers_count": matched_customers_count,
        "unmatched_customers_count": unmatched_customers_count,
        "detected_column_mappings": {
            "customers": cust_map,
            "orders": orders_map,
            "order_items": items_map
        },
        "segment_distribution": segment_distribution,
        "reference_date": dataset_reference_date.strftime("%Y-%m-%d"),
        "vip_threshold": vip_threshold
    }

    return processed_customers, metadata


def validate_and_preview_relational_csv(
    customers_content: bytes,
    orders_content: bytes,
    order_items_content: bytes,
    customers_filename: str = "customers.csv",
    orders_filename: str = "orders.csv",
    order_items_filename: str = "order_items.csv"
) -> Dict[str, Any]:
    """
    Validates the 3 relational CSV files, computes the join, and generates a preview of the first 10 customers.
    """
    customers, metadata = process_relational_dataset(
        customers_content,
        orders_content,
        order_items_content
    )

    # Sort preview to highlight customers with purchases first
    preview_candidates = sorted(customers, key=lambda x: (x["lifetime_value"], x["purchase_count"]), reverse=True)
    preview = preview_candidates[:10]

    return {
        "status": "valid",
        "dataset_type": "relational_olist",
        "filenames": {
            "customers": customers_filename,
            "orders": orders_filename,
            "order_items": order_items_filename
        },
        "total_customer_rows": metadata["total_customer_rows"],
        "total_unique_customers": metadata["total_unique_customers"],
        "total_orders": metadata["total_orders"],
        "total_order_items": metadata["total_order_items"],
        "matched_customers_count": metadata["matched_customers_count"],
        "unmatched_customers_count": metadata["unmatched_customers_count"],
        "detected_column_mappings": metadata["detected_column_mappings"],
        "segment_distribution": metadata["segment_distribution"],
        "reference_date": metadata["reference_date"],
        "preview": [
            {
                "customer_id": c["id"],
                "purchase_count": c["purchase_count"],
                "lifetime_value": c["lifetime_value"],
                "average_order_value": c["average_order_value"],
                "last_purchase_date": c["last_purchase_date"],
                "days_since_last_purchase": c["days_since_last_purchase"],
                "segment": c["segment"],
                "has_orders": c["has_orders"]
            }
            for c in preview
        ]
    }


def import_processed_relational_csv(
    customers_content: bytes,
    orders_content: bytes,
    order_items_content: bytes,
    merchant_id: str,
    mode: str = "replace"
) -> Dict[str, Any]:
    """
    Parses and joins the 3 relational CSV files, calculates behavioral metrics, segments customers,
    and imports records into MongoDB partitioned by merchant_id in chunks.
    """
    from database import customers_collection, merchants_collection
    start_time = time.time()
    customers, metadata = process_relational_dataset(
        customers_content,
        orders_content,
        order_items_content
    )

    if not customers:
        raise ValueError("No customer records were found after processing the relational datasets.")

    # Merchant isolation:
    # If replace, strictly delete only this merchant's customers
    if mode == "replace":
        customers_collection.delete_many({"merchant_id": merchant_id})
    elif mode == "append":
        new_ids = [c["id"] for c in customers]
        chunk_size = 1000
        for i in range(0, len(new_ids), chunk_size):
            chunk = new_ids[i:i + chunk_size]
            customers_collection.delete_many({"merchant_id": merchant_id, "id": {"$in": chunk}})

    # Batch insert into MongoDB (chunks of 2000 for high efficiency)
    batch = []
    batch_size = 2000
    imported = 0
    seg_counts: Dict[str, int] = {}

    for c in customers:
        c["merchant_id"] = merchant_id
        s = c.get("segment", "regular")
        seg_counts[s] = seg_counts.get(s, 0) + 1
        batch.append(c)

        if len(batch) >= batch_size:
            customers_collection.insert_many(batch)
            imported += len(batch)
            batch = []

    if batch:
        customers_collection.insert_many(batch)
        imported += len(batch)

    # Check onboarding completion requirements:
    merchant_doc = merchants_collection.find_one({"merchant_id": merchant_id})
    has_business_info = bool(merchant_doc and merchant_doc.get("business_name"))
    has_guardrails = bool(
        merchant_doc and 
        merchant_doc.get("rules") and 
        merchant_doc.get("rules", {}).get("max_discount_percentage") is not None and
        merchant_doc.get("rules", {}).get("min_margin_percentage") is not None
    )
    is_completed = bool(has_business_info and has_guardrails and imported > 0)

    merchants_collection.update_one(
        {"merchant_id": merchant_id},
        {"$set": {
            "onboarding_completed": is_completed,
            "onboarding_step": "completed" if is_completed else ("guardrails_setup" if not has_guardrails else "data_setup")
        }}
    )

    duration = time.time() - start_time

    return {
        "status": "success",
        "merchant_id": merchant_id,
        "mode": mode,
        "dataset_type": "relational_olist",
        "rows_processed": metadata["total_customer_rows"],
        "rows_imported": imported,
        "total_orders": metadata["total_orders"],
        "total_order_items": metadata["total_order_items"],
        "matched_customers": metadata["matched_customers_count"],
        "unmatched_customers": metadata["unmatched_customers_count"],
        "segments_calculated": seg_counts,
        "duration_seconds": round(duration, 2),
        "onboarding_completed": is_completed
    }


