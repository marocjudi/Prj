from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configuration
JWT_SECRET = "your-secret-key-here-change-in-production"
JWT_ALGORITHM = "HS256"
COMMISSION_RATE = 0.10

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe initialization
stripe_api_key = os.environ['STRIPE_SECRET_KEY']
stripe_checkout = StripeCheckout(api_key=stripe_api_key)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Models
class UserType(str):
    USER = "user"
    TECHNICIAN = "technician"
    ADMIN = "admin"

class InterventionType(str):
    PHONE = "phone"
    COMPUTER = "computer"

class ServiceType(str):
    REMOTE = "remote"
    ONSITE = "onsite"

class InterventionStatus(str):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentStatus(str):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"

# User Models
class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    phone: str
    user_type: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    skills: Optional[List[str]] = []
    hourly_rate: Optional[float] = None
    available: Optional[bool] = True

class UserLogin(BaseModel):
    email: str
    password: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    phone: str
    user_type: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    skills: Optional[List[str]] = []
    hourly_rate: Optional[float] = None
    available: Optional[bool] = True
    rating: Optional[float] = 0.0
    total_interventions: Optional[int] = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Intervention Models
class InterventionCreate(BaseModel):
    title: str
    description: str
    intervention_type: str  # phone, computer
    service_type: str  # remote, onsite
    urgency: str  # low, medium, high
    budget_min: float
    budget_max: float
    user_address: Optional[str] = None
    user_latitude: Optional[float] = None
    user_longitude: Optional[float] = None

class Intervention(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    technician_id: Optional[str] = None
    title: str
    description: str
    intervention_type: str
    service_type: str
    urgency: str
    budget_min: float
    budget_max: float
    final_price: Optional[float] = None
    status: str = InterventionStatus.PENDING
    user_address: Optional[str] = None
    user_latitude: Optional[float] = None
    user_longitude: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# Payment Models
class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intervention_id: str
    user_id: str
    technician_id: Optional[str] = None
    session_id: str
    amount: float
    currency: str = "eur"
    commission_amount: float
    technician_amount: float
    payment_status: str = PaymentStatus.PENDING
    metadata: Optional[Dict[str, Any]] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentCreate(BaseModel):
    intervention_id: str

# Message Models
class MessageCreate(BaseModel):
    intervention_id: str
    content: str

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intervention_id: str
    sender_id: str
    sender_type: str  # user, technician
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, user_type: str) -> str:
    payload = {
        "user_id": user_id,
        "user_type": user_type,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        user_type = payload.get("user_type")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
        
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in km (simplified)"""
    import math
    R = 6371  # Earth's radius in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat/2) * math.sin(dLat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dLon/2) * math.sin(dLon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Authentication endpoints
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")
    
    hashed_password = hash_password(user_data.password)
    user = User(**user_data.dict(exclude={"password"}))
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    
    await db.users.insert_one(user_dict)
    token = create_token(user.id, user.user_type)
    
    return {
        "message": "Inscription réussie",
        "token": token,
        "user": user.dict()
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    token = create_token(user["id"], user["user_type"])
    user_obj = User(**user)
    
    return {
        "message": "Connexion réussie",
        "token": token,
        "user": user_obj.dict()
    }

@api_router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Technician endpoints
@api_router.get("/technicians/nearby")
async def get_nearby_technicians(
    latitude: float,
    longitude: float,
    radius: float = 20,  # km
    intervention_type: Optional[str] = None
):
    technicians = await db.users.find({
        "user_type": UserType.TECHNICIAN,
        "available": True,
        "latitude": {"$exists": True},
        "longitude": {"$exists": True}
    }).to_list(100)
    
    nearby_technicians = []
    for tech in technicians:
        if tech.get("latitude") and tech.get("longitude"):
            distance = calculate_distance(
                latitude, longitude, 
                tech["latitude"], tech["longitude"]
            )
            if distance <= radius:
                tech_obj = User(**tech)
                tech_dict = tech_obj.dict()
                tech_dict["distance"] = round(distance, 2)
                nearby_technicians.append(tech_dict)
    
    # Sort by distance
    nearby_technicians.sort(key=lambda x: x["distance"])
    return nearby_technicians

@api_router.put("/technicians/availability")
async def update_availability(
    available: bool,
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.TECHNICIAN:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"available": available}}
    )
    
    return {"message": "Disponibilité mise à jour"}

# Intervention endpoints
@api_router.post("/interventions", response_model=Intervention)
async def create_intervention(
    intervention_data: InterventionCreate,
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.USER:
        raise HTTPException(status_code=403, detail="Seuls les utilisateurs peuvent créer des demandes")
    
    intervention = Intervention(**intervention_data.dict(), user_id=current_user.id)
    await db.interventions.insert_one(intervention.dict())
    
    return intervention

@api_router.get("/interventions")
async def get_interventions(current_user: User = Depends(get_current_user)):
    if current_user.user_type == UserType.USER:
        interventions = await db.interventions.find({"user_id": current_user.id}).to_list(100)
    elif current_user.user_type == UserType.TECHNICIAN:
        # Show available interventions and assigned ones
        interventions = await db.interventions.find({
            "$or": [
                {"status": InterventionStatus.PENDING},
                {"technician_id": current_user.id}
            ]
        }).to_list(100)
    else:  # Admin
        interventions = await db.interventions.find().to_list(100)
    
    return [Intervention(**intervention) for intervention in interventions]

@api_router.put("/interventions/{intervention_id}/assign")
async def assign_intervention(
    intervention_id: str,
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.TECHNICIAN:
        raise HTTPException(status_code=403, detail="Seuls les techniciens peuvent accepter des interventions")
    
    intervention = await db.interventions.find_one({"id": intervention_id})
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention non trouvée")
    
    if intervention["status"] != InterventionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Cette intervention n'est plus disponible")
    
    await db.interventions.update_one(
        {"id": intervention_id},
        {
            "$set": {
                "technician_id": current_user.id,
                "status": InterventionStatus.ASSIGNED,
                "assigned_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Intervention acceptée avec succès"}

@api_router.put("/interventions/{intervention_id}/status")
async def update_intervention_status(
    intervention_id: str,
    new_status: str,
    final_price: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    intervention = await db.interventions.find_one({"id": intervention_id})
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention non trouvée")
    
    # Check permissions
    if current_user.user_type == UserType.USER and intervention["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    elif current_user.user_type == UserType.TECHNICIAN and intervention["technician_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    update_data = {"status": new_status}
    if new_status == InterventionStatus.COMPLETED:
        update_data["completed_at"] = datetime.utcnow()
        if final_price:
            update_data["final_price"] = final_price
    
    await db.interventions.update_one(
        {"id": intervention_id},
        {"$set": update_data}
    )
    
    return {"message": "Statut mis à jour"}

# Payment endpoints
@api_router.post("/payments/checkout/session")
async def create_checkout_session(
    payment_data: PaymentCreate,
    origin_url: str,
    current_user: User = Depends(get_current_user)
):
    # Get intervention details
    intervention = await db.interventions.find_one({"id": payment_data.intervention_id})
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention non trouvée")
    
    if intervention["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    if not intervention.get("final_price"):
        raise HTTPException(status_code=400, detail="Prix final non défini")
    
    amount = float(intervention["final_price"])
    commission_amount = amount * COMMISSION_RATE
    technician_amount = amount - commission_amount
    
    # Create success and cancel URLs
    success_url = f"{origin_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/interventions"
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=amount,
        currency="eur",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "intervention_id": payment_data.intervention_id,
            "user_id": current_user.id,
            "technician_id": intervention["technician_id"],
            "commission_rate": str(COMMISSION_RATE)
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    payment_transaction = PaymentTransaction(
        intervention_id=payment_data.intervention_id,
        user_id=current_user.id,
        technician_id=intervention["technician_id"],
        session_id=session.session_id,
        amount=amount,
        commission_amount=commission_amount,
        technician_amount=technician_amount,
        metadata=checkout_request.metadata
    )
    
    await db.payment_transactions.insert_one(payment_transaction.dict())
    
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/payments/checkout/status/{session_id}")
async def get_checkout_status(session_id: str):
    checkout_status = await stripe_checkout.get_checkout_status(session_id)
    
    # Update payment transaction
    payment_transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if payment_transaction:
        update_data = {
            "payment_status": checkout_status.payment_status,
            "updated_at": datetime.utcnow()
        }
        
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": update_data}
        )
        
        # If payment successful, mark intervention as paid
        if checkout_status.payment_status == "paid":
            await db.interventions.update_one(
                {"id": payment_transaction["intervention_id"]},
                {"$set": {"status": InterventionStatus.COMPLETED}}
            )
    
    return checkout_status

# Message endpoints
@api_router.post("/messages")
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    # Verify user has access to this intervention
    intervention = await db.interventions.find_one({"id": message_data.intervention_id})
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention non trouvée")
    
    if (intervention["user_id"] != current_user.id and 
        intervention.get("technician_id") != current_user.id):
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    message = Message(
        **message_data.dict(),
        sender_id=current_user.id,
        sender_type=current_user.user_type
    )
    
    await db.messages.insert_one(message.dict())
    return message

@api_router.get("/messages/{intervention_id}")
async def get_messages(
    intervention_id: str,
    current_user: User = Depends(get_current_user)
):
    # Verify access
    intervention = await db.interventions.find_one({"id": intervention_id})
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention non trouvée")
    
    if (intervention["user_id"] != current_user.id and 
        intervention.get("technician_id") != current_user.id):
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    messages = await db.messages.find({"intervention_id": intervention_id}).sort("created_at", 1).to_list(100)
    return [Message(**message) for message in messages]

# Admin endpoints
@api_router.get("/admin/dashboard")
async def admin_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    # Get key metrics
    total_users = await db.users.count_documents({"user_type": "user"})
    total_technicians = await db.users.count_documents({"user_type": "technician"}) 
    total_interventions = await db.interventions.count_documents({})
    completed_interventions = await db.interventions.count_documents({"status": "completed"})
    pending_interventions = await db.interventions.count_documents({"status": "pending"})
    
    # Revenue calculation
    completed_payments = await db.payment_transactions.find({"payment_status": "paid"}).to_list(1000)
    total_revenue = sum(payment.get("commission_amount", 0) for payment in completed_payments)
    
    # Average rating calculation
    avg_rating_pipeline = [
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}}
    ]
    avg_rating_result = await db.users.aggregate(avg_rating_pipeline).to_list(1)
    avg_rating = avg_rating_result[0]["avg_rating"] if avg_rating_result else 0
    
    return {
        "total_users": total_users,
        "total_technicians": total_technicians,
        "total_interventions": total_interventions,
        "completed_interventions": completed_interventions,
        "pending_interventions": pending_interventions,
        "completion_rate": round((completed_interventions / total_interventions * 100) if total_interventions > 0 else 0, 2),
        "total_revenue": round(total_revenue, 2),
        "average_rating": round(avg_rating, 2)
    }

@api_router.get("/admin/users")
async def admin_get_users(
    skip: int = 0,
    limit: int = 50,
    user_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    query = {}
    if user_type:
        query["user_type"] = user_type
    
    users = await db.users.find(query).skip(skip).limit(limit).to_list(limit)
    # Remove passwords from response
    for user in users:
        user.pop("password", None)
    
    return users

@api_router.get("/admin/interventions")
async def admin_get_interventions(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    query = {}
    if status:
        query["status"] = status
    
    interventions = await db.interventions.find(query).skip(skip).limit(limit).to_list(limit)
    return [Intervention(**intervention) for intervention in interventions]

@api_router.get("/admin/payments")
async def admin_get_payments(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    payments = await db.payment_transactions.find({}).skip(skip).limit(limit).to_list(limit)
    return [PaymentTransaction(**payment) for payment in payments]

@api_router.put("/admin/users/{user_id}/status")
async def admin_update_user_status(
    user_id: str,
    active: bool,
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"active": active}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    return {"message": "Statut utilisateur mis à jour"}

@api_router.post("/admin/interventions/{intervention_id}/resolve")
async def admin_resolve_intervention(
    intervention_id: str,
    resolution: str,
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    result = await db.interventions.update_one(
        {"id": intervention_id},
        {
            "$set": {
                "status": "resolved_by_admin",
                "admin_resolution": resolution,
                "resolved_at": datetime.utcnow(),
                "resolved_by": current_user.id
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Intervention non trouvée")
    
    return {"message": "Intervention résolue par l'administrateur"}

# Notification endpoints
class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    type: str  # info, success, warning, error
    data: Optional[Dict[str, Any]] = {}

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    message: str
    type: str
    data: Optional[Dict[str, Any]] = {}
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

@api_router.post("/notifications")
async def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(get_current_user)
):
    # Only admin or system can create notifications for other users
    if current_user.user_type != UserType.ADMIN and notification_data.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    notification = Notification(**notification_data.dict())
    await db.notifications.insert_one(notification.dict())
    return notification

@api_router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    query = {"user_id": current_user.id}
    if unread_only:
        query["read"] = False
    
    notifications = await db.notifications.find(query).sort("created_at", -1).limit(50).to_list(50)
    return [Notification(**notification) for notification in notifications]

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"read": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification non trouvée")
    
    return {"message": "Notification marquée comme lue"}

@api_router.post("/notifications/send-push")
async def send_push_notification(
    user_id: str,
    title: str,
    message: str,
    current_user: User = Depends(get_current_user)
):
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    # Create notification in database
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type="info"
    )
    await db.notifications.insert_one(notification.dict())
    
    # TODO: Integrate with push notification service (Firebase, OneSignal, etc.)
    # For now, just store in database
    
    return {"message": "Notification push envoyée"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()