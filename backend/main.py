from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict
from dotenv import load_dotenv
from database import merchants_collection, offers_collection, orders_collection, campaigns_collection, customers_collection, optimizations_collection
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

class OfferRecommendationRequest(BaseModel):
    merchant_id: str
    customer: CustomerProfile
    campaign_id: Optional[str] = None

class OfferRecommendationResponse(BaseModel):
    customer_id: Optional[str] = None
    campaign_id: Optional[str] = None
    segment: str
    recommended_offer_type: str
    recommended_discount_percentage: float
    reason: str
    confidence: float
    guardrail_status: str

@app.post("/offers/recommend", response_model=OfferRecommendationResponse)
def recommend_offer(request: OfferRecommendationRequest):
    """Authoritative recommendation endpoint using AI and Guardrails without persistence"""
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
        
        # Step 3: Validate customer exists
        # In a real system, you might fetch customer from customers_collection,
        # but here we accept the provided profile or fetch if ID provided.
        customer_dict = request.customer.model_dump(exclude_unset=True) if hasattr(request.customer, 'model_dump') else request.customer.dict(exclude_unset=True)
        if "id" in customer_dict:
            db_cust = customers_collection.find_one({"id": customer_dict["id"]})
            if db_cust:
                customer_dict.update(db_cust)
            else:
                raise HTTPException(status_code=404, detail="Customer not found")
                
        # Step 4: Retrieve campaign context if campaign_id provided
        campaign_context = None
        if request.campaign_id:
            campaign = campaigns_collection.find_one({"campaign_id": request.campaign_id, "merchant_id": request.merchant_id})
            if not campaign:
                raise HTTPException(status_code=404, detail="Campaign not found")
            campaign_context = {
                "name": campaign.get("campaign_name", "Unknown"),
                "description": campaign.get("campaign_description", ""),
                "target": campaign.get("target_segment", "All")
            }

        from decision_engine import recommend_offer_strategy
        
        # Steps 5-11 handled in decision_engine.py
        decision = recommend_offer_strategy(
            merchant_id=request.merchant_id,
            customer=customer_dict,
            merchant_rules=merchant_rules,
            campaign_context=campaign_context,
            campaign_id=request.campaign_id
        )
        
        return decision
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in recommend_offer: {e}")
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
            
        # Step 3, 4, 5: AI Offer Decision Engine
        from decision_engine import run_offer_decision_engine
        try:
            decision = run_offer_decision_engine(
                merchant_id=request.merchant_id,
                customer=customer_dict,
                merchant_rules=merchant_rules
            )
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error in generate_offer: {repr(e)}")
            raise HTTPException(status_code=500, detail="AI generation failed")
        
        segment = decision["segment"]
                
        # Step 6: Store in MongoDB
        offer_id = str(uuid.uuid4())
        offer_doc = {
            "offer_id": offer_id,
            "merchant_id": request.merchant_id,
            "customer_id": customer_dict.get("id"),
            "customer_segment": segment,
            "offer_description": decision["offer_details"],
            "discount_percentage": decision["discount_percentage"],
            "explanation": decision["explanation"],
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
            "offer_details": decision["offer_details"],
            "offer_status": "OFFER_CREATED",
            "discount_percentage": decision["discount_percentage"],
            "creation_timestamp": offer_doc["created_at"],
            "explanation": decision["explanation"]
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
    target_segment: str = "auto"

class CampaignResponse(BaseModel):
    campaign_id: str
    merchant_id: str
    campaign_name: str
    target_segment: str
    status: str
    offers_generated: int
    created_at: str
    offers: Optional[Dict[str, Any]] = {}
    strategy: Optional[Dict[str, Any]] = None

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
        merchant_rules = merchant.get("rules", {})
        
        # Fetch target customers
        all_customers = list(customers_collection.find({"merchant_id": request.merchant_id}))
        target_customers = []
        
        from decision_engine import run_offer_decision_engine
        from segmentation import segment_customer
        from historical_analyzer import get_historical_learning_insights
        from merchant_intelligence import get_merchant_campaign_intelligence
        from claude_agent import determine_campaign_strategy
        
        # We process customers to determine segments and stats
        all_segments_data = {}
        for cust in all_customers:
            cust_dict = {
                "id": str(cust.get("_id", cust.get("id"))),
                "purchase_count": cust.get("purchase_count", 0),
                "days_since_last_purchase": cust.get("days_since_last_purchase", 999),
                "lifetime_value": cust.get("lifetime_value", 0),
                "cart_status": cust.get("cart_status", "browsing"),
                "average_order_value": cust.get("average_order_value", 0)
            }
            segment = segment_customer(cust_dict)
            if segment not in all_segments_data:
                all_segments_data[segment] = {"customers": [], "stats": {}}
            all_segments_data[segment]["customers"].append(cust_dict)
            
        # Aggregate stats per segment for AI context
        for segment, data in all_segments_data.items():
            customers = data["customers"]
            data["stats"] = {
                "segment_name": segment,
                "customer_count": len(customers),
                "average_lifetime_value": sum(c.get("lifetime_value", 0) for c in customers) / len(customers) if customers else 0,
                "average_purchase_count": sum(c.get("purchase_count", 0) for c in customers) / len(customers) if customers else 0,
                "cart_abandoned_count": sum(1 for c in customers if c.get("cart_status") == "abandoned")
            }
            
        # Strategy Generation
        historical_learning = get_historical_learning_insights(request.merchant_id)
        intelligence = get_merchant_campaign_intelligence(request.merchant_id)
        
        strategy_context = {
            "merchant_rules": merchant_rules,
            "segment_stats": {k: v["stats"] for k, v in all_segments_data.items()},
            "historical_learning": historical_learning,
            "campaign_intelligence": intelligence
        }
        
        strategy_decision = determine_campaign_strategy(
            goal=request.campaign_description or request.campaign_name,
            merchant_context=strategy_context
        )
        
        ai_target_segments = strategy_decision.get("target_segments", [])
        
        # Filter segments to target
        segments_data = {}
        if request.target_segment.lower() in ["all", "auto"]:
            # Use AI selected segments
            for seg in ai_target_segments:
                if seg in all_segments_data:
                    segments_data[seg] = all_segments_data[seg]
            # Fallback if AI selected nothing but we need something
            if not segments_data and all_segments_data:
                # Safest fallback is existing segments
                segments_data = all_segments_data
        else:
            # Respect explicit manual selection
            explicit_seg = request.target_segment.lower()
            if explicit_seg in all_segments_data:
                segments_data[explicit_seg] = all_segments_data[explicit_seg]
        for segment, data in segments_data.items():
            customers = data["customers"]
            data["stats"] = {
                "segment_name": segment,
                "customer_count": len(customers),
                "average_lifetime_value": sum(c.get("lifetime_value", 0) for c in customers) / len(customers) if customers else 0,
                "average_purchase_count": sum(c.get("purchase_count", 0) for c in customers) / len(customers) if customers else 0,
                "cart_abandoned_count": sum(1 for c in customers if c.get("cart_status") == "abandoned")
            }
                
        offers_generated = 0
        failed_generations = 0
        generated_offers = {}
        
        # Generate exactly ONE offer per segment, then apply to all customers in segment
        for segment, data in segments_data.items():
            try:
                # Step 5 & 6: AI Offer Decision Engine
                campaign_context = {
                    "name": request.campaign_name,
                    "description": request.campaign_description,
                    "target": request.target_segment,
                    "strategy": strategy_decision
                }
                decision = run_offer_decision_engine(
                    merchant_id=request.merchant_id,
                    segment=segment,
                    segment_stats=data["stats"],
                    merchant_rules=merchant_rules,
                    campaign_context=campaign_context
                )
                
                # Keep one sample offer per segment for the UI response and final campaign document
                generated_offers[segment] = {
                    "discount_pct": decision["discount_percentage"],
                    "offer": decision["offer_details"],
                    "reasoning": decision["explanation"]
                }
                
                # Persist Offer linked to Campaign for EVERY customer in this segment
                for cust_dict in data["customers"]:
                    offer_doc = {
                        "offer_id": str(uuid.uuid4()),
                        "campaign_id": campaign_id,
                        "merchant_id": request.merchant_id,
                        "customer_id": cust_dict["id"],
                        "customer_segment": segment,
                        "offer_description": decision["offer_details"],
                        "discount_percentage": decision["discount_percentage"],
                        "explanation": decision["explanation"],
                        "status": "OFFER_CREATED",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    offers_collection.insert_one(offer_doc)
                    offers_generated += 1
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Failed to generate offer for segment {segment}: {e}")
                failed_generations += 1
                
        # Finalize Campaign
        final_status = "ACTIVE" if offers_generated > 0 else "FAILED"
        campaigns_collection.update_one(
            {"campaign_id": campaign_id},
            {"$set": {
                "status": final_status,
                "target_segments": list(generated_offers.keys()),
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
            "created_at": campaign_doc["created_at"],
            "offers": generated_offers,
            "strategy": strategy_decision
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
def get_campaign_analytics_segments_route(campaign_id: str, merchant_id: str = Query(...)):
    """Get segment-level analytics for a campaign"""
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id, "merchant_id": merchant_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    from analytics import get_campaign_segment_analytics
    stats = get_campaign_segment_analytics(campaign_id)
    return stats or []

@app.get("/merchants/{merchant_id}/historical-performance")
def get_historical_performance_route(merchant_id: str):
    from analytics import get_merchant_historical_performance
    return get_merchant_historical_performance(merchant_id)

@app.get("/merchants/{merchant_id}/historical-performance/segments")
def get_historical_performance_segments_route(merchant_id: str):
    from analytics import get_merchant_segment_performance
    return get_merchant_segment_performance(merchant_id)

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

@app.post("/campaigns/{campaign_id}/optimize")
def optimize_campaign_route(campaign_id: str, merchant_id: str = Query(...)):
    """Generate optimization recommendations for a campaign"""
    try:
        from optimization_agent import analyze_campaign_for_optimization
        
        result = analyze_campaign_for_optimization(
            campaign_id=campaign_id,
            merchant_id=merchant_id
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        print(f"Error in optimize_campaign_route: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/optimizations")
def get_optimizations_route(merchant_id: str = Query(...)):
    """Fetch all optimizations for a merchant's campaigns"""
    try:
        # Sort by generated_at descending (newest first)
        cursor = optimizations_collection.find({"merchant_id": merchant_id}, {"_id": 0}).sort("generated_at", -1)
        return list(cursor)
    except Exception as e:
        print(f"Error in get_optimizations_route: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/optimizations/{optimization_id}/approve")
def approve_optimization_route(optimization_id: str, merchant_id: str = Query(...)):
    try:
        from optimization_execution import approve_optimization
        return approve_optimization(optimization_id, merchant_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

class RejectionRequest(BaseModel):
    reason: Optional[str] = None

@app.post("/optimizations/{optimization_id}/reject")
def reject_optimization_route(optimization_id: str, request: RejectionRequest, merchant_id: str = Query(...)):
    try:
        from optimization_execution import reject_optimization
        return reject_optimization(optimization_id, merchant_id, request.reason)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/optimizations/{optimization_id}/execute")
def execute_optimization_route(optimization_id: str, merchant_id: str = Query(...)):
    try:
        from optimization_execution import execute_optimization
        return execute_optimization(optimization_id, merchant_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/optimizations/{optimization_id}/feedback")
def evaluate_optimization_feedback_route(optimization_id: str, merchant_id: str = Query(...)):
    """Evaluate and record the performance of an executed optimization."""
    try:
        from feedback_service import evaluate_optimization_outcome
        return evaluate_optimization_outcome(optimization_id, merchant_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error in evaluate_optimization_feedback_route: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/merchants/{merchant_id}/intelligence")
def get_merchant_intelligence_route(merchant_id: str):
    """Retrieve multi-campaign intelligence and AI insights for a merchant."""
    try:
        from merchant_intelligence import get_merchant_campaign_intelligence
        return get_merchant_campaign_intelligence(merchant_id)
    except ValueError as ve:
        if str(ve) == "Merchant not found":
            raise HTTPException(status_code=404, detail="Merchant not found")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error in get_merchant_intelligence_route: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

class AgentRunRequest(BaseModel):
    merchant_id: str

@app.post("/agent/run")
def run_revenue_agent_route(request: AgentRunRequest):
    """Run the holistic AI Revenue Agent to get an evidence-based campaign strategy."""
    try:
        from revenue_agent import run_revenue_agent
        return run_revenue_agent(request.merchant_id)
    except ValueError as ve:
        if str(ve) == "Merchant not found":
            raise HTTPException(status_code=404, detail="Merchant not found")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error in run_revenue_agent_route: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")