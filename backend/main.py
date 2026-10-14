import sys
import os
import re

# Add root-level folders to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "agents"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "policy_engine"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "injection_detector"))


from detector import detect
from customer_agent import CustomerSupportAgent
from malicious_agent import MaliciousTestAgent
from policy_checker import check_permission

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from database import db, users_collection, customers_collection, requests_logs_collection
from models import SignupRequest, LoginRequest, RequestPayload
from auth import hash_password, verify_password, create_jwt_token, decode_jwt_token

app = FastAPI(title="Secure AI Agent System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Helper: Agent's request interpreter ----------
def interpret_request(request_text: str):
    text = request_text.lower()
    match = re.search(r"cust\d+", text)
    customer_id = match.group(0).upper() if match else None

    if "delete" in text:
        action = "DELETE_CUSTOMER"
    elif "ticket" in text or "create" in text:
        action = "CREATE_TICKET"
    elif "show" in text or "details" in text or "fetch" in text or "get" in text:
        action = "READ_CUSTOMER"
    else:
        action = None

    return action, customer_id


# ---------- Basic routes ----------
@app.get("/")
async def root():
    return {"message": "Backend is running!"}


@app.get("/test-db")
async def test_db():
    try:
        collections = await db.list_collection_names()
        return {"status": "connected", "collections": collections}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ---------- Auth routes ----------
@app.post("/signup")
async def signup(data: SignupRequest):
    existing_user = await users_collection.find_one({"username": data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_pw = hash_password(data.password)
    new_user = {
        "username": data.username,
        "password": hashed_pw,
        "role": data.role
    }
    result = await users_collection.insert_one(new_user)
    return {"message": "User created successfully", "user_id": str(result.inserted_id)}


@app.post("/login")
async def login(data: LoginRequest):
    user = await users_collection.find_one({"username": data.username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_jwt_token(str(user["_id"]), user["username"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": user["username"]
    }


# ---------- Core: Request -> Agent -> Gateway -> DB ----------
@app.post("/request")
async def handle_request(payload: RequestPayload, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    user_data = decode_jwt_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    role = user_data["role"]
    username = user_data["username"]

        # ---- Prompt injection check (agent se PEHLE) ----
    inj = detect(payload.request_text)

    if inj.action == "block":
        await requests_logs_collection.insert_one({
            "username": username,
            "role": role,
            "request_text": payload.request_text,
            "action": "PROMPT_INJECTION",
            "decision": "blocked",
            "reason": inj.reason,
            "injection_score": inj.risk_score,
            "severity": "high",
        })
        return {
            "decision": "blocked",
            "message": "Access Blocked",
            "reason": "Suspicious request detected. This attempt has been logged.",
        }

    # For demo: every normal request goes through Customer Support Agent
    agent = CustomerSupportAgent()

    # Step 1: Agent interprets the request
    action, customer_id = interpret_request(payload.request_text)

    if not action:
        return {"decision": "error", "message": "Agent could not understand the request."}

    agent_request = agent.create_request(action=action, resource="customer_database")

    # Step 2: Policy Engine checks permission
    decision = check_permission(agent_request["agent_name"], action)
    is_allowed = decision == "ALLOW"

    log_entry = {
        "username": username,
        "role": role,
        "agent_name": agent_request["agent_name"],
        "request_text": payload.request_text,
        "action": action,
        "customer_id": customer_id,
        "decision": "allowed" if is_allowed else "blocked",
         "injection_score": inj.risk_score,
                 "severity": "medium" if inj.action == "flag" else "none",
      }

        

    if not is_allowed:
        await requests_logs_collection.insert_one(log_entry)
        return {
            "decision": "blocked",
            "message": "Access Blocked",
            "reason": f"{agent_request['agent_name']} is not permitted to perform '{action}'.",
        }

    # Step 3: Perform actual DB action
    if action == "READ_CUSTOMER":
        customer = await customers_collection.find_one({"customer_id": customer_id})
        if not customer:
            return {"decision": "error", "message": f"Customer {customer_id} not found."}
        customer["_id"] = str(customer["_id"])
        await requests_logs_collection.insert_one(log_entry)
        return {
            "decision": "allowed",
            "message": "Access Allowed",
            "reason": f"{agent_request['agent_name']} is permitted to perform '{action}'.",
            "data": customer,
        }

    elif action == "DELETE_CUSTOMER":
        await customers_collection.delete_one({"customer_id": customer_id})
        await requests_logs_collection.insert_one(log_entry)
        return {
            "decision": "allowed",
            "message": "Customer deleted successfully.",
            "reason": f"{agent_request['agent_name']} is permitted to perform '{action}'.",
        }

    elif action == "CREATE_TICKET":
        await requests_logs_collection.insert_one(log_entry)
        return {
            "decision": "allowed",
            "message": "Support ticket created.",
            "reason": f"{agent_request['agent_name']} is permitted to perform '{action}'.",
        }

        # ---------- Admin Routes ----------

@app.get("/admin/logs")
async def get_logs(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    user_data = decode_jwt_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if user_data["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    logs = []
    cursor = requests_logs_collection.find().sort("_id", -1)  # latest first
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        logs.append(doc)

    return {"logs": logs}


@app.get("/admin/customers")
async def get_customers(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    user_data = decode_jwt_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if user_data["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    customers = []
    cursor = customers_collection.find()
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        customers.append(doc)

    return {"customers": customers}


@app.get("/admin/stats")
async def get_stats(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    user_data = decode_jwt_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if user_data["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    total_requests = await requests_logs_collection.count_documents({})
    allowed_requests = await requests_logs_collection.count_documents({"decision": "allowed"})
    blocked_requests = await requests_logs_collection.count_documents({"decision": "blocked"})

    return {
        "total_requests": total_requests,
        "allowed_requests": allowed_requests,
        "blocked_requests": blocked_requests,
    }