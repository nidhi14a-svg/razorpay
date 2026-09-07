from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Form, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict
from dotenv import load_dotenv
from database import merchants_collection, offers_collection, orders_collection, campaigns_collection, customers_collection, optimizations_collection, campaign_executions_collection
from offer_service import generate_personalized_offer
import uuid
import os
import logging
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Basic Setup
app = FastAPI(title="RAZZZ AI Revenue Agent API")

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

from guardrails import validate_merchant_guardrails

class GuardrailsRequest(BaseModel):
    max_discount_percentage: Optional[float] = None
    min_order_value: Optional[float] = 0.0
    free_shipping_allowed: Optional[bool] = True
    max_campaign_budget: Optional[float] = None
    high_value_customer_protection: Optional[bool] = True
    contact_frequency_days: Optional[int] = 7
    min_margin_percentage: Optional[float] = None

class BusinessProfileRequest(BaseModel):
    full_name: Optional[str] = None
    business_name: str
    business_category: Optional[str] = "E-commerce"
    business_description: Optional[str] = ""

# Development bypass: set to False in .env to allow localhost testing without email verification
REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() in ("true", "1", "yes")

import hashlib
import os
import binascii

def hash_password(password: str) -> str:
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')

def verify_password(stored_password: str, provided_password: str) -> bool:
    if stored_password == provided_password:
        return True
    if len(stored_password) >= 64:
        salt = stored_password[:64].encode('ascii')
        stored_pwdhash = stored_password[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha512', provided_password.encode('utf-8'), salt, 100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        return pwdhash == stored_pwdhash
    return False

@app.get("/health")
def health():
    """Test endpoint - if works, backend is running"""
    return {"status": "Backend is alive ✓"}

@app.post("/auth/login")
def login(request: LoginRequest):
    """Authenticate merchant with email and password"""
    try:
        merchant = merchants_collection.find_one({"email": request.email})
        if not merchant:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not verify_password(merchant.get("password"), request.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        # Email verification check (bypassed in development mode when REQUIRE_EMAIL_VERIFICATION=False)
        if REQUIRE_EMAIL_VERIFICATION and not merchant.get("email_verified", True):
            return {
                "requires_verification": True,
                "email": merchant.get("email"),
                "detail": "Email address must be verified before logging in."
            }
        
        has_business_info = bool(merchant.get("business_name"))
        has_guardrails = bool(
            merchant.get("rules") and 
            merchant.get("rules", {}).get("max_discount_percentage") is not None and
            merchant.get("rules", {}).get("min_margin_percentage") is not None
        )
        has_customers = customers_collection.count_documents({"merchant_id": merchant.get("merchant_id")}) > 0
        
        onboarding_completed = bool(
            (merchant.get("onboarding_completed") is True and has_business_info and has_guardrails and has_customers) or
            (has_business_info and has_guardrails and has_customers) or
            (merchant.get("merchant_id") == "demo_merchant_001" and has_guardrails and has_customers)
        )
        if onboarding_completed and not merchant.get("onboarding_completed"):
            merchants_collection.update_one(
                {"_id": merchant["_id"]},
                {"$set": {"onboarding_completed": True, "onboarding_step": "completed"}}
            )
        elif not onboarding_completed and merchant.get("onboarding_completed"):
            merchants_collection.update_one(
                {"_id": merchant["_id"]},
                {"$set": {"onboarding_completed": False}}
            )

        session_token = secrets.token_hex(32)
        merchants_collection.update_one(
            {"_id": merchant["_id"]},
            {"$set": {"session_token": session_token}}
        )
        
        return {
            "merchant_id": merchant.get("merchant_id"),
            "full_name": merchant.get("full_name"),
            "business_name": merchant.get("business_name"),
            "email": merchant.get("email"),
            "token": session_token,
            "onboarding_completed": onboarding_completed
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_current_merchant(authorization: str = Header(None)) -> str:
    """Dependency to get merchant_id from Authorization token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    merchant = merchants_collection.find_one({"session_token": token})
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid session token")
        
    return merchant.get("merchant_id")

class RegisterRequest(BaseModel):
    full_name: str
    business_name: str
    email: str
    password: str

def send_verification_email(to_email: str, token: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", smtp_username)

    if not smtp_username or not smtp_password:
        logger.error("SMTP_USERNAME or SMTP_PASSWORD environment variables are missing.")
        raise Exception("Email service is not configured.")

    verification_link = f"http://localhost:3000/verify-email?token={token}"
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = "Verify your RAZZZ account"

    body = f"Hello,\n\nPlease verify your RAZZZ account by clicking the following link:\n{verification_link}\n\nThanks,\nThe RAZZZ Team"
    msg.attach(MIMEText(body, 'plain'))

    try:
        logger.info(f"Attempting to send verification email to {to_email} via {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"Verification email successfully sent to {to_email}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed for {smtp_username}: {e}")
        raise Exception("Email authentication failed.") from e
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        raise Exception("Failed to send verification email.") from e

@app.post("/auth/register")
def register(request: RegisterRequest):
    try:
        existing = merchants_collection.find_one({"email": request.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
            
        merchant_id = f"merch_{uuid.uuid4().hex[:12]}"
        verification_token = str(uuid.uuid4())
        
        merchant_doc = {
            "merchant_id": merchant_id,
            "full_name": request.full_name,
            "business_name": request.business_name,
            "email": request.email,
            "password": hash_password(request.password),
            "email_verified": False,
            "verification_token": verification_token,
            "onboarding_completed": False,
            "onboarding_step": "welcome",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        merchants_collection.insert_one(merchant_doc)
        print(f"[AUTH DEV] Verification link: http://localhost:3000/verify-email?token={verification_token}")
        
        try:
            send_verification_email(request.email, verification_token)
        except Exception as e:
            logger.warning(f"[DEV BYPASS] Verification email delivery skipped/failed: {e}")
            if REQUIRE_EMAIL_VERIFICATION:
                raise HTTPException(status_code=500, detail=f"User registered, but failed to send verification email: {str(e)}")
        
        return {
            "status": "success", 
            "message": "Registration successful. You may now log in to begin onboarding." if not REQUIRE_EMAIL_VERIFICATION else "Registration successful. Please check your email to verify your account.",
            "require_email_verification": REQUIRE_EMAIL_VERIFICATION
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

class TokenRequest(BaseModel):
    token: str

@app.post("/auth/verify-email")
def verify_email(request: TokenRequest):
    try:
        merchant = merchants_collection.find_one({"verification_token": request.token})
        if not merchant:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
            
        merchants_collection.update_one(
            {"_id": merchant["_id"]},
            {"$set": {"email_verified": True}, "$unset": {"verification_token": ""}}
        )
        return {"status": "success", "message": "Email verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Verification failed")

class ResendVerificationRequest(BaseModel):
    email: str

@app.post("/auth/resend-verification")
def resend_verification(request: ResendVerificationRequest):
    try:
        merchant = merchants_collection.find_one({"email": request.email})
        if not merchant:
            return {"status": "success", "message": "If an account exists, a verification email was sent."}
            
        if merchant.get("email_verified"):
            return {"status": "success", "message": "Account is already verified."}
            
        verification_token = str(uuid.uuid4())
        merchants_collection.update_one(
            {"_id": merchant["_id"]},
            {"$set": {"verification_token": verification_token}}
        )
        
        try:
            send_verification_email(request.email, verification_token)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to resend verification email: {str(e)}")
        
        return {"status": "success", "message": "If an account exists, a verification email was sent."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend verification: {e}")
        raise HTTPException(status_code=500, detail="Failed to resend verification")

class ForgotPasswordRequest(BaseModel):
    email: str

@app.post("/auth/forgot-password")
def forgot_password(request: ForgotPasswordRequest):
    try:
        merchant = merchants_collection.find_one({"email": request.email})
        if not merchant:
            # Generic response to prevent email enumeration
            return {"status": "success", "message": "If an account exists with that email, a password reset link has been sent."}
            
        reset_token = str(uuid.uuid4())
        merchants_collection.update_one(
            {"_id": merchant["_id"]},
            {"$set": {"reset_token": reset_token}}
        )
        
        print("\n" + "="*50)
        print("DEV MODE: Password Reset Email Simulation")
        print(f"To: {request.email}")
        print(f"Link: http://localhost:3000/reset-password?token={reset_token}")
        print("="*50 + "\n")
        
        return {"status": "success", "message": "If an account exists with that email, a password reset link has been sent."}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process request")

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@app.post("/auth/reset-password")
def reset_password(request: ResetPasswordRequest):
    try:
        merchant = merchants_collection.find_one({"reset_token": request.token})
        if not merchant:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
            
        merchants_collection.update_one(
            {"_id": merchant["_id"]},
            {"$set": {"password": hash_password(request.new_password)}, "$unset": {"reset_token": ""}}
        )
        
        return {"status": "success", "message": "Password has been reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to reset password")

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

        # Step 2: Load business rules
        merchant_rules = merchant.get("rules")
        if not merchant_rules or "max_discount_percentage" not in merchant_rules:
            raise HTTPException(
                status_code=400,
                detail="Merchant guardrail rules are not configured. Complete your business rules before generating campaigns."
            )

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
        
        # Fetch target customers
        all_customers = list(customers_collection.find({"merchant_id": request.merchant_id}))
        
        from claude_agent import generate_campaign_intelligence
        from guardrails import validate_offer
        from historical_analyzer import get_historical_learning_insights
        
        historical_learning = get_historical_learning_insights(request.merchant_id)
        
        # Call the unified data-driven AI intelligence
        intelligence = generate_campaign_intelligence(
            goal=request.campaign_description or request.campaign_name,
            customers=all_customers,
            merchant_rules=merchant_rules,
            historical_context=historical_learning
        )
        
        # Defensive type checking for AI intelligence output
        if not isinstance(intelligence, dict):
            intelligence = {"segments": []}
            
        segments_data = intelligence.get("segments", [])
        if not isinstance(segments_data, list):
            segments_data = []
        
        offers_generated = 0
        generated_offers = {}
        eligible_customers_count = 0
        
        # Process each dynamically generated segment
        for segment_info in segments_data:
            segment_name = segment_info.get("segment", "Unknown Segment")
            customer_ids = segment_info.get("customer_ids", [])
            
            if not customer_ids:
                continue
                
            # Validate the offer against merchant rules
            # We construct a mock customer with purchase_count=0 to pass the now-removed loyal check safely,
            # though validate_offer mainly checks max_discount and min_margin.
            is_valid = validate_offer(segment_info, merchant_rules, {"purchase_count": 0})
            
            if not is_valid:
                print(f"❌ Guardrails blocked AI offer for {segment_name}. Clamping discount.")
                segment_info["discount_pct"] = min(
                    segment_info.get("discount_pct", 0), 
                    merchant_rules.get("max_discount_percentage", 20)
                )
                if not isinstance(segment_info.get("merchant_constraints"), list):
                    segment_info["merchant_constraints"] = []
                segment_info["merchant_constraints"].append("Forced discount clamp due to rules violation")
                
            generated_offers[segment_name] = {
                "discount_pct": segment_info.get("discount_pct", 0),
                "offer": segment_info.get("offer", ""),
                "reasoning": segment_info.get("reasoning", "")
            }
            
            # Map the customer_ids back to the real customer data
            matched_customers = [c for c in all_customers if c.get("id") in customer_ids or str(c.get("_id")) in customer_ids]
            eligible_customers_count += len(matched_customers)
            
            for cust in matched_customers:
                offer_doc = {
                    "offer_id": str(uuid.uuid4()),
                    "campaign_id": campaign_id,
                    "merchant_id": request.merchant_id,
                    "customer_id": str(cust.get("_id", cust.get("id"))),
                    "customer_name": cust.get("name", "Unknown"),
                    "customer_email": cust.get("email", ""),
                    "customer_segment": segment_name,
                    "offer_description": segment_info.get("offer", ""),
                    "discount_percentage": segment_info.get("discount_pct", 0),
                    "explanation": segment_info.get("reasoning", ""),
                    
                    # Expanded AI fields
                    "campaign_goal": request.campaign_description or request.campaign_name,
                    "why_this_segment": segment_info.get("segment_description", ""),
                    "recommended_strategy": segment_info.get("strategy", ""),
                    "why_this_offer": segment_info.get("reasoning", ""),
                    "duration": f"{segment_info.get('duration_days', 7)} days",
                    "merchant_constraints": ", ".join(segment_info.get("merchant_constraints", [])),
                    "expected_objective": segment_info.get("expected_objective", ""),
                    "confidence": segment_info.get("confidence", "medium"),
                    "data_evidence": ", ".join(segment_info.get("data_evidence", [])),
                    
                    "status": "GENERATED",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                offers_collection.insert_one(offer_doc)
                offers_generated += 1
                
        # Finalize Campaign
        final_status = "ACTIVE" if offers_generated > 0 else "FAILED"
        customers_analyzed = len(all_customers)
        
        campaigns_collection.update_one(
            {"campaign_id": campaign_id},
            {"$set": {
                "status": final_status,
                "target_segments": list(generated_offers.keys()),
                "customers_analyzed": customers_analyzed,
                "eligible_customers": eligible_customers_count,
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
            "strategy": {"opportunity": {"title": "Dynamic AI Strategy", "description": "Strategy generated natively from customer data analysis."}}
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

class ExecuteCampaignRequest(BaseModel):
    merchant_id: str

class ExecuteCampaignResponse(BaseModel):
    execution_id: str
    campaign_id: str
    status: str
    total_offers_sent: int
    executed_at: str

@app.post("/campaigns/{campaign_id}/execute", response_model=ExecuteCampaignResponse)
def execute_campaign(campaign_id: str, request: ExecuteCampaignRequest):
    """Executes a campaign, generating unique coupon codes and marking offers as SENT."""
    try:
        # Check if already executed
        existing_execution = campaign_executions_collection.find_one({
            "campaign_id": campaign_id,
            "merchant_id": request.merchant_id
        })
        
        if existing_execution:
            raise HTTPException(status_code=400, detail="Campaign has already been executed")
            
        campaign = campaigns_collection.find_one({"campaign_id": campaign_id, "merchant_id": request.merchant_id})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
            
        # Get all offers for this campaign
        offers = list(offers_collection.find({"campaign_id": campaign_id, "merchant_id": request.merchant_id}))
        
        if not offers:
            raise HTTPException(status_code=400, detail="No offers found for this campaign to execute")
            
        total_sent = 0
        execution_id = str(uuid.uuid4())
        
        for offer in offers:
            coupon_code = f"OFFER-{uuid.uuid4().hex[:8].upper()}"
            
            offers_collection.update_one(
                {"_id": offer["_id"]},
                {
                    "$set": {
                        "status": "SENT",
                        "coupon_code": coupon_code,
                        "sent_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            total_sent += 1
            
        # --- DEMO SIMULATION LOGIC ---
        import random
        import hashlib
        
        # Use a deterministic seed based on the campaign_id so the demo results are stable
        # Using md5 to get an integer seed
        seed_val = int(hashlib.md5(campaign_id.encode('utf-8')).hexdigest(), 16)
        random.seed(seed_val)
        
        for offer in offers:
            # Deterministically convert ~15% of offers
            if random.random() < 0.15:
                orders_collection.insert_one({
                    "order_id": str(uuid.uuid4()),
                    "offer_id": offer["offer_id"],
                    "customer_id": offer.get("customer_id"),
                    "merchant_id": request.merchant_id,
                    "campaign_id": campaign_id,
                    "payment_status": "PAYMENT_VERIFIED",
                    # Generate realistic revenue in paise (e.g. 1500 to 5000 INR)
                    "amount": random.randint(1500, 5000) * 100, 
                    "razorpay_order_id": f"order_{uuid.uuid4().hex[:14]}",
                    "razorpay_payment_id": f"pay_{uuid.uuid4().hex[:14]}",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
        # -----------------------------

        # Create execution record
        execution_doc = {
            "execution_id": execution_id,
            "campaign_id": campaign_id,
            "merchant_id": request.merchant_id,
            "total_offers_sent": total_sent,
            "status": "COMPLETED",
            "executed_at": datetime.now(timezone.utc).isoformat()
        }
        campaign_executions_collection.insert_one(execution_doc)
        
        # Update campaign status
        campaigns_collection.update_one(
            {"campaign_id": campaign_id},
            {"$set": {"status": "EXECUTED"}}
        )
        
        return {
            "execution_id": execution_id,
            "campaign_id": campaign_id,
            "status": "COMPLETED",
            "total_offers_sent": total_sent,
            "executed_at": execution_doc["executed_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error executing campaign: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/campaigns/{campaign_id}/execution")
def get_campaign_execution(campaign_id: str, merchant_id: str = Query(...)):
    """Gets the execution status and stats of a campaign."""
    execution = campaign_executions_collection.find_one(
        {"campaign_id": campaign_id, "merchant_id": merchant_id},
        {"_id": 0}
    )
    
    if not execution:
        return {"executed": False}
        
    execution["executed"] = True
    return execution

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

import math
import re

@app.get("/customers")
def get_customers(
    merchant_id: str = Query(...),
    segment: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Paginated customer list with merchant isolation, segment filter, and total metadata."""
    query = {"merchant_id": merchant_id}
    
    if segment and segment.lower() != "all":
        query["segment"] = segment
        
    if search and search.strip():
        safe_search = re.escape(search.strip())
        query["$or"] = [
            {"id": {"$regex": safe_search, "$options": "i"}},
            {"name": {"$regex": safe_search, "$options": "i"}},
            {"email": {"$regex": safe_search, "$options": "i"}}
        ]
        
    total_count = customers_collection.count_documents(query)
    total_pages = max(1, math.ceil(total_count / limit)) if total_count > 0 else 1
    
    cursor = customers_collection.find(query, {"_id": 0}).skip((page - 1) * limit).limit(limit)
    customers = list(cursor)
    
    # Ensure segment is populated on all items
    from segmentation import segment_customer
    for c in customers:
        if not c.get("segment"):
            c["segment"] = segment_customer(c)
            
    # Aggregated segment breakdown across all customers for this merchant
    try:
        segment_pipeline = [
            {"$match": {"merchant_id": merchant_id}},
            {"$group": {"_id": "$segment", "count": {"$sum": 1}}}
        ]
        segment_counts = {
            doc["_id"] or "Unknown": doc["count"]
            for doc in customers_collection.aggregate(segment_pipeline)
            if doc.get("_id")
        }
    except Exception as e:
        segment_counts = {}
            
    return {
        "items": customers,
        "customers": customers,
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "segments": segment_counts
    }

import csv
import io
import time
import codecs
from segmentation import segment_customer

@app.post("/customers/validate-csv")
async def validate_csv_endpoint(
    file: UploadFile = File(...)
):
    """Validates CSV format, auto-detects column mapping, aggregates metrics, and returns preview."""
    try:
        content = await file.read()
        from csv_processor import validate_and_preview_csv
        return validate_and_preview_csv(content, file.filename)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error validating CSV: {e}")
        raise HTTPException(status_code=400, detail=f"CSV Validation Error: {str(e)}")

@app.post("/customers/upload")
async def upload_customers(
    merchant_id: str = Depends(get_current_merchant),
    file: UploadFile = File(...),
    mode: str = Form("replace")
):
    """Parses customer/transaction CSV, computes behavioral metrics, segments customers, and imports into DB."""
    try:
        content = await file.read()
        from csv_processor import import_processed_csv
        return import_processed_csv(content, file.filename, merchant_id, mode=mode.lower().strip())
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error importing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import customer dataset: {str(e)}")

@app.post("/customers/validate-multi-csv")
async def validate_multi_csv_endpoint(
    customers_file: UploadFile = File(...),
    orders_file: UploadFile = File(...),
    order_items_file: UploadFile = File(...)
):
    """Validates 3 related CSV files (Customers, Orders, Order Items), computes relational joins, and returns preview."""
    try:
        for f in [customers_file, orders_file, order_items_file]:
            if not f.filename.lower().endswith(".csv"):
                raise HTTPException(status_code=400, detail=f"File '{f.filename}' must be a valid CSV file (.csv extension required).")
                
        cust_content = await customers_file.read()
        ord_content = await orders_file.read()
        items_content = await order_items_file.read()
        
        from csv_processor import validate_and_preview_relational_csv
        return validate_and_preview_relational_csv(
            cust_content,
            ord_content,
            items_content,
            customers_filename=customers_file.filename,
            orders_filename=orders_file.filename,
            order_items_filename=order_items_file.filename
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error validating relational CSVs: {e}")
        raise HTTPException(status_code=400, detail=f"Relational CSV Validation Error: {str(e)}")

@app.post("/customers/upload-multi")
async def upload_multi_customers(
    merchant_id: str = Depends(get_current_merchant),
    customers_file: UploadFile = File(...),
    orders_file: UploadFile = File(...),
    order_items_file: UploadFile = File(...),
    mode: str = Form("replace")
):
    """Parses and joins 3 related CSV files, calculates behavioral metrics, segments customers, and imports into DB."""
    try:
        for f in [customers_file, orders_file, order_items_file]:
            if not f.filename.lower().endswith(".csv"):
                raise HTTPException(status_code=400, detail=f"File '{f.filename}' must be a valid CSV file (.csv extension required).")

        cust_content = await customers_file.read()
        ord_content = await orders_file.read()
        items_content = await order_items_file.read()

        from csv_processor import import_processed_relational_csv
        return import_processed_relational_csv(
            cust_content,
            ord_content,
            items_content,
            merchant_id=merchant_id,
            mode=mode.lower().strip()
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error importing relational CSVs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import relational customer dataset: {str(e)}")

@app.post("/customers/demo")
def setup_demo_customers(merchant_id: str = Depends(get_current_merchant)):
    """Seeds the DB with demo data (merchant and customers) for authenticated merchant"""
    try:
        from demo import setup_demo_data
        merchant = merchants_collection.find_one({"merchant_id": merchant_id})
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")

        # If the authenticated merchant does not yet have guardrails, provide demo guardrails
        if not merchant.get("rules") or merchant.get("rules", {}).get("max_discount_percentage") is None:
            demo_rules = {
                "max_discount_percentage": 20.0,
                "min_order_value": 500.0,
                "free_shipping_allowed": True,
                "max_campaign_budget": 50000.0,
                "high_value_customer_protection": True,
                "contact_frequency_days": 7,
                "min_margin_percentage": 25.0
            }
            merchants_collection.update_one(
                {"_id": merchant["_id"]},
                {"$set": {"rules": demo_rules}}
            )

        result = setup_demo_data(merchant_id=merchant_id)
        
        # Mark onboarding as completed for this merchant
        merchants_collection.update_one(
            {"merchant_id": merchant_id},
            {"$set": {
                "onboarding_completed": True,
                "onboarding_step": "completed"
            }}
        )

        return {
            "status": "success",
            "message": "Demo data loaded successfully",
            "merchant_id": merchant_id,
            "customers_count": result.get("customers_count", 0),
            "segments_count": result.get("segments_count", 0),
            "onboarding_completed": True
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error setting up demo data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load demo data: {str(e)}")

@app.post("/customers/demo/reset")
def reset_demo_customers(merchant_id: str = Depends(get_current_merchant)):
    """Clears demo data from the DB for authenticated merchant"""
    try:
        from demo import clear_demo_data
        clear_demo_data(merchant_id=merchant_id)
        return {"status": "success", "message": "Demo data reset successfully"}
    except Exception as e:
        print(f"Error resetting demo data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset demo data: {str(e)}")

@app.get("/merchants/{merchant_id}/guardrails")
def get_merchant_guardrails(merchant_id: str):
    """Retrieve merchant-specific guardrails or sensible defaults for onboarding"""
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    default_rules = {
        "max_discount_percentage": 15.0,
        "min_order_value": 500.0,
        "free_shipping_allowed": True,
        "max_campaign_budget": 50000.0,
        "high_value_customer_protection": True,
        "contact_frequency_days": 7,
        "min_margin_percentage": 25.0
    }
    rules = merchant.get("rules") or default_rules
    return {
        "merchant_id": merchant_id,
        "rules": rules,
        "has_guardrails": bool(merchant.get("rules") and merchant.get("rules", {}).get("max_discount_percentage") is not None)
    }

@app.put("/merchants/{merchant_id}/guardrails")
def update_merchant_guardrails(merchant_id: str, request: GuardrailsRequest):
    """Validate and update merchant guardrails"""
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    rules_dict = request.model_dump() if hasattr(request, "model_dump") else request.dict()
    is_valid, err_msg = validate_merchant_guardrails(rules_dict)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)
        
    update_fields = {
        "rules": rules_dict,
        "onboarding_step": "data_setup"
    }
    if merchant.get("onboarding_completed"):
        update_fields["onboarding_step"] = "completed"
        
    merchants_collection.update_one(
        {"_id": merchant["_id"]},
        {"$set": update_fields}
    )
    return {
        "status": "success",
        "message": "Merchant guardrails saved successfully",
        "rules": rules_dict,
        "onboarding_step": update_fields["onboarding_step"]
    }

@app.get("/merchants/{merchant_id}/profile")
def get_merchant_profile(merchant_id: str):
    """Get merchant business profile"""
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    return {
        "merchant_id": merchant_id,
        "business_name": merchant.get("business_name", ""),
        "business_category": merchant.get("business_category", "E-commerce"),
        "business_description": merchant.get("business_description", ""),
        "full_name": merchant.get("full_name", ""),
        "email": merchant.get("email", "")
    }

@app.put("/merchants/{merchant_id}/profile")
def update_merchant_profile(merchant_id: str, request: BusinessProfileRequest):
    """Update merchant business profile"""
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    if not request.business_name.strip():
        raise HTTPException(status_code=400, detail="Business name is required")
        
    update_data = {
        "business_name": request.business_name.strip(),
        "business_category": request.business_category or "E-commerce",
        "business_description": request.business_description or "",
        "onboarding_step": "guardrails_setup"
    }
    if request.full_name and request.full_name.strip():
        update_data["full_name"] = request.full_name.strip()
        
    merchants_collection.update_one(
        {"_id": merchant["_id"]},
        {"$set": update_data}
    )
    return {
        "status": "success",
        "message": "Business profile updated successfully",
        "business_name": request.business_name.strip(),
        "full_name": update_data.get("full_name", merchant.get("full_name", ""))
    }

@app.post("/merchants/{merchant_id}/complete-onboarding")
def complete_onboarding(merchant_id: str):
    """Mark onboarding as completed once business info, guardrails, and customer dataset are configured"""
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    has_business_info = bool(merchant.get("business_name"))
    has_guardrails = bool(
        merchant.get("rules") and 
        merchant.get("rules", {}).get("max_discount_percentage") is not None and
        merchant.get("rules", {}).get("min_margin_percentage") is not None
    )
    customers_count = customers_collection.count_documents({"merchant_id": merchant_id})
    has_customers = customers_count > 0
    
    if not has_business_info:
        raise HTTPException(status_code=400, detail="Business information is required to complete onboarding")
    if not has_guardrails:
        raise HTTPException(status_code=400, detail="Revenue guardrails (both max discount & min margin) must be configured before completing onboarding")
    if not has_customers:
        raise HTTPException(status_code=400, detail="Customer/transaction dataset must be uploaded and processed before completing onboarding")
        
    merchants_collection.update_one(
        {"_id": merchant["_id"]},
        {"$set": {
            "onboarding_completed": True,
            "onboarding_step": "completed"
        }}
    )
    return {
        "status": "success",
        "message": "Onboarding completed successfully",
        "merchant_id": merchant_id,
        "onboarding_completed": True
    }

@app.get("/merchants/{merchant_id}/onboarding-status")
def get_onboarding_status(merchant_id: str):
    """Check if merchant has completed all onboarding steps"""
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    has_business_info = bool(merchant.get("business_name"))
    has_guardrails = bool(
        merchant.get("rules") and 
        merchant.get("rules", {}).get("max_discount_percentage") is not None and
        merchant.get("rules", {}).get("min_margin_percentage") is not None
    )
    customers_count = customers_collection.count_documents({"merchant_id": merchant_id})
    has_customers = customers_count > 0
    
    # Fully completed only if ALL required steps are satisfied
    is_completed = bool(
        (merchant.get("onboarding_completed") is True and has_business_info and has_guardrails and has_customers) or
        (has_business_info and has_guardrails and has_customers) or
        (merchant_id == "demo_merchant_001" and has_guardrails and has_customers)
    )
    
    if is_completed:
        step = "completed"
        if not merchant.get("onboarding_completed"):
            merchants_collection.update_one(
                {"_id": merchant["_id"]},
                {"$set": {"onboarding_completed": True, "onboarding_step": "completed"}}
            )
    else:
        if merchant.get("onboarding_completed"):
            merchants_collection.update_one(
                {"_id": merchant["_id"]},
                {"$set": {"onboarding_completed": False}}
            )
        step = merchant.get("onboarding_step")
        if not step or step == "welcome" or step == "business_setup":
            step = "business_setup"
        elif not has_business_info:
            step = "business_setup"
        elif not has_guardrails:
            step = "guardrails_setup"
        elif not has_customers:
            step = "data_setup"
        else:
            step = "completed"
            is_completed = True
            
    return {
        "merchant_id": merchant_id,
        "full_name": merchant.get("full_name", ""),
        "business_name": merchant.get("business_name", ""),
        "email": merchant.get("email", ""),
        "onboarding_completed": is_completed,
        "onboarding_step": step,
        "has_business_info": has_business_info,
        "has_guardrails": has_guardrails,
        "has_customers": has_customers,
        "customers_count": customers_count,
        "rules": merchant.get("rules")
    }

@app.get("/merchants/{merchant_id}/dashboard-summary")
def get_dashboard_summary(merchant_id: str):
    """Aggregate customer and business metrics for merchant dashboard."""
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    pipeline = [
        {"$match": {"merchant_id": merchant_id}},
        {
            "$group": {
                "_id": None,
                "total_customers": {"$sum": 1},
                "total_revenue": {"$sum": "$lifetime_value"},
                "total_purchases": {"$sum": "$purchase_count"},
                "avg_aov": {"$avg": "$average_order_value"}
            }
        }
    ]
    agg = list(customers_collection.aggregate(pipeline))
    if agg:
        total_customers = agg[0].get("total_customers", 0)
        total_revenue = round(agg[0].get("total_revenue", 0.0), 2)
        total_purchases = agg[0].get("total_purchases", 0)
        aov = round(total_revenue / max(1, total_purchases), 2) if total_purchases > 0 else round(agg[0].get("avg_aov", 0.0), 2)
    else:
        total_customers = 0
        total_revenue = 0.0
        total_purchases = 0
        aov = 0.0

    # Segment distribution
    segment_pipeline = [
        {"$match": {"merchant_id": merchant_id}},
        {"$group": {"_id": "$segment", "count": {"$sum": 1}}}
    ]
    segment_distribution = {
        (doc["_id"] or "regular"): doc["count"]
        for doc in customers_collection.aggregate(segment_pipeline)
    }

    return {
        "merchant_id": merchant_id,
        "business_name": merchant.get("business_name", ""),
        "total_customers": total_customers,
        "total_revenue": total_revenue,
        "total_orders": total_purchases,
        "average_order_value": aov,
        "segment_distribution": segment_distribution
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