from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict
from dotenv import load_dotenv
from database import merchants_collection, offers_collection, orders_collection, campaigns_collection, customers_collection
from offer_service import generate_personalized_offer
import uuid
from datetime import datetime, timezone

load_dotenv()

app = FastAPI()

# Allow frontend (localhost:3000) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: str

class CustomerProfile(BaseModel):
    id: Optional[str] = None
    purchase_count: Optional[int] = None
    days_since_last_purchase: Optional[int] = None
    lifetime_value: Optional[float] = None
    cart_status: Optional[str] = None
    average_order_value: Optional[float] = None

@app.get("/health")
def health():
    """Test endpoint - if works, backend is running"""
    return {"status": "Backend is alive ✓"}

@app.post("/auth/login")
def login(request: LoginRequest):
    """Authenticate merchant with email and password"""
    try:
        # Find merchant by email
        merchant = merchants_collection.find_one({"email": request.email})
        
        if not merchant:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Validate password
        if merchant.get("password") != request.password:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Return merchant data (excluding password for security)
        return {
            "merchant_id": merchant.get("merchant_id"),
            "business_name": merchant.get("business_name"),
            "email": merchant.get("email")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

class OfferGenerationRequest(BaseModel):
    merchant_id: str
    customer: CustomerProfile

class OfferGenerationResponse(BaseModel):
    offer_id: str
    customer_id: Optional[str] = None
    merchant_id: str
    segment: str
    offer_details: str
    offer_status: str
    discount_percentage: float
    creation_timestamp: str
    explanation: Optional[str] = None

@app.post("/offers/generate", response_model=OfferGenerationResponse)
def generate_offer(request: OfferGenerationRequest):
    """End-to-End API: Merchant rules -> AI Generation -> Guardrails -> MongoDB"""
    try:
        # Step 1: Validate merchant
        merchant = merchants_collection.find_one({"merchant_id": request.merchant_id})
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")
            
        # Step 2: Retrieve merchant rules (default fallback if missing)
        merchant_rules = merchant.get("rules", {
            "max_discount_percentage": 20.0,
            "min_margin_percentage": 30.0
        })
        
        # Format customer dict
        if hasattr(request.customer, 'model_dump'):
            customer_dict = request.customer.model_dump(exclude_unset=True)
        else:
            customer_dict = request.customer.dict(exclude_unset=True)
            
        # Step 3: Deterministic segmentation
        from segmentation import segment_customer
        segment = segment_customer(customer_dict)
        
        # Step 4: AI Offer generation
        from claude_agent import get_offer_for_segment
        try:
            ai_offer = get_offer_for_segment(segment, merchant_rules, use_deterministic=False, customer_context=customer_dict)
            if not ai_offer or "discount_pct" not in ai_offer:
                raise ValueError("Invalid response from AI")
        except Exception as e:
            raise HTTPException(status_code=500, detail="AI generation failed")
            
        # Step 5: Validate offer
        from guardrails import validate_offer
        is_valid = validate_offer(ai_offer, merchant_rules, customer_dict)
        
        # If AI returns excessive discount, handle safely via deterministic fallback
        if not is_valid:
            ai_offer = get_offer_for_segment(segment, merchant_rules, use_deterministic=True)
            if not validate_offer(ai_offer, merchant_rules, customer_dict):
                raise HTTPException(status_code=400, detail="Generated offer violated merchant rules")
                
        # Step 6: Store in MongoDB
        offer_id = str(uuid.uuid4())
        offer_doc = {
            "offer_id": offer_id,
            "merchant_id": request.merchant_id,
            "customer_id": customer_dict.get("id"),
            "customer_segment": segment,
            "offer_description": ai_offer.get("offer", ""),
            "discount_percentage": float(ai_offer.get("discount_pct", 0)),
            "explanation": ai_offer.get("reasoning", ""),
            "status": "OFFER_CREATED",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        offers_collection.insert_one(offer_doc)
        
        # Step 7: Return response
        return {
            "offer_id": offer_id,
            "customer_id": customer_dict.get("id"),
            "merchant_id": request.merchant_id,
            "segment": segment,
            "offer_details": ai_offer.get("offer", ""),
            "offer_status": "OFFER_CREATED",
            "discount_percentage": float(ai_offer.get("discount_pct", 0)),
            "creation_timestamp": offer_doc["created_at"],
            "explanation": ai_offer.get("reasoning", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in generate_offer: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

class CampaignCreateRequest(BaseModel):
    merchant_id: str
    campaign_name: str
    campaign_description: Optional[str] = ""
    target_segment: str

class CampaignResponse(BaseModel):
    campaign_id: str
    merchant_id: str
    campaign_name: str
    target_segment: str
    status: str
    offers_generated: int
    created_at: str

@app.post("/campaigns", response_model=CampaignResponse)
def create_campaign(request: CampaignCreateRequest):
    """Creates a campaign, targeting either all customers or a specific segment."""
    try:
        # Step 1: Validate Merchant
        merchant = merchants_collection.find_one({"merchant_id": request.merchant_id})
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")
            
        # Check idempotency: If this exact campaign was created recently
        existing_campaign = campaigns_collection.find_one({
            "merchant_id": request.merchant_id,
            "campaign_name": request.campaign_name,
            "status": {"$in": ["GENERATING", "ACTIVE", "READY"]}
        })
        if existing_campaign:
            return {
                "campaign_id": existing_campaign.get("campaign_id"),
                "merchant_id": existing_campaign.get("merchant_id"),
                "campaign_name": existing_campaign.get("campaign_name"),
                "target_segment": existing_campaign.get("target_segment"),
                "status": existing_campaign.get("status"),
                "offers_generated": offers_collection.count_documents({"campaign_id": existing_campaign.get("campaign_id")}),
                "created_at": existing_campaign.get("created_at")
            }

        # Create base Campaign Doc
        campaign_id = str(uuid.uuid4())
        campaign_doc = {
            "campaign_id": campaign_id,
            "merchant_id": request.merchant_id,
            "campaign_name": request.campaign_name,
            "campaign_description": request.campaign_description,
            "target_segment": request.target_segment,
            "status": "GENERATING",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        campaigns_collection.insert_one(campaign_doc)
        
        # Step 2: Load business rules
        merchant_rules = merchant.get("business_rules", {})
        
        # Fetch target customers
        # For this prototype, we'll fetch all customers if target_segment == 'all', else filter by deterministic segment
        # Since deterministic segment isn't pre-computed in `customers_collection` usually, we fetch all and filter in memory
        all_customers = list(customers_collection.find())
        target_customers = []
        
        from segmentation import segment_customer
        from claude_agent import get_offer_for_segment
        from guardrails import validate_offer
        
        # We process customers to determine targets
        for cust in all_customers:
            cust_dict = {
                "id": str(cust.get("_id", cust.get("id"))),
                "purchase_count": cust.get("purchase_count", 0),
                "days_since_last_purchase": cust.get("days_since_last_purchase", 999),
                "lifetime_value": cust.get("lifetime_value", 0),
                "cart_status": cust.get("cart_status", "browsing"),
                "average_order_value": cust.get("average_order_value", 0)
            }
            
            # Deterministic segment
            segment = segment_customer(cust_dict)
            if request.target_segment.lower() == "all" or segment == request.target_segment.lower():
                target_customers.append((cust_dict, segment))
                
        offers_generated = 0
        failed_generations = 0
        
        for cust_dict, segment in target_customers:
            try:
                # Step 5: AI Offer Generation
                campaign_context = {
                    "name": request.campaign_name,
                    "description": request.campaign_description,
                    "target": request.target_segment
                }
                ai_offer = get_offer_for_segment(segment, merchant_rules, use_deterministic=False, customer_context=cust_dict, campaign_context=campaign_context)
                if not ai_offer or "discount_pct" not in ai_offer:
                    raise ValueError("Invalid response from AI")
                    
                # Step 6: Guardrails
                is_valid = validate_offer(ai_offer, merchant_rules, cust_dict)
                if not is_valid:
                    ai_offer = get_offer_for_segment(segment, merchant_rules, use_deterministic=True)
                    if not validate_offer(ai_offer, merchant_rules, cust_dict):
                        raise ValueError("Guardrails blocked even deterministic fallback")
                
                # Persist Offer linked to Campaign
                offer_doc = {
                    "offer_id": str(uuid.uuid4()),
                    "campaign_id": campaign_id,
                    "merchant_id": request.merchant_id,
                    "customer_id": cust_dict["id"],
                    "customer_segment": segment,
                    "offer_description": ai_offer.get("offer", ""),
                    "discount_percentage": float(ai_offer.get("discount_pct", 0)),
                    "explanation": ai_offer.get("reasoning", ""),
                    "status": "OFFER_CREATED",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                offers_collection.insert_one(offer_doc)
                offers_generated += 1
                
            except Exception as e:
                print(f"Failed to generate offer for customer {cust_dict.get('id')}: {e}")
                failed_generations += 1
                
        # Finalize Campaign
        final_status = "ACTIVE" if offers_generated > 0 else "FAILED"
        campaigns_collection.update_one(
            {"campaign_id": campaign_id},
            {"$set": {
                "status": final_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "campaign_id": campaign_id,
            "merchant_id": request.merchant_id,
            "campaign_name": request.campaign_name,
            "target_segment": request.target_segment,
            "status": final_status,
            "offers_generated": offers_generated,
            "created_at": campaign_doc["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str, merchant_id: str = Query(...)):
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id, "merchant_id": merchant_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    offers_count = offers_collection.count_documents({"campaign_id": campaign_id})
    campaign["offers_generated"] = offers_count
    return campaign

@app.get("/campaigns/{campaign_id}/offers")
def get_campaign_offers(
    campaign_id: str, 
    merchant_id: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id, "merchant_id": merchant_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    cursor = offers_collection.find({"campaign_id": campaign_id}, {"_id": 0}).skip((page - 1) * limit).limit(limit)
    offers = list(cursor)
    total = offers_collection.count_documents({"campaign_id": campaign_id})
    return {
        "items": offers,
        "page": page,
        "limit": limit,
        "total": total
    }

@app.get("/campaigns/{campaign_id}/analytics")
def get_campaign_analytics_route(campaign_id: str, merchant_id: str = Query(...)):
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id, "merchant_id": merchant_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    from analytics import get_campaign_analytics
    analytics = get_campaign_analytics(campaign_id)
    if analytics is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return analytics

@app.get("/campaigns/{campaign_id}/analytics/segments")
def get_campaign_segment_analytics_route(campaign_id: str, merchant_id: str = Query(...)):
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id, "merchant_id": merchant_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    from analytics import get_campaign_segment_analytics
    segments = get_campaign_segment_analytics(campaign_id)
    if segments is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return segments

@app.get("/campaigns/{campaign_id}/insights")
def get_campaign_insights(campaign_id: str, merchant_id: str = Query(...)):
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id, "merchant_id": merchant_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    from analytics import get_campaign_analytics, get_campaign_segment_analytics
    from claude_agent import generate_campaign_insights
    
    analytics = get_campaign_analytics(campaign_id)
    if analytics is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    segments = get_campaign_segment_analytics(campaign_id) or []
    
    insights = generate_campaign_insights(campaign, analytics, segments)
    insights["campaign_id"] = campaign_id
    
    return insights


class OrderRequest(BaseModel):
    amount: float
    offer_id: Optional[str] = None
    currency: Optional[str] = "INR"
    receipt: Optional[str] = None
    notes: Optional[Dict[str, str]] = None

class OrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    status: str

class CreateOfferPaymentRequest(BaseModel):
    original_amount: float
    currency: Optional[str] = "INR"
    receipt: Optional[str] = None
    notes: Optional[Dict[str, str]] = None

@app.post("/offers/{offer_id}/create-payment-order", response_model=OrderResponse)
def create_payment_order_for_offer(offer_id: str, request: CreateOfferPaymentRequest):
    """Create a Razorpay order securely tied to an existing offer"""
    try:
        offer = offers_collection.find_one({"offer_id": offer_id})
        if not offer:
            raise HTTPException(status_code=404, detail="Offer not found")
            
        if offer.get("status") in ["PAYMENT_VERIFIED", "CANCELLED", "PAID"]:
            raise HTTPException(status_code=400, detail="Offer is no longer eligible for payment")
            
        # Calculate expected final amount in INR
        discount = float(offer.get("discount_percentage", 0))
        final_amount_inr = request.original_amount * (1.0 - discount / 100.0)
        expected_amount_paise = int(final_amount_inr * 100)
        
        # Check if pending order already exists and matches expected amount
        existing_order = orders_collection.find_one({
            "offer_id": offer_id,
            "payment_status": {"$in": ["ORDER_CREATED", "PAYMENT_PENDING"]}
        })
        
        if existing_order and existing_order.get("amount") == expected_amount_paise:
            return {
                "order_id": existing_order.get("razorpay_order_id"),
                "amount": existing_order.get("amount"),
                "currency": existing_order.get("currency"),
                "status": existing_order.get("payment_status")
            }
            
        # Create new order via Razorpay service
        from razorpay_service import create_razorpay_order
        order = create_razorpay_order(
            amount_inr=final_amount_inr,
            currency=request.currency,
            receipt=request.receipt,
            notes=request.notes
        )
        
        if not order:
            raise HTTPException(status_code=502, detail="Failed to create Razorpay order")
            
        # Store in MongoDB
        order_doc = {
            "offer_id": offer_id,
            "merchant_id": offer.get("merchant_id"),
            "customer_id": offer.get("customer_id"),
            "razorpay_order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "payment_status": "ORDER_CREATED",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        from pymongo.errors import DuplicateKeyError
        try:
            orders_collection.insert_one(order_doc)
        except DuplicateKeyError:
            pass # Unique index on razorpay_order_id handles duplicates safely
            
        # Update offer status
        offers_collection.update_one(
            {"offer_id": offer_id},
            {"$set": {"status": "ORDER_CREATED"}}
        )
            
        return {
            "order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "status": "ORDER_CREATED"
        }
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error in create_payment_order_for_offer: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/payments/create-order", response_model=OrderResponse)
def create_order(request: OrderRequest):
    """Create a Razorpay order in test mode"""
    try:
        from razorpay_service import create_razorpay_order
        
        if request.offer_id:
            offer = offers_collection.find_one({"offer_id": request.offer_id})
            if not offer:
                raise ValueError(f"Invalid offer_id: {request.offer_id}")
                
        order = create_razorpay_order(
            amount_inr=request.amount,
            currency=request.currency,
            receipt=request.receipt,
            notes=request.notes
        )
        
        if not order:
            raise HTTPException(status_code=500, detail="Failed to create Razorpay order")
            
        order_doc = {
            "offer_id": request.offer_id,
            "razorpay_order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "payment_status": "ORDER_CREATED",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Handle duplicate insert exception if Razorpay surprisingly returned a duplicate ID
        from pymongo.errors import DuplicateKeyError
        try:
            orders_collection.insert_one(order_doc)
        except DuplicateKeyError:
            print(f"Warning: Duplicate order ID {order.get('id')}")
            
        return {
            "order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "status": order.get("status")
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

class PaymentVerificationRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class PaymentVerificationResponse(BaseModel):
    status: str
    message: str
    verified: bool

@app.post("/payments/verify", response_model=PaymentVerificationResponse)
def verify_payment(request: PaymentVerificationRequest):
    """Verify Razorpay payment signature on the server and update DB"""
    try:
        from razorpay_service import verify_payment_signature
        
        # Step 2: Find the stored order
        order_record = orders_collection.find_one({"razorpay_order_id": request.razorpay_order_id})
        
        # Step 3: If order not found, return 404
        if not order_record:
            raise HTTPException(status_code=404, detail="Order not found")
            
        # Step 5: Idempotency check
        if order_record.get("payment_status") == "PAYMENT_VERIFIED" and order_record.get("razorpay_payment_id") == request.razorpay_payment_id:
            return {
                "status": "success",
                "message": "Payment already verified successfully",
                "verified": True
            }
            
        # Step 4: Verify signature
        is_valid = verify_payment_signature(
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature
        )
        
        if is_valid:
            # Step 6: Verification succeeds
            now = datetime.now(timezone.utc).isoformat()
            
            # Update order
            orders_collection.update_one(
                {"razorpay_order_id": request.razorpay_order_id},
                {"$set": {
                    "razorpay_payment_id": request.razorpay_payment_id,
                    "payment_status": "PAYMENT_VERIFIED",
                    "verified_at": now
                }}
            )
            
            # Update corresponding offer if offer_id is present
            offer_id = order_record.get("offer_id")
            if offer_id:
                offers_collection.update_one(
                    {"offer_id": offer_id},
                    {"$set": {
                        "status": "PAYMENT_VERIFIED",
                        "verified_at": now
                    }}
                )
                
            return {
                "status": "success",
                "message": "Payment signature verified successfully",
                "verified": True
            }
        else:
            # Step 5: Verification fails
            # We preserve the previous state and do NOT mark as paid.
            raise HTTPException(status_code=400, detail="Invalid payment signature")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in verify_payment: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Run with: uvicorn main:app --reload

# --- DATA RETRIEVAL APIS ---

@app.get("/customers")
def get_customers(
    merchant_id: str = Query(...),
    segment: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    # Enforce merchant isolation: only return customers who have interacted with this merchant
    customer_ids = offers_collection.distinct("customer_id", {"merchant_id": merchant_id})
    
    query = {"id": {"$in": customer_ids}}
    cursor = customers_collection.find(query, {"_id": 0}).skip((page - 1) * limit).limit(limit)
    customers = list(cursor)
    
    from segmentation import segment_customer
    filtered_customers = []
    for c in customers:
        seg = segment_customer(c)
        c["segment"] = seg
        if not segment or seg == segment:
            filtered_customers.append(c)
            
    return {
        "items": filtered_customers,
        "page": page,
        "limit": limit,
        "total": len(customer_ids)
    }

@app.get("/customers/{customer_id}")
def get_customer(customer_id: str, merchant_id: str = Query(...)):
    # Check isolation
    has_interaction = offers_collection.find_one({"customer_id": customer_id, "merchant_id": merchant_id})
    if not has_interaction:
        raise HTTPException(status_code=404, detail="Customer not found or access denied")
        
    customer = customers_collection.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    from segmentation import segment_customer
    customer["segment"] = segment_customer(customer)
    return customer

@app.get("/customers/{customer_id}/segment")
def get_customer_segment(customer_id: str, merchant_id: str = Query(...)):
    has_interaction = offers_collection.find_one({"customer_id": customer_id, "merchant_id": merchant_id})
    if not has_interaction:
        raise HTTPException(status_code=404, detail="Customer not found or access denied")
        
    customer = customers_collection.find_one({"id": customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    from segmentation import segment_customer
    return {
        "customer_id": customer_id,
        "segment": segment_customer(customer)
    }

@app.get("/offers")
def get_offers(
    merchant_id: str = Query(...),
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    segment: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    query = {"merchant_id": merchant_id}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if status:
        query["status"] = status
    if segment:
        query["customer_segment"] = segment
        
    cursor = offers_collection.find(query, {"_id": 0}).skip((page - 1) * limit).limit(limit)
    offers = list(cursor)
    total = offers_collection.count_documents(query)
    
    return {
        "items": offers,
        "page": page,
        "limit": limit,
        "total": total
    }

@app.get("/offers/{offer_id}")
def get_offer(offer_id: str, merchant_id: str = Query(...)):
    offer = offers_collection.find_one({"offer_id": offer_id, "merchant_id": merchant_id}, {"_id": 0})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer

@app.get("/campaigns")
def get_campaigns(
    merchant_id: str = Query(...),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    query = {"merchant_id": merchant_id}
    if status:
        query["status"] = status
        
    cursor = campaigns_collection.find(query, {"_id": 0}).skip((page - 1) * limit).limit(limit)
    campaigns = list(cursor)
    total = campaigns_collection.count_documents(query)
    
    return {
        "items": campaigns,
        "page": page,
        "limit": limit,
        "total": total
    }