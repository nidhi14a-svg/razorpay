from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict
from dotenv import load_dotenv
from database import merchants_collection, offers_collection, orders_collection
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
            ai_offer = get_offer_for_segment(segment, merchant_rules, use_deterministic=False)
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
            "creation_timestamp": offer_doc["created_at"]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in generate_offer: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
        
        is_valid = verify_payment_signature(
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature
        )
        
        order_record = orders_collection.find_one({"razorpay_order_id": request.razorpay_order_id})
        
        if is_valid:
            if order_record:
                orders_collection.update_one(
                    {"razorpay_order_id": request.razorpay_order_id},
                    {"$set": {
                        "razorpay_payment_id": request.razorpay_payment_id,
                        "payment_status": "PAYMENT_VERIFIED",
                        "verified_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            return {
                "status": "success",
                "message": "Payment signature verified successfully",
                "verified": True
            }
        else:
            if order_record:
                orders_collection.update_one(
                    {"razorpay_order_id": request.razorpay_order_id},
                    {"$set": {
                        "payment_status": "PAYMENT_FAILED"
                    }}
                )
            raise HTTPException(status_code=400, detail="Invalid payment signature")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Run with: uvicorn main:app --reload