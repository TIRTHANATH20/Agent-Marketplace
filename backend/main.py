import time
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from uuid import uuid4
import sqlite3
import os
import re
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# 1. CONFIGURATION & SETUP
# ============================================

app = FastAPI(title="Agent Marketplace API")


def parse_allowed_origins() -> List[str]:
    """Resolve allowed CORS origins from env, defaulting to local development hosts."""
    configured = os.getenv("ALLOWED_ORIGINS", "").strip()
    if configured:
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
        if origins:
            return origins
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

SENSITIVE_FIELDS = {
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "jwt",
    "password",
    "secret",
    "access_key",
    "license_key",
}


def redact_sensitive(value):
    """Recursively redact secret-bearing fields before logs are persisted."""
    if isinstance(value, dict):
        redacted = {}
        for k, v in value.items():
            key_lower = str(k).lower()
            if key_lower in SENSITIVE_FIELDS or "token" in key_lower or "auth" in key_lower or "password" in key_lower:
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_sensitive(v)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(v) for v in value]
    if isinstance(value, str):
        # Redact bearer headers and JWT-like values embedded in free-form strings.
        masked = re.sub(r"Bearer\s+[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+", "Bearer [REDACTED]", value)
        masked = re.sub(r"\b[A-Za-z0-9\-_=]{10,}\.[A-Za-z0-9\-_=]{10,}\.[A-Za-z0-9\-_=]{10,}\b", "[REDACTED_JWT]", masked)
        return masked
    return value


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Apply baseline security headers and prevent token transport through query params."""
    sensitive_qs_keys = {"token", "access_token", "jwt", "authorization", "auth"}
    if any(k.lower() in sensitive_qs_keys for k in request.query_params.keys()):
        return Response(content="Sensitive credentials must not be sent in URL query parameters.", status_code=400)

    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq LLM Setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None
    logging.getLogger(__name__).warning("GROQ_API_KEY not set. Agent responses are disabled until LLM is configured.")

# Security Config
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
if SECRET_KEY == "your-secret-key-change-in-production":
    logging.getLogger(__name__).warning("Using default SECRET_KEY. Set SECRET_KEY environment variable for production.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
PURCHASE_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

# Password Hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('marketplace.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global logs store
logs_store: List[Dict] = []
MAX_LOGS = 1000

# Demo usage tracking: {username: {agent_id: usage_count}}
demo_usage_tracker: Dict[str, Dict[str, int]] = {}
MAX_DEMO_USES = 10

# Persistent memory store for per-user, per-agent conversation history
MEMORY_DB_PATH = os.path.join(os.path.dirname(__file__), "agent_memory.db")

# ============================================
# 2. DATABASE MODELS (In-Memory for MVP)
# ============================================

class Agent(BaseModel):
    id: str
    name: str
    description: str
    purpose: str
    status: str = "active"
    version: str = "1.0"
    capabilities: List[str]
    mcp_server_ids: List[str] = []  # Bundled MCP tools
    
class User(BaseModel):
    username: str
    email: str
    password: str = None

class UserInDB(User):
    hashed_password: str

# ============================================
# 3. AUTHENTICATION SYSTEM
# ============================================

# Sample users (in production, use a real database)
fake_users_db = {
    "admin": {
        "username": "admin",
        "email": "admin@marketplace.com",
        "hashed_password": pwd_context.hash("admin123"),
        "purchased_agents": {},
        "purchased_mcp_servers": {},  # {mcp_server_id: {purchase_date, license_key}}
        "active_session_id": None,
        "session_access_token": None,
        "purchase_access_tokens": {}
    },
    "user1": {
        "username": "user1",
        "email": "user1@marketplace.com",
        "hashed_password": pwd_context.hash("user123"),
        "purchased_agents": {},
        "purchased_mcp_servers": {},  # {mcp_server_id: {purchase_date, license_key}}
        "active_session_id": None,
        "session_access_token": None,
        "purchase_access_tokens": {}
    }
}

class Token(BaseModel):
    access_token: str
    token_type: str
    user: str

class LoginRequest(BaseModel):
    username: str
    password: str

class QuestionRequest(BaseModel):
    question: str
    include_reasoning: bool = False

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _decode_token_payload(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _is_token_still_valid(token: str, username: str, expected_session_id: Optional[str] = None) -> bool:
    """Return True if token is valid JWT and belongs to username/session."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return False

    if payload.get("sub") != username:
        return False
    if expected_session_id and payload.get("sid") != expected_session_id:
        return False
    return True


def _ensure_active_session_id(username: str) -> str:
    user = fake_users_db.get(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    session_id = user.get("active_session_id")
    if not session_id:
        session_id = str(uuid4())
        user["active_session_id"] = session_id
    return session_id


def _get_or_create_session_access_token(username: str) -> str:
    """Reuse token during active session; mint new one only when no active session token exists."""
    user = fake_users_db.get(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    session_id = _ensure_active_session_id(username)
    existing_token = user.get("session_access_token")
    if existing_token and _is_token_still_valid(existing_token, username, session_id):
        return existing_token

    access_token = create_access_token(
        data={"sub": username, "typ": "session", "sid": session_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    user["session_access_token"] = access_token
    return access_token

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=15)
    # Issue token with unique claims; session stability is managed by reuse in login flow.
    to_encode.update({"exp": expire, "iat": now, "jti": str(uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_purchase_access_token(username: str, agent_id: str) -> str:
    """Create/reuse purchase token scoped to one agent for the active user session."""
    user = fake_users_db.get(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    session_id = _ensure_active_session_id(username)
    per_session = user.setdefault("purchase_access_tokens", {}).setdefault(session_id, {})
    existing_token = per_session.get(agent_id)
    if existing_token and _is_token_still_valid(existing_token, username, session_id):
        return existing_token

    token = create_access_token(
        data={"sub": username, "agent_id": agent_id, "typ": "purchase_access", "sid": session_id},
        expires_delta=timedelta(minutes=PURCHASE_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    per_session[agent_id] = token
    return token

def verify_token(token: str) -> str:
    payload = _decode_token_payload(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = fake_users_db.get(username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    active_session_id = user.get("active_session_id")
    token_session_id = payload.get("sid")
    if not active_session_id or token_session_id != active_session_id:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")

    return username

async def get_current_user(credentials = Depends(security)) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_token(credentials.credentials)


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return token


def resolve_purchased_agent_user(http_request: Request, agent_id: str) -> str:
    """Resolve authenticated user for purchased endpoint from session JWT or purchase access token."""
    token = _extract_bearer_token(http_request)
    payload = _decode_token_payload(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_record = fake_users_db.get(username)
    if user_record is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    active_session_id = user_record.get("active_session_id")
    token_session_id = payload.get("sid")
    if not active_session_id or token_session_id != active_session_id:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")

    token_type = payload.get("typ", "session")
    if token_type == "purchase_access":
        token_agent_id = payload.get("agent_id")
        if token_agent_id != agent_id:
            raise HTTPException(status_code=403, detail="Token is not valid for this agent")

    has_purchased = user_record and agent_id in user_record.get("purchased_agents", {})
    if not has_purchased:
        raise HTTPException(status_code=403, detail="You do not own this agent. Purchase it first.")

    return username

# ============================================
# 4. AGENT-TO-AGENT COMMUNICATION & STORAGE
# ============================================

agents_db: Dict[str, Agent] = {
    "agent-001": Agent(
        id="agent-001",
        name="Data Analyst",
        description="Finds KPIs, trends, and notable changes across catalog and business activity",
        purpose="Deliver concise analytics insights with clear takeaways for decision making",
        capabilities=["kpi-analysis", "trend-detection", "executive-summaries", "anomaly-highlights"],
        status="active",
        mcp_server_ids=["mcp-004", "mcp-006"]  # Database Query, Code Analysis
    ),
    "agent-002": Agent(
        id="agent-002",
        name="Database Helper",
        description="Answers data questions with database-first, fact-only responses",
        purpose="Provide exact data retrieval and SQL-style query interpretation",
        capabilities=["sql-interpretation", "fact-retrieval", "schema-aware-answers", "result-validation"],
        status="active",
        mcp_server_ids=["mcp-004", "mcp-005"]  # Database Query, API Client
    ),
    "agent-003": Agent(
        id="agent-003",
        name="Report Writer",
        description="Produces formal reports with structure, sections, and action summaries",
        purpose="Turn business data into readable reports for stakeholders",
        capabilities=["report-structuring", "narrative-summaries", "action-items", "stakeholder-formatting"],
        status="active",
        mcp_server_ids=["mcp-001", "mcp-006"]  # Filesystem Tools, Code Analysis
    ),
    "agent-004": Agent(
        id="agent-004",
        name="Customer Analyst",
        description="Explains customer segments, behavior patterns, and retention opportunities",
        purpose="Help teams understand customer value, cohorts, and lifecycle patterns",
        capabilities=["customer-segmentation", "cohort-analysis", "ltv-insights", "retention-recommendations"],
        status="active",
        mcp_server_ids=["mcp-004", "mcp-003"]  # Database Query, Web Search & Browsing
    ),
    "agent-005": Agent(
        id="agent-005",
        name="Sales Analyst",
        description="Tracks sales performance, top products, and revenue movement",
        purpose="Identify what drives sales and where commercial performance is improving or weakening",
        capabilities=["revenue-analysis", "product-performance", "sales-trend-breakdown", "commercial-insights"],
        status="active",
        mcp_server_ids=["mcp-004", "mcp-005"]  # Database Query, API Client
    ),
    "agent-006": Agent(
        id="agent-006",
        name="Pricing Expert",
        description="Designs pricing and discount recommendations with clear tradeoffs",
        purpose="Balance conversion and margin using practical pricing strategy",
        capabilities=["pricing-strategy", "discount-planning", "margin-protection", "what-if-scenarios"],
        status="active",
        mcp_server_ids=["mcp-004", "mcp-006"]  # Database Query, Code Analysis
    )
}

class AgentMessage(BaseModel):
    message_id: str = None
    from_agent: str
    to_agent: str
    payload: Dict
    timestamp: str = None

class MCPServer(BaseModel):
    id: str
    name: str
    description: str
    category: str
    tools: List[str]
    status: str = "active"
    price: float = 0.0

# MCP Servers Database
mcp_servers_db: Dict[str, MCPServer] = {
    "mcp-001": MCPServer(
        id="mcp-001",
        name="Filesystem Tools",
        description="Read, write, and manage files on the system",
        category="file-operations",
        tools=["read_file", "write_file", "list_directory", "delete_file", "move_file"],
        status="active",
        price=0.0
    ),
    "mcp-002": MCPServer(
        id="mcp-002",
        name="Git Integration",
        description="Git operations including commit, push, pull, and branch management",
        category="version-control",
        tools=["git_commit", "git_push", "git_pull", "create_branch", "merge_branch", "view_diff"],
        status="active",
        price=0.0
    ),
    "mcp-003": MCPServer(
        id="mcp-003",
        name="Web Search & Browsing",
        description="Search the web and fetch website content",
        category="web-tools",
        tools=["search", "fetch_url", "get_page_content", "extract_links"],
        status="active",
        price=0.0
    ),
    "mcp-004": MCPServer(
        id="mcp-004",
        name="Database Query",
        description="Execute SQL queries and manage database connections",
        category="database",
        tools=["execute_query", "fetch_data", "insert_record", "update_record", "create_table"],
        status="active",
        price=0.0
    ),
    "mcp-005": MCPServer(
        id="mcp-005",
        name="API Client",
        description="Make HTTP requests to external APIs with authentication support",
        category="api-integration",
        tools=["get_request", "post_request", "put_request", "delete_request", "set_headers"],
        status="active",
        price=0.0
    ),
    "mcp-006": MCPServer(
        id="mcp-006",
        name="Code Analysis",
        description="Analyze, parse, and generate code snippets",
        category="code-tools",
        tools=["parse_code", "analyze_syntax", "generate_code", "lint_code", "format_code"],
        status="active",
        price=0.0
    )
}

class A2ACommunication:
    """Agent-to-Agent Communication Handler"""
    
    def __init__(self):
        self.message_queue: List[AgentMessage] = []
        self.message_history: List[Dict] = []
    
    def send_message(self, from_agent: str, to_agent: str, payload: Dict) -> Dict:
        """Send message from one agent to another"""
        message_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        message = AgentMessage(
            message_id=message_id,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload,
            timestamp=timestamp
        )
        
        self.message_queue.append(message)
        self.message_history.append(message.dict())
        
        log_event(f"A2A_MESSAGE", {
            "message_id": message_id,
            "from": from_agent,
            "to": to_agent,
            "payload": payload
        })
        
        return {
            "status": "delivered",
            "message_id": message_id,
            "timestamp": timestamp
        }
    
    def get_messages(self, agent_id: str) -> List[Dict]:
        """Get messages for a specific agent"""
        return [
            msg.dict() for msg in self.message_queue 
            if msg.to_agent == agent_id
        ]
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get message history"""
        return self.message_history[-limit:]

a2a_comm = A2ACommunication()

# ============================================
# 5. LOGGING SYSTEM
# ============================================

class LogEntry(BaseModel):
    timestamp: str
    level: str
    event_type: str
    user: Optional[str] = None
    details: Dict

def log_event(event_type: str, details: Dict, level: str = "INFO", user: str = None):
    """Log an event to both file and in-memory store"""
    safe_details = redact_sensitive(details or {})
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event_type": event_type,
        "user": user,
        "details": safe_details
    }
    
    logs_store.append(log_entry)
    if len(logs_store) > MAX_LOGS:
        logs_store.pop(0)
    
    logger.info(f"{event_type} | {json.dumps(safe_details)}")


def init_memory_db():
    """Initialize SQLite table used for per-user, per-agent conversation memory."""
    conn = sqlite3.connect(MEMORY_DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_agent_memory_user_agent_time
            ON agent_memory(username, agent_id, created_at)
            """
        )
        conn.commit()
    finally:
        conn.close()


def append_agent_memory(username: str, agent_id: str, role: str, content: str):
    """Store a single conversation turn in persistent memory."""
    if role not in {"user", "assistant"}:
        return
    text = (content or "").strip()
    if not text:
        return

    # Keep rows bounded so context assembly remains predictable.
    trimmed = text[:4000]
    conn = sqlite3.connect(MEMORY_DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agent_memory (username, agent_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, agent_id, role, trimmed, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_agent_memory(username: str, agent_id: str, limit: int = 8) -> List[Dict]:
    """Fetch recent conversation turns for one user-agent pair in chronological order."""
    safe_limit = max(1, min(limit, 50))
    conn = sqlite3.connect(MEMORY_DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT role, content, created_at
            FROM agent_memory
            WHERE username = ? AND agent_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (username, agent_id, safe_limit)
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    rows.reverse()
    return [
        {"role": role, "content": content, "created_at": created_at}
        for role, content, created_at in rows
    ]


def clear_agent_memory(username: str, agent_id: str) -> int:
    """Delete all saved conversation memory for one user-agent pair."""
    conn = sqlite3.connect(MEMORY_DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM agent_memory WHERE username = ? AND agent_id = ?",
            (username, agent_id)
        )
        deleted = cur.rowcount or 0
        conn.commit()
        return deleted
    finally:
        conn.close()


init_memory_db()

def get_groq_response(
    agent_name: str,
    agent_purpose: str,
    user_question: str,
    agent_context: str = "",
    include_reasoning: bool = False,
) -> str:
    """Generate response using Groq LLM"""
    if not groq_client:
        raise RuntimeError("LLM backend is not configured. Set GROQ_API_KEY to enable agent responses.")
    
    try:
        reasoning_policy = (
            "- User explicitly requested reasoning.\n"
            "- REQUIRED OUTPUT FORMAT:\n"
            "  Final Answer: <concise result>\n"
            "  Methodology: <how the answer was derived>\n"
            "  Rationale: <why this recommendation/answer is appropriate>\n"
            "- Keep these sections concise and practical.\n"
            "- Include SQL/query text only if it is directly useful for this answer."
            if include_reasoning
            else "- Return only final conclusions/recommendations; do not reveal intermediate reasoning, thought process, or analysis steps.\n"
             "- Do not explain how you arrived at the answer unless the user explicitly asks for methodology.\n"
             "- Do not include SQL queries unless the user explicitly asks for SQL/query text."
        )

        system_prompt = f"""You are {agent_name}, an AI agent in an Agent Marketplace system.
Your purpose: {agent_purpose}

STRICT RESPONSE POLICY:
- Be direct, precise, and professional.
- Stay within your role and provided context.
- Do not invent facts, numbers, or sources.
- If information is missing, say exactly what is missing.
- Provide actionable output with clear structure.
- Do not include filler, hype, or unnecessary preamble.
- Do not use markdown formatting symbols such as **, __, ##, or ```.
- Return plain text only.
    - Keep responses concise by default; prefer short direct answers over long walkthroughs.
{reasoning_policy}
"""
        
        user_prompt = f"{agent_context}\n\nUser Question: {user_question}" if agent_context else f"User Question: {user_question}"
        
        message = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.1-8b-instant",
            max_tokens=500,
            temperature=0.7
        )
        
        return message.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API error: {str(e)}")
        raise RuntimeError(f"LLM request failed: {str(e)}")

def find_chinook_db_path() -> Optional[str]:
    """Locate Chinook.db if present in known runtime locations."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "Chinook.db"),
        os.path.join(os.getcwd(), "backend", "Chinook.db"),
        "Chinook.db"
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

def get_agent_style_instructions(agent_id: str) -> str:
    """Return role-specific formatting/behavior directives for each agent."""
    style_map = {
        "agent-001": (
            "You are a KPI-focused analyst. Prioritize trends, deltas, and anomalies. "
            "Output format: Snapshot, Trend Direction, Risk Flag, Next Decision. "
            "Do not provide long explanations."
        ),
        "agent-002": (
            "You are a database helper. Prioritize exact values, entity names, and counts. "
            "Output format: Direct Answer, Evidence Rows, Missing Inputs. "
            "Keep language factual and terse."
        ),
        "agent-003": (
            "You are a report writer for stakeholders. "
            "Output format: Executive Summary, Evidence, Recommendation, Assumptions. "
            "Use formal tone and complete sentences."
        ),
        "agent-004": (
            "You are a customer analyst. Focus on segment behavior and lifecycle insights. "
            "Output format: Segment Insight, Behavior Pattern, Retention Move. "
            "Tie every recommendation to customer impact."
        ),
        "agent-005": (
            "You are a sales analyst. Focus on revenue movement and product performance. "
            "Output format: Sales Outcome, Key Drivers, Commercial Action. "
            "Quantify impact whenever possible."
        ),
        "agent-006": (
            "You are a pricing expert. Focus on margin, conversion tradeoffs, and testing. "
            "Output format: Pricing Move, Tradeoff, Guardrail, Test Plan. "
            "Explicitly state downside risk."
        ),
    }
    return style_map.get(agent_id, "Output format: concise, structured, and actionable.")


def clean_agent_response(text: str) -> str:
    """Normalize model output to plain text and remove markdown emphasis markers."""
    if not text:
        return ""

    cleaned = text.replace("**", "")
    cleaned = cleaned.replace("__", "")
    cleaned = cleaned.replace("```", "")

    # Remove common leaked reasoning section headers when present.
    lines = cleaned.splitlines()
    filtered = []
    skip_prefixes = (
        "thought process:",
        "reasoning:",
        "analysis:",
        "chain of thought:",
    )
    for line in lines:
        if line.strip().lower().startswith(skip_prefixes):
            continue
        filtered.append(line)
    cleaned = "\n".join(filtered)

    # Drop standalone markdown language hints if they leak through.
    cleaned = re.sub(r"(?im)^\s*(sql|python|javascript|json)\s*$", "", cleaned)
    return cleaned.strip()


def enforce_final_output_only(user_question: str, response_text: str) -> str:
    """Remove chain-of-thought style prose and SQL blocks unless explicitly requested."""
    if not response_text:
        return ""

    q = (user_question or "").lower()
    wants_sql = any(k in q for k in ["sql", "query", "select ", "database query", "show query"])

    filtered = response_text

    # Remove explicit reasoning/process phrases.
    filtered = re.sub(
        r"(?im)^\s*(based on (the )?provided .*?|this query will .*?|here('s| is) (the )?analysis:?|reasoning:?|thought process:?|step-by-step:?|let'?s think.*?)\s*$",
        "",
        filtered,
    )

    if not wants_sql:
        # Remove inline/backticked SQL snippets.
        filtered = re.sub(r"`\s*select\b[\s\S]*?;\s*`", "", filtered, flags=re.IGNORECASE)
        # Remove common SQL multi-line statements even if not fenced.
        filtered = re.sub(
            r"(?is)\bselect\b[\s\S]*?\bfrom\b[\s\S]*?(?:;|$)",
            "",
            filtered,
        )
        # Remove leftover references to query text.
        filtered = re.sub(r"(?im)^\s*this query will.*$", "", filtered)

    # Collapse excessive blank lines created by filtering.
    filtered = re.sub(r"\n{3,}", "\n\n", filtered).strip()
    return filtered or response_text


def enforce_detailed_output(response_text: str) -> str:
    """Ensure reasoning mode always returns a visibly detailed, structured format."""
    text = (response_text or "").strip()
    if not text:
        return "Final Answer: No response generated.\nMethodology: No methodology available.\nRationale: No rationale available."

    lower = text.lower()
    has_final = "final answer:" in lower
    has_method = "methodology:" in lower
    has_rationale = "rationale:" in lower

    if has_final and has_method and has_rationale:
        return text

    return (
        f"Final Answer: {text}\n"
        "Methodology: Reasoning mode requested. The answer is based on agent context, available memory, and role constraints.\n"
        "Rationale: Detailed mode is enabled to provide a concise explanation of how and why this answer was produced."
    )

def build_agent_context(agent: Agent, agent_id: str, user_question: str, username: str) -> str:
    """Build grounding context for LLM while keeping final answer generation fully LLM-based."""
    user_record = fake_users_db.get(username) or {}
    owned_mcp_servers = set((user_record.get("purchased_mcp_servers") or {}).keys())

    context_parts = [
        f"Agent ID: {agent_id}",
        f"Agent Name: {agent.name}",
        f"Purpose: {agent.purpose}",
        f"Capabilities: {', '.join(agent.capabilities)}",
        f"MCP Server IDs: {', '.join(agent.mcp_server_ids) if agent.mcp_server_ids else 'None'}",
        f"Role-specific directives: {get_agent_style_instructions(agent_id)}",
    ]

    if agent.mcp_server_ids:
        context_parts.append("MCP tool knowledge:")
        for sid in agent.mcp_server_ids:
            srv = mcp_servers_db.get(sid)
            if not srv:
                continue
            ownership = "owned" if sid in owned_mcp_servers else "not-owned"
            context_parts.append(
                f"- {sid}: {srv.name} ({ownership}) | category={srv.category} | tools={', '.join(srv.tools)}"
            )

    recent_turns = get_recent_agent_memory(username, agent_id, limit=8)
    if recent_turns:
        context_parts.append("Conversation memory:")
        for turn in recent_turns:
            speaker = "User" if turn["role"] == "user" else agent.name
            snippet = turn["content"].replace("\n", " ").strip()[:500]
            context_parts.append(f"- {speaker}: {snippet}")

    db_path = find_chinook_db_path()
    if not db_path:
        context_parts.append("Database context: Chinook.db not found in expected runtime locations.")
        return "\n".join(context_parts)

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM Track;")
        total_tracks = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Artist;")
        total_artists = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Genre;")
        total_genres = cur.fetchone()[0]
        cur.execute("SELECT SUM(Total) FROM Invoice;")
        total_revenue = cur.fetchone()[0] or 0
        conn.close()

        context_parts.extend([
            "Database context: Chinook.db available.",
            f"Chinook summary: tracks={total_tracks}, artists={total_artists}, genres={total_genres}, revenue={total_revenue:.2f}",
            "Instruction: Use this context when relevant. If a requested metric is not provided in context, explicitly say so instead of guessing."
        ])
    except Exception as e:
        context_parts.append(f"Database context error: {str(e)[:100]}")

    return "\n".join(context_parts)


def get_missing_mcp_servers(agent_id: str, username: str) -> List[str]:
    """Return MCP server IDs required by an agent but not owned by the user."""
    agent = agents_db[agent_id]
    required = set(agent.mcp_server_ids or [])
    if not required:
        return []

    user_record = fake_users_db.get(username) or {}
    owned = set((user_record.get("purchased_mcp_servers") or {}).keys())
    return sorted(required - owned)


def auto_provision_required_free_mcp_servers(agent_id: str, username: str) -> List[str]:
    """Auto-install required free MCP servers for smoother first-run agent usage."""
    user_record = fake_users_db.get(username)
    if not user_record:
        return []

    installed: List[str] = []
    purchased = user_record.setdefault("purchased_mcp_servers", {})

    for server_id in agents_db[agent_id].mcp_server_ids or []:
        server = mcp_servers_db.get(server_id)
        if not server:
            continue
        if server_id in purchased:
            continue
        if server.price > 0:
            continue

        purchased[server_id] = {
            "license_key": str(uuid4()),
            "purchased_at": datetime.now(timezone.utc).isoformat(),
            "auto_provisioned": True,
            "source_agent_id": agent_id,
        }
        installed.append(server_id)

    if installed:
        log_event(
            "MCP_AUTO_PROVISIONED",
            {"agent_id": agent_id, "installed_mcp_servers": installed, "user": username},
            user=username,
        )

    return installed


def enforce_mcp_access(agent_id: str, username: str):
    """Block execution when the user does not own MCP tools required by the agent."""
    auto_provision_required_free_mcp_servers(agent_id, username)
    missing = get_missing_mcp_servers(agent_id, username)
    if not missing:
        return

    missing_labels = [
        f"{sid} ({mcp_servers_db[sid].name})" if sid in mcp_servers_db else sid
        for sid in missing
    ]
    log_event(
        "MCP_ACCESS_DENIED",
        {"agent_id": agent_id, "missing_mcp_servers": missing, "user": username},
        level="WARN",
        user=username,
    )
    raise HTTPException(
        status_code=403,
        detail=(
            "Missing required MCP tools for this agent. "
            f"Please install: {', '.join(missing_labels)}"
        ),
    )


def answer_memory_lookup(agent_id: str, question: str, username: str) -> Optional[str]:
    """Resolve explicit memory questions directly from saved conversation turns."""
    q = (question or "").strip().lower()
    if not q:
        return None

    ask_prev_question = any(
        phrase in q
        for phrase in ["previous question", "last question", "what did i ask", "my earlier question"]
    )
    ask_prev_answer = any(
        phrase in q
        for phrase in ["previous answer", "last answer", "what did you answer", "your earlier response"]
    )

    if not ask_prev_question and not ask_prev_answer:
        return None

    turns = get_recent_agent_memory(username, agent_id, limit=40)
    if not turns:
        return "No saved conversation memory found yet for this agent."

    if ask_prev_question:
        user_turns = [t["content"].strip() for t in turns if t.get("role") == "user" and t.get("content")]
        if user_turns:
            return f"Your previous question was: {user_turns[-1]}"
        return "I do not have a previous user question in saved memory yet."

    assistant_turns = [t["content"].strip() for t in turns if t.get("role") == "assistant" and t.get("content")]
    if assistant_turns:
        return f"My previous answer was: {assistant_turns[-1]}"
    return "I do not have a previous assistant answer in saved memory yet."


def generate_agent_answer(agent_id: str, question: str, username: str, include_reasoning: bool = False) -> Dict:
    """Generate a strict LLM answer payload for a specific agent and user."""
    agent = agents_db[agent_id]
    response_text = answer_memory_lookup(agent_id, question, username)

    if response_text is None:
        context = build_agent_context(agent, agent_id, question, username)

        try:
            response_text = get_groq_response(
                agent.name,
                agent.purpose,
                question,
                context,
                include_reasoning=include_reasoning,
            )
        except RuntimeError as e:
            log_event("LLM_RESPONSE_ERROR", {
                "agent_id": agent_id,
                "error": str(e)[:200]
            }, level="ERROR", user=username)
            raise HTTPException(status_code=503, detail=str(e))

    # Always normalize and enforce response mode, including memory-hit responses.
    response_text = clean_agent_response(response_text)
    if include_reasoning:
        response_text = enforce_detailed_output(response_text)
    else:
        response_text = enforce_final_output_only(question, response_text)

    log_event("AGENT_QUESTION", {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "question": question[:100],
        "user": username
    }, user=username)

    append_agent_memory(username, agent_id, "user", question)
    append_agent_memory(username, agent_id, "assistant", response_text)

    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "question": question,
        "response": response_text,
        "include_reasoning": include_reasoning,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============================================
# 6. API ENDPOINTS
# ============================================

# AUTH ENDPOINTS
@app.post("/auth/login", response_model=Token)
async def login(login_request: LoginRequest):
    """Authenticate user and return JWT token"""
    user = fake_users_db.get(login_request.username)
    if not user or not verify_password(login_request.password, user["hashed_password"]):
        log_event("AUTH_FAILED", {"username": login_request.username}, level="WARN")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = _get_or_create_session_access_token(login_request.username)
    
    log_event("AUTH_SUCCESS", {"username": login_request.username}, user=login_request.username)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": login_request.username
    }


@app.post("/auth/logout")
async def logout(current_user: str = Depends(get_current_user)):
    """Invalidate the active session so next login gets a new token."""
    user = fake_users_db.get(current_user)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    old_session_id = user.get("active_session_id")
    if old_session_id:
        user.get("purchase_access_tokens", {}).pop(old_session_id, None)

    user["active_session_id"] = None
    user["session_access_token"] = None

    log_event("LOGOUT", {"username": current_user}, user=current_user)
    return {"message": "Logged out successfully"}

@app.post("/auth/register", response_model=Token)
async def register(user: LoginRequest):
    """Register a new user"""
    if user.username in fake_users_db:
        log_event("REGISTER_FAILED", {"username": user.username, "reason": "User exists"}, level="WARN")
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_password = get_password_hash(user.password)
    fake_users_db[user.username] = {
        "username": user.username,
        "email": f"{user.username}@marketplace.com",
        "hashed_password": hashed_password,
        "purchased_agents": {},
        "purchased_mcp_servers": {},
        "active_session_id": None,
        "session_access_token": None,
        "purchase_access_tokens": {}
    }
    
    access_token = _get_or_create_session_access_token(user.username)
    
    log_event("USER_REGISTERED", {"username": user.username}, user=user.username)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.username
    }


# PURCHASE ENDPOINTS
@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(
    agent_id: str, 
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Simulate purchasing an agent. Grants the user access to the agent's endpoint."""
    if agent_id not in agents_db:
        log_event("AGENT_NOT_FOUND", {"agent_id": agent_id}, level="WARN", user=current_user)
        raise HTTPException(status_code=404, detail="Agent not found")

    user = fake_users_db.get(current_user)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    # Keep purchase record internal; clients use JWT on purchased_api_url.
    access_key = str(uuid4())
    purchase_record = {
        "access_key": access_key,
        "purchased_at": datetime.now(timezone.utc).isoformat()
    }

    user.setdefault("purchased_agents", {})[agent_id] = purchase_record

    log_event("AGENT_PURCHASED", {"agent_id": agent_id, "user": current_user}, user=current_user)

    # Build full URL based on request
    agent_endpoint_path = f"/agents/{agent_id}/ask"
    purchased_api_path = f"/agents/{agent_id}/purchased-ask"
    # Get base URL from request
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    full_url = f"{base_url}{agent_endpoint_path}"
    full_api_url = f"{base_url}{purchased_api_path}"
    purchase_access_token = create_purchase_access_token(current_user, agent_id)

    return {
        "message": "Purchase successful",
        "agent_id": agent_id,
        "agent_name": agents_db[agent_id].name,
        "agent_endpoint": agent_endpoint_path,
        "url": full_url,
        "purchased_api_endpoint": purchased_api_path,
        "purchased_api_url": full_api_url,
        "purchase_access_token": purchase_access_token,
        "purchased_at": purchase_record["purchased_at"],
        "usage_instructions": {
            "method": "POST",
            "url": full_api_url,
            "headers": {
                "Authorization": "Bearer <PURCHASE_ACCESS_TOKEN>",
                "Content-Type": "application/json"
            },
            "body": {
                "question": "Your question here"
            },
            "example_curl": f"curl -X POST {full_api_url} -H 'Authorization: Bearer <PURCHASE_ACCESS_TOKEN>' -H 'Content-Type: application/json' -d '{{\"question\":\"How many jazz tracks?\"}}'",
            "example_javascript": f"fetch('{full_api_url}', {{ method: 'POST', headers: {{ 'Authorization': 'Bearer <PURCHASE_ACCESS_TOKEN>', 'Content-Type': 'application/json' }}, body: JSON.stringify({{ question: 'Your question here' }}) }}).then(r => r.json()).then(d => console.log(d))"
        }
    }


@app.get("/users/me/purchases")
async def get_my_purchases(request: Request, current_user: str = Depends(get_current_user)):
    user = fake_users_db.get(current_user)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    purchases = user.get("purchased_agents", {})
    # Enrich with agent name and endpoint
    result = {}
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    for aid, rec in purchases.items():
        agent = agents_db.get(aid)
        full_endpoint = f"{base_url}/agents/{aid}/ask"
        purchased_api_url = f"{base_url}/agents/{aid}/purchased-ask"
        result[aid] = {
            "agent_name": agent.name if agent else aid,
            "agent_endpoint": f"/agents/{aid}/ask",
            "url": full_endpoint,
            "purchased_api_endpoint": f"/agents/{aid}/purchased-ask",
            "purchased_api_url": purchased_api_url,
            "purchased_at": rec.get("purchased_at"),
            "usage_instructions": {
                "method": "POST",
                "url": purchased_api_url,
                "headers": {
                    "Authorization": "Bearer <JWT_TOKEN>",
                    "Content-Type": "application/json"
                },
                "body": {
                    "question": "Your question here"
                },
                "example_curl": f"curl -X POST {repr(purchased_api_url)} -H 'Authorization: Bearer <JWT_TOKEN>' -H 'Content-Type: application/json' -d '{{\"question\":\"How many jazz tracks?\"}}'",
                "example_javascript": "fetch(API_URL, { method: 'POST', headers: { 'Authorization': 'Bearer TOKEN', 'Content-Type': 'application/json' }, body: JSON.stringify({ question: 'Your question here' }) }).then(r => r.json()).then(d => console.log(d))"
            }
        }

    return {"user": current_user, "purchases": result}

# USER AGENT ACCESS STATUS
@app.get("/agents/my-access-status")
async def get_my_agent_access(current_user: str = Depends(get_current_user)):
    """Get access status for all agents (purchased or demo tries left)"""
    user = fake_users_db.get(current_user)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    access_status = {}
    user_purchases = user.get("purchased_agents", {})
    user_demo_usage = demo_usage_tracker.get(current_user, {})
    
    for agent_id, agent in agents_db.items():
        # Keep free MCP dependencies in sync before computing availability.
        auto_provision_required_free_mcp_servers(agent_id, current_user)

        is_purchased = agent_id in user_purchases
        demo_uses_left = MAX_DEMO_USES - user_demo_usage.get(agent_id, 0)
        missing_mcp = get_missing_mcp_servers(agent_id, current_user)
        mcp_ready = len(missing_mcp) == 0
        
        access_status[agent_id] = {
            "agent_name": agent.name,
            "is_purchased": is_purchased,
            "demo_uses_left": demo_uses_left if not is_purchased else None,
            "missing_mcp_servers": missing_mcp,
            "mcp_ready": mcp_ready,
            "can_use": (is_purchased or demo_uses_left > 0) and mcp_ready
        }
    
    return access_status

# AGENT MARKETPLACE ENDPOINTS
@app.get("/agents", response_model=List[Agent])
async def get_agents(current_user: str = Depends(get_current_user)):
    """Get list of all available agents"""
    log_event("AGENTS_FETCHED", {"count": len(agents_db)}, user=current_user)
    return list(agents_db.values())

@app.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, current_user: str = Depends(get_current_user)):
    """Get details of a specific agent"""
    if agent_id not in agents_db:
        log_event("AGENT_NOT_FOUND", {"agent_id": agent_id}, level="WARN", user=current_user)
        raise HTTPException(status_code=404, detail="Agent not found")
    
    log_event("AGENT_DETAILS_FETCHED", {"agent_id": agent_id}, user=current_user)
    return agents_db[agent_id]

# MCP SERVERS MARKETPLACE ENDPOINTS
@app.get("/mcp-servers", response_model=List[MCPServer])
async def get_mcp_servers(current_user: str = Depends(get_current_user)):
    """Get list of all available MCP servers"""
    log_event("MCP_SERVERS_FETCHED", {"count": len(mcp_servers_db)}, user=current_user)
    return list(mcp_servers_db.values())

@app.get("/mcp-servers/{server_id}", response_model=MCPServer)
async def get_mcp_server(server_id: str, current_user: str = Depends(get_current_user)):
    """Get details of a specific MCP server"""
    if server_id not in mcp_servers_db:
        log_event("MCP_SERVER_NOT_FOUND", {"server_id": server_id}, level="WARN", user=current_user)
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    log_event("MCP_SERVER_DETAILS_FETCHED", {"server_id": server_id}, user=current_user)
    return mcp_servers_db[server_id]

@app.post("/mcp-servers/{server_id}/purchase")
async def purchase_mcp_server(
    server_id: str,
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Purchase/install an MCP server tool"""
    if server_id not in mcp_servers_db:
        log_event("MCP_SERVER_NOT_FOUND", {"server_id": server_id}, level="WARN", user=current_user)
        raise HTTPException(status_code=404, detail="MCP server not found")

    user = fake_users_db.get(current_user)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    # Create a simple license record
    license_key = str(uuid4())
    purchase_record = {
        "license_key": license_key,
        "purchased_at": datetime.now(timezone.utc).isoformat()
    }

    user.setdefault("purchased_mcp_servers", {})[server_id] = purchase_record

    log_event("MCP_SERVER_PURCHASED", {"server_id": server_id, "user": current_user}, user=current_user)

    mcp_server = mcp_servers_db[server_id]

    return {
        "message": "Installation successful",
        "server_id": server_id,
        "server_name": mcp_server.name,
        "license_key": license_key,
        "purchased_at": purchase_record["purchased_at"],
        "tools": mcp_server.tools,
        "agents_using_this": [
            agents_db[aid].name for aid in agents_db 
            if server_id in agents_db[aid].mcp_server_ids
        ]
    }

@app.get("/users/me/mcp-purchases")
async def get_my_mcp_purchases(current_user: str = Depends(get_current_user)):
    """Get list of purchased MCP servers for current user"""
    user = fake_users_db.get(current_user)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    purchases = user.get("purchased_mcp_servers", {})
    result = {}

    for server_id, rec in purchases.items():
        server = mcp_servers_db.get(server_id)
        if server:
            result[server_id] = {
                "server_name": server.name,
                "tools": server.tools,
                "license_key": rec.get("license_key"),
                "purchased_at": rec.get("purchased_at"),
                "agents_using_this": [
                    agents_db[aid].name for aid in agents_db 
                    if server_id in agents_db[aid].mcp_server_ids
                ]
            }

    return {
        "user": current_user, 
        "purchased_mcp_servers": list(purchases.keys()),  # Return just the IDs as array
        "details": result  # Detailed info if needed
    }

# Example queries for each agent
AGENT_EXAMPLE_QUERIES = {
    "agent-001": [
        "What are the top-performing data sources this quarter?",
        "Show me the trend analysis for Q1 2026",
        "Which metrics have shown the most growth?"
    ],
    "agent-002": [
        "Fetch all customer orders from the last 30 days",
        "Get the list of top 10 customers by revenue",
        "Retrieve all tracks sold in the Rock genre"
    ],
    "agent-003": [
        "Generate a monthly sales report for March 2026",
        "Create a customer acquisition summary",
        "Export the year-end financial report"
    ],
    "agent-004": [
        "Which customers have the highest lifetime value?",
        "Segment customers by purchase frequency",
        "What are the preferences of our top spenders?",
        "Analyze customer demographics and buying patterns"
    ],
    "agent-005": [
        "What are the top 10 best-selling tracks?",
        "Which artists generate the most revenue?",
        "What are the trending genres this month?",
        "Analyze sales trends by music genre"
    ]
}

@app.get("/agents/{agent_id}/access-details")
async def get_access_details(
    agent_id: str, 
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Get JWT-based access details for a purchased agent."""
    if agent_id not in agents_db:
        log_event("AGENT_NOT_FOUND", {"agent_id": agent_id}, level="WARN", user=current_user)
        raise HTTPException(status_code=404, detail="Agent not found")
    
    user = fake_users_db.get(current_user)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Check if user has purchased this agent
    purchases = user.get("purchased_agents", {})
    if agent_id not in purchases:
        log_event("UNAUTHORIZED_ACCESS", {"agent_id": agent_id}, level="WARN", user=current_user)
        raise HTTPException(status_code=403, detail="You do not own this agent. Purchase it first.")
    
    # Keep purchase data internal; only expose JWT-based usage info.
    purchase_record = purchases[agent_id]
    
    # Build the access URL
    agent_endpoint_path = f"/agents/{agent_id}/ask"
    purchased_api_path = f"/agents/{agent_id}/purchased-ask"
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    full_url = f"{base_url}{agent_endpoint_path}"
    full_api_url = f"{base_url}{purchased_api_path}"
    purchase_access_token = create_purchase_access_token(current_user, agent_id)
    
    log_event("ACCESS_DETAILS_FETCHED", {"agent_id": agent_id}, user=current_user)
    
    return {
        "agent_id": agent_id,
        "agent_name": agents_db[agent_id].name,
        "url": full_url,
        "purchased_api_url": full_api_url,
        "purchase_access_token": purchase_access_token,
        "instructions": "Use purchase token as bearer token.",
        "purchased_at": purchase_record.get("purchased_at")
    }

# AGENT COMMUNICATION ENDPOINTS
@app.post("/agents/send-message")
async def send_agent_message(
    message: AgentMessage,
    current_user: str = Depends(get_current_user)
):
    """Send message from one agent to another"""
    if message.from_agent not in agents_db or message.to_agent not in agents_db:
        log_event(
            "INVALID_AGENT_MESSAGE",
            {"from": message.from_agent, "to": message.to_agent},
            level="ERROR",
            user=current_user
        )
        raise HTTPException(status_code=400, detail="Invalid agent IDs")
    
    result = a2a_comm.send_message(
        message.from_agent,
        message.to_agent,
        message.payload
    )
    
    return result

@app.post("/agents/communicate")
async def communicate_agents(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Alternative endpoint for agent-to-agent communication (from frontend)"""
    try:
        data = await request.json()
        from_agent_id = data.get("from_agent_id")
        to_agent_id = data.get("to_agent_id")
        payload = data.get("payload", "")
        
        if not from_agent_id or not to_agent_id:
            raise HTTPException(status_code=400, detail="Missing from_agent_id or to_agent_id")
        
        if from_agent_id not in agents_db or to_agent_id not in agents_db:
            raise HTTPException(status_code=404, detail="Invalid agent IDs")
        
        result = a2a_comm.send_message(from_agent_id, to_agent_id, {"message": payload})
        
        log_event("A2A_COMMUNICATION", {
            "from": from_agent_id,
            "to": to_agent_id,
            "payload_length": len(str(payload))
        }, user=current_user)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log_event("A2A_COMMUNICATION_ERROR", {"error": str(e)[:200]}, level="WARN", user=current_user)
        raise HTTPException(status_code=400, detail="Invalid communication payload")

@app.get("/agents/{agent_id}/messages")
async def get_agent_messages(
    agent_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get messages for a specific agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    messages = a2a_comm.get_messages(agent_id)
    log_event("MESSAGES_FETCHED", {"agent_id": agent_id, "count": len(messages)}, user=current_user)
    return messages

@app.get("/agents/communication/history")
async def get_communication_history(
    limit: int = 50,
    current_user: str = Depends(get_current_user)
):
    """Get agent communication history"""
    history = a2a_comm.get_history(limit)
    log_event("HISTORY_FETCHED", {"limit": limit}, user=current_user)
    return history


@app.get("/agents/{agent_id}/memory")
async def get_agent_memory(
    agent_id: str,
    limit: int = 20,
    current_user: str = Depends(get_current_user)
):
    """Get saved conversation memory for the current user and selected agent."""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    memory = get_recent_agent_memory(current_user, agent_id, limit=limit)
    return {
        "user": current_user,
        "agent_id": agent_id,
        "agent_name": agents_db[agent_id].name,
        "memory": memory
    }


@app.delete("/agents/{agent_id}/memory")
async def delete_agent_memory(
    agent_id: str,
    current_user: str = Depends(get_current_user)
):
    """Clear saved conversation memory for the current user and selected agent."""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    deleted = clear_agent_memory(current_user, agent_id)
    log_event(
        "AGENT_MEMORY_CLEARED",
        {"agent_id": agent_id, "deleted_rows": deleted},
        user=current_user,
    )
    return {
        "message": "Memory cleared",
        "user": current_user,
        "agent_id": agent_id,
        "deleted_rows": deleted
    }

# AGENT QUESTION ENDPOINT
@app.post("/agents/{agent_id}/ask")
async def ask_agent(
    agent_id: str,
    request: QuestionRequest,
    current_user: str = Depends(get_current_user)
):
    """Marketplace ask endpoint: only for non-purchased demo usage."""
    if agent_id not in agents_db:
        log_event("AGENT_NOT_FOUND", {"agent_id": agent_id}, level="WARN", user=current_user)
        raise HTTPException(status_code=404, detail="Agent not found")

    actual_user = current_user

    # Access control: Check if user purchased this agent
    user_record = fake_users_db.get(actual_user)
    has_purchased = user_record and agent_id in user_record.get("purchased_agents", {})

    if has_purchased:
        raise HTTPException(
            status_code=403,
            detail=(
                "Purchased agents are accessible only through the dedicated agent URL using JWT token. "
                "Fetch /agents/{agent_id}/access-details and call purchased_api_url."
            )
        )

    enforce_mcp_access(agent_id, actual_user)
    
    # Non-purchased agents consume demo attempts for every user, including admin.
    if not has_purchased:
        # Track demo usage for non-purchased agents
        if actual_user not in demo_usage_tracker:
            demo_usage_tracker[actual_user] = {}
        
        current_usage = demo_usage_tracker[actual_user].get(agent_id, 0)
        
        if current_usage >= MAX_DEMO_USES:
            log_event(
                "DEMO_LIMIT_EXCEEDED",
                {"agent_id": agent_id, "usage_count": current_usage},
                level="WARN",
                user=actual_user
            )
            raise HTTPException(
                status_code=402,
                detail=f"Demo limit reached ({MAX_DEMO_USES} free tries). Please purchase this agent for unlimited access."
            )
        
        # Increment demo usage counter
        demo_usage_tracker[actual_user][agent_id] = current_usage + 1
        log_event(
            "DEMO_USAGE",
            {"agent_id": agent_id, "usage_count": current_usage + 1, "max": MAX_DEMO_USES},
            user=actual_user
        )

    q_text = request.question
    payload = generate_agent_answer(
        agent_id,
        q_text,
        actual_user,
        include_reasoning=request.include_reasoning,
    )
    
    # Calculate demo usage info for response
    demo_uses_left = MAX_DEMO_USES - demo_usage_tracker.get(actual_user, {}).get(agent_id, 0)
    
    return {
        **payload,
        "is_purchased": has_purchased,
        "demo_uses_left": demo_uses_left,
        "usage_count": demo_usage_tracker.get(actual_user, {}).get(agent_id, 0),
        "max_demo_uses": MAX_DEMO_USES
    }


@app.post("/agents/{agent_id}/purchased-ask")
async def ask_purchased_agent(
    agent_id: str,
    request: QuestionRequest,
    http_request: Request,
):
    """Dedicated purchased-agent endpoint requiring ownership and bearer auth."""
    if agent_id not in agents_db:
        log_event("AGENT_NOT_FOUND", {"agent_id": agent_id}, level="WARN")
        raise HTTPException(status_code=404, detail="Agent not found")

    current_user = resolve_purchased_agent_user(http_request, agent_id)

    enforce_mcp_access(agent_id, current_user)

    payload = generate_agent_answer(
        agent_id,
        request.question,
        current_user,
        include_reasoning=request.include_reasoning,
    )
    return {
        **payload,
        "is_purchased": True,
        "demo_uses_left": None,
        "usage_count": None,
        "max_demo_uses": None
    }

# AGENT ACCESS HELPER ENDPOINT
@app.get("/agents/{agent_id}/ask", response_class=HTMLResponse)
async def get_agent_endpoint_info(agent_id: str, request: Request):
    """Interactive query interface for the agent."""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agents_db[agent_id]
    
    # Build domain-specific example questions
    if agent_id == "agent-001":  # Data Analyzer
        example_questions_html = """
        <div class="space-y-4">
            <div>
                <h4 class="font-semibold text-blue-700 mb-2">📊 Business Analytics</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('What are the top genres?')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ What are the top genres?
                    </button>
                    <button onclick="fillQuestion('Who are the top artists?')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ Who are the top artists?
                    </button>
                    <button onclick="fillQuestion('Most popular music trends')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ Most popular music trends
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-green-700 mb-2">💰 Customer Insights</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('Top customers by spending?')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ Top customers by spending?
                    </button>
                    <button onclick="fillQuestion('Customer spending analysis')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ Customer spending analysis
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-purple-700 mb-2">📈 Statistics</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('Database statistics')" class="w-full text-left px-4 py-2 hover:bg-purple-50 rounded border border-purple-200 hover:border-purple-300 transition text-sm">
                        ❓ Database statistics
                    </button>
                    <button onclick="fillQuestion('Catalog overview')" class="w-full text-left px-4 py-2 hover:bg-purple-50 rounded border border-purple-200 hover:border-purple-300 transition text-sm">
                        ❓ Catalog overview
                    </button>
                </div>
            </div>
        </div>
        """
    elif agent_id == "agent-002":  # Query Executive
        example_questions_html = """
        <div class="space-y-4">
            <div>
                <h4 class="font-semibold text-blue-700 mb-2">📊 Track Queries</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('How many rock tracks?')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ How many rock tracks?
                    </button>
                    <button onclick="fillQuestion('How many jazz tracks?')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ How many jazz tracks?
                    </button>
                    <button onclick="fillQuestion('How many metal tracks?')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ How many metal tracks?
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-green-700 mb-2">🎵 Genre Queries</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('What genres are available?')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ What genres are available?
                    </button>
                    <button onclick="fillQuestion('List all genres')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ List all genres
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-purple-700 mb-2">📈 Total Counts</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('How many total tracks?')" class="w-full text-left px-4 py-2 hover:bg-purple-50 rounded border border-purple-200 hover:border-purple-300 transition text-sm">
                        ❓ How many total tracks?
                    </button>
                </div>
            </div>
        </div>
        """
    elif agent_id == "agent-003":  # Report Generator
        example_questions_html = """
        <div class="space-y-4">
            <div>
                <h4 class="font-semibold text-blue-700 mb-2">🎵 Catalog Reports</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('Music catalog report')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ Music catalog report
                    </button>
                    <button onclick="fillQuestion('Catalog composition analysis')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ Catalog composition analysis
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-green-700 mb-2">💰 Financial Reports</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('Sales revenue report')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ Sales revenue report
                    </button>
                    <button onclick="fillQuestion('Revenue analysis')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ Revenue analysis
                    </button>
                    <button onclick="fillQuestion('Invoice summary')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ Invoice summary
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-purple-700 mb-2">👥 HR & Staff Reports</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('Employee staff report')" class="w-full text-left px-4 py-2 hover:bg-purple-50 rounded border border-purple-200 hover:border-purple-300 transition text-sm">
                        ❓ Employee staff report
                    </button>
                    <button onclick="fillQuestion('Sales team information')" class="w-full text-left px-4 py-2 hover:bg-purple-50 rounded border border-purple-200 hover:border-purple-300 transition text-sm">
                        ❓ Sales team information
                    </button>
                </div>
            </div>
        </div>
        """
    elif agent_id == "agent-004":  # Customer Insights Agent
        example_questions_html = """
        <div class="space-y-4">
            <div>
                <h4 class="font-semibold text-blue-700 mb-2">💰 Customer Lifetime Value</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('Which customers have the highest lifetime value?')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ Which customers have the highest lifetime value?
                    </button>
                    <button onclick="fillQuestion('Top spending customers analysis')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ Top spending customers analysis
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-green-700 mb-2">📊 Customer Segmentation</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('Segment customers by purchase frequency')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ Segment customers by purchase frequency
                    </button>
                    <button onclick="fillQuestion('Customer behavior segments')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ Customer behavior segments
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-purple-700 mb-2">🎯 Preferences & Demographics</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('What are the preferences of our top spenders?')" class="w-full text-left px-4 py-2 hover:bg-purple-50 rounded border border-purple-200 hover:border-purple-300 transition text-sm">
                        ❓ What are the preferences of our top spenders?
                    </button>
                    <button onclick="fillQuestion('Analyze customer demographics and buying patterns')" class="w-full text-left px-4 py-2 hover:bg-purple-50 rounded border border-purple-200 hover:border-purple-300 transition text-sm">
                        ❓ Analyze customer demographics and buying patterns
                    </button>
                </div>
            </div>
        </div>
        """
    elif agent_id == "agent-005":  # Music Sales Optimizer
        example_questions_html = """
        <div class="space-y-4">
            <div>
                <h4 class="font-semibold text-blue-700 mb-2">🎵 Track Performance</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('What are the top 10 best-selling tracks?')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ What are the top 10 best-selling tracks?
                    </button>
                    <button onclick="fillQuestion('Top performing music tracks analysis')" class="w-full text-left px-4 py-2 hover:bg-blue-50 rounded border border-blue-200 hover:border-blue-300 transition text-sm">
                        ❓ Top performing music tracks analysis
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-green-700 mb-2">💵 Revenue Optimization</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('Which artists generate the most revenue?')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ Which artists generate the most revenue?
                    </button>
                    <button onclick="fillQuestion('Revenue by artist and genre')" class="w-full text-left px-4 py-2 hover:bg-green-50 rounded border border-green-200 hover:border-green-300 transition text-sm">
                        ❓ Revenue by artist and genre
                    </button>
                </div>
            </div>
            <div>
                <h4 class="font-semibold text-purple-700 mb-2">📈 Trends & Forecasts</h4>
                <div class="space-y-2">
                    <button onclick="fillQuestion('What are the trending genres this month?')" class="w-full text-left px-4 py-2 hover:bg-purple-50 rounded border border-purple-200 hover:border-purple-300 transition text-sm">
                        ❓ What are the trending genres this month?
                    </button>
                    <button onclick="fillQuestion('Analyze sales trends by music genre')" class="w-full text-left px-4 py-2 hover:bg-purple-50 rounded border border-purple-200 hover:border-purple-300 transition text-sm">
                        ❓ Analyze sales trends by music genre
                    </button>
                </div>
            </div>
        </div>
        """
    else:
        example_questions_html = "<p class='text-gray-600'>No examples available</p>"

    # Normalize legacy emoji/prefix-heavy examples to match marketplace UI tone.
    example_questions_html = (
        example_questions_html
        .replace("❓ ", "")
        .replace("📊 ", "")
        .replace("💰 ", "")
        .replace("📈 ", "")
        .replace("🎵 ", "")
        .replace("👥 ", "")
        .replace("🎯 ", "")
        .replace("💵 ", "")
    )
    
    requested_theme = request.query_params.get("theme", "").strip().lower()
    initial_theme = "dark" if requested_theme == "dark" else "light"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{agent.name} - Query Agent</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

            :root {{
                --bg: #f8f6ef;
                --ink: #1f2933;
                --ink-soft: #4b5d6b;
                --brand: #d95d39;
                --mint: #2b8a78;
                --paper: #fffef9;
                --line: #e5e1d5;
                --shadow: 0 10px 30px rgba(31, 41, 51, 0.12);
            }}

            body[data-theme='dark'] {{
                --bg: #10161d;
                --ink: #e4edf5;
                --ink-soft: #a7bac9;
                --brand: #ff8454;
                --mint: #44b9a1;
                --paper: #19212b;
                --line: #2e3c4b;
                --shadow: 0 14px 32px rgba(0, 0, 0, 0.38);
            }}

            * {{ box-sizing: border-box; }}

            body {{
                margin: 0;
                font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                color: var(--ink);
                                background: linear-gradient(180deg, color-mix(in srgb, var(--paper) 86%, var(--bg) 14%) 0%, var(--bg) 100%);
                min-height: 100vh;
                transition: background 0.25s ease, color 0.25s ease;
            }}

            .endpoint-shell {{
                width: min(960px, 100%);
                margin: 0 auto;
                padding: 1.2rem;
            }}

            .endpoint-card {{
                border: 1px solid var(--line);
                border-radius: 16px;
                background: var(--paper);
                box-shadow: 0 8px 20px rgba(31, 41, 51, 0.08);
                padding: 1rem;
                margin-bottom: 0.9rem;
            }}

            body[data-theme='dark'] .endpoint-card {{
                box-shadow: none;
            }}

            .title {{
                font-family: 'Fraunces', Georgia, serif;
                margin: 0 0 0.4rem 0;
                font-size: 2rem;
                color: var(--ink);
            }}

            .subtitle {{
                margin: 0.2rem 0 0.9rem 0;
                color: var(--ink-soft);
            }}

            .pill {{
                display: inline-block;
                border: 1px solid color-mix(in srgb, var(--mint) 40%, var(--line) 60%);
                border-radius: 999px;
                padding: 0.24rem 0.7rem;
                font-size: 0.78rem;
                color: color-mix(in srgb, var(--mint) 80%, var(--ink) 20%);
                background: color-mix(in srgb, var(--paper) 80%, var(--mint) 20%);
            }}

            .section-title {{
                margin: 0 0 0.5rem 0;
                font-size: 1.1rem;
                font-weight: 800;
            }}

            .space-y-4 {{
                display: grid;
                gap: 0.75rem;
            }}

            .space-y-4 > div {{
                border: 1px solid var(--line);
                border-radius: 12px;
                padding: 0.72rem;
                background: color-mix(in srgb, var(--paper) 94%, transparent 6%);
            }}

            .space-y-4 h4 {{
                margin: 0 0 0.48rem 0;
                font-size: 0.8rem;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: var(--ink-soft);
                font-weight: 700;
            }}

            .font-semibold {{ font-weight: 700; }}
            .mb-2 {{ margin-bottom: 0.48rem; }}
            .text-blue-700,
            .text-green-700,
            .text-purple-700 {{ color: var(--ink-soft); }}

            label {{
                display: block;
                font-size: 0.82rem;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                color: var(--ink-soft);
                margin-bottom: 0.35rem;
                font-weight: 700;
            }}

            input, textarea {{
                width: 100%;
                border: 1px solid var(--line);
                border-radius: 12px;
                background: color-mix(in srgb, var(--paper) 92%, transparent);
                color: var(--ink);
                font-family: inherit;
                font-size: 0.95rem;
                padding: 0.72rem;
            }}

            textarea {{
                min-height: 120px;
                resize: vertical;
            }}

            .token-row {{
                display: flex;
                gap: 0.5rem;
                align-items: center;
            }}

            .token-row input {{
                flex: 1;
                min-width: 0;
            }}

            .token-toggle-btn {{
                min-height: 42px;
                border: 1px solid var(--line);
                border-radius: 10px;
                background: color-mix(in srgb, var(--paper) 88%, transparent 12%);
                color: var(--ink);
                font-weight: 700;
                padding: 0.5rem 0.8rem;
                cursor: pointer;
                white-space: nowrap;
            }}

            .token-toggle-btn:hover {{
                background: color-mix(in srgb, var(--paper) 78%, var(--mint) 22%);
                border-color: color-mix(in srgb, var(--mint) 48%, var(--line) 52%);
            }}

            .ask-btn {{
                width: 100%;
                min-height: 50px;
                margin-top: 0.65rem;
                border: none;
                border-radius: 12px;
                background: linear-gradient(120deg, var(--brand), #ef7d4f);
                color: white;
                font-size: 1rem;
                font-weight: 800;
                cursor: pointer;
                box-shadow: 0 9px 18px rgba(217, 93, 57, 0.28);
                display: inline-flex;
                align-items: center;
                justify-content: center;
                line-height: 1.2;
            }}

            .helper {{
                margin-top: 0.45rem;
                font-size: 0.8rem;
                color: var(--ink-soft);
            }}

            .reasoning-toggle {{
                margin-top: 0.6rem;
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                font-size: 0.86rem;
                color: var(--ink-soft);
            }}

            .reasoning-toggle input {{
                width: auto;
                margin: 0;
                accent-color: var(--brand);
            }}

            .state-box {{
                margin-top: 0.8rem;
                border-radius: 12px;
                border: 1px solid var(--line);
                padding: 0.8rem;
                background: color-mix(in srgb, var(--paper) 88%, transparent);
            }}

            .response-text {{
                white-space: pre-wrap;
                line-height: 1.48;
            }}

            /* Example question option buttons */
            .space-y-2 {{
                display: grid;
                gap: 0.5rem;
            }}

            .space-y-2 button {{
                width: 100%;
                text-align: left;
                padding: 0.55rem 0.72rem;
                border-radius: 10px;
                border: 1px solid var(--line);
                background: color-mix(in srgb, var(--paper) 96%, transparent 4%);
                color: var(--ink);
                font-size: 0.95rem;
                font-weight: 600;
                cursor: pointer;
                transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
                display: inline-flex;
                align-items: center;
                justify-content: flex-start;
                line-height: 1.25;
                min-height: 42px;
            }}

            body[data-theme='dark'] .space-y-4 > div {{
                background: color-mix(in srgb, var(--paper) 90%, black 10%);
                border-color: var(--line);
            }}

            .space-y-2 button:hover {{
                background: color-mix(in srgb, var(--paper) 78%, var(--mint) 22%);
                border-color: color-mix(in srgb, var(--mint) 48%, var(--line) 52%);
                color: var(--ink);
            }}

            body[data-theme='dark'] .space-y-2 button {{
                background: color-mix(in srgb, var(--paper) 88%, black 12%);
                border-color: var(--line);
                color: var(--ink);
            }}

            body[data-theme='dark'] .space-y-2 button:hover {{
                background: color-mix(in srgb, var(--paper) 80%, var(--mint) 20%);
                border-color: color-mix(in srgb, var(--mint) 48%, var(--line) 52%);
                color: var(--ink);
            }}

            .hidden {{ display: none; }}
        </style>
    </head>
    <body data-theme="{initial_theme}">
        <div class="endpoint-shell">
                <!-- Header -->
                <div class="endpoint-card">
                    <h1 class="title">{agent.name}</h1>
                    <p class="subtitle">{agent.description}</p>
                    <span class="pill">Agent ID: {agent_id}</span>
                </div>

                <!-- Auth Section -->
                <div class="endpoint-card">
                    <h2 class="section-title">Authentication</h2>
                    
                    <!-- Token Input -->
                    <div>
                        <label>Access Token</label>
                        <div class="token-row">
                            <input type="password" id="tokenInput" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste purchase access token...">
                            <button type="button" id="toggleTokenBtn" class="token-toggle-btn">Show</button>
                        </div>
                        <p class="helper">Use purchase token as bearer token.</p>
                    </div>
                </div>

                <!-- Query Section -->
                <div class="endpoint-card">
                    <h2 class="section-title">Ask A Question</h2>
                    
                    <div>
                        <textarea id="questionInput" placeholder="Ask a question... Examples:&#10;- How many rock tracks?&#10;- How many total tracks?&#10;- What genres are available?" rows="4"></textarea>
                        <label class="reasoning-toggle" for="reasoningToggle">
                            <input type="checkbox" id="reasoningToggle">
                            Show reasoning/details
                        </label>
                        
                        <button onclick="askAgent()" class="ask-btn">Ask Agent</button>
                    </div>

                    <!-- Response Section -->
                    <div id="responseSection" class="state-box hidden">
                        <h3 class="section-title">Response</h3>
                        <p class="helper"><strong>Mode:</strong> <span id="responseMode">Concise</span></p>
                        <p id="responseText" class="response-text"></p>
                        <div class="helper" style="margin-top:0.45rem;">
                            <p>
                                <strong>Demo Uses Left:</strong> <span id="demoUsesLeft">-</span>
                            </p>
                        </div>
                    </div>

                    <!-- Error Section -->
                    <div id="errorSection" class="state-box hidden" style="border-color:#f3cfbe;">
                        <p><strong>Error:</strong> <span id="errorText"></span></p>
                    </div>

                    <!-- Loading -->
                    <div id="loadingSection" class="state-box hidden">
                        <span>Processing your question...</span>
                    </div>
                </div>

                <!-- Example Questions -->
                <div class="endpoint-card">
                    <h3 class="section-title">Example Questions By Domain</h3>
                    {example_questions_html}
                </div>
        </div>

        <script>
        const AGENT_ID = '{agent_id}';
        const TOKEN_STORAGE_KEY = `agent-access-token-${{AGENT_ID}}`;
        const tokenInputEl = document.getElementById('tokenInput');
        const toggleTokenBtn = document.getElementById('toggleTokenBtn');
        const urlTheme = new URLSearchParams(window.location.search).get('theme');
        const savedAppTheme = localStorage.getItem('app-theme');
        const savedTheme = localStorage.getItem('theme');
        const systemDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        let pageTheme = (urlTheme === 'dark' || urlTheme === 'light')
            ? urlTheme
            : (savedAppTheme || savedTheme || (systemDark ? 'dark' : 'light'));
        document.body.setAttribute('data-theme', pageTheme);
        localStorage.setItem('app-theme', pageTheme);
        localStorage.setItem('theme', pageTheme);

        const savedAccessToken = sessionStorage.getItem(TOKEN_STORAGE_KEY);
        if (savedAccessToken) {{
            tokenInputEl.value = savedAccessToken;
        }}

        tokenInputEl.addEventListener('input', () => {{
            const currentValue = tokenInputEl.value.trim();
            if (currentValue) {{
                sessionStorage.setItem(TOKEN_STORAGE_KEY, currentValue);
            }} else {{
                sessionStorage.removeItem(TOKEN_STORAGE_KEY);
            }}
        }});

        toggleTokenBtn.addEventListener('click', () => {{
            const showing = tokenInputEl.type === 'text';
            tokenInputEl.type = showing ? 'password' : 'text';
            toggleTokenBtn.textContent = showing ? 'Show' : 'Hide';
        }});

        function fillQuestion(question) {{
            document.getElementById('questionInput').value = question;
            document.getElementById('questionInput').focus();
        }}

        async function askAgent() {{
            const tokenInput = document.getElementById('tokenInput');
            const token = tokenInput.value.trim();
            const question = document.getElementById('questionInput').value.trim();
            const includeReasoning = document.getElementById('reasoningToggle').checked;

            if (!token) {{
                showError('Please enter your access token');
                return;
            }}
            if (!question) {{
                showError('Please enter a question');
                return;
            }}

            showLoading(true);
            hideError();

            try {{
                const response = await fetch(`${window.location.origin}/agents/${{AGENT_ID}}/purchased-ask`, {{
                    method: 'POST',
                    headers: {{
                        'Authorization': `Bearer ${{token}}`,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ question: question, include_reasoning: includeReasoning }})
                }});

                const data = await response.json();

                if (response.ok) {{
                    showResponse(data.response, data.demo_uses_left, !!data.include_reasoning);
                }} else {{
                    showError(data.detail || 'Failed to query agent');
                }}
            }} catch (error) {{
                showError('Connection error: ' + error.message);
            }} finally {{
                showLoading(false);
            }}
        }}

        function showResponse(response, demoUsesLeft, includeReasoning) {{
            document.getElementById('responseMode').textContent = includeReasoning ? 'Detailed' : 'Concise';
            document.getElementById('responseText').textContent = response;
            document.getElementById('demoUsesLeft').textContent = (demoUsesLeft === null || demoUsesLeft === -1)
                ? '∞ Unlimited (purchased)'
                : demoUsesLeft;
            document.getElementById('responseSection').classList.remove('hidden');
            document.getElementById('errorSection').classList.add('hidden');
        }}

        function showError(message) {{
            document.getElementById('errorText').textContent = message;
            document.getElementById('errorSection').classList.remove('hidden');
            document.getElementById('responseSection').classList.add('hidden');
        }}

        function hideError() {{
            document.getElementById('errorSection').classList.add('hidden');
        }}

        function showLoading(show) {{
            document.getElementById('loadingSection').classList.toggle('hidden', !show);
        }}

        // Allow Ctrl+Enter to submit
        document.getElementById('questionInput').addEventListener('keydown', (e) => {{
            if (e.ctrlKey && e.key === 'Enter') {{
                askAgent();
            }}
        }});
        </script>
    </body>
    </html>
    """
    
    return html

# LOGGING ENDPOINTS
@app.get("/logs")
async def get_logs(
    limit: int = 100,
    event_type: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get system logs (filtered by event type if specified)"""
    filtered_logs = logs_store[-limit:]
    
    if event_type:
        filtered_logs = [log for log in filtered_logs if log["event_type"] == event_type]
    
    log_event("LOGS_FETCHED", {"limit": limit, "event_type": event_type, "count": len(filtered_logs)}, user=current_user)
    return filtered_logs

@app.get("/logs/events")
async def get_log_events(current_user: str = Depends(get_current_user)):
    """Get unique event types"""
    events = list(set(log["event_type"] for log in logs_store))
    return {"events": events}

@app.delete("/logs")
async def clear_logs(current_user: str = Depends(get_current_user)):
    """Clear all logs (admin only)"""
    if current_user != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    global logs_store
    logs_store = []
    log_event("LOGS_CLEARED", {"user": current_user}, user=current_user)
    return {"message": "Logs cleared"}

# HEALTH ENDPOINT
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents_count": len(agents_db),
        "logs_count": len(logs_store)
    }

# ROOT ENDPOINT
@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon to prevent 404 errors"""
    return Response(
        content=b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x18\x00\x30\x00\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00\x20\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        media_type="image/x-icon"
    )

@app.get("/")
async def root():
    """API info"""
    return {
        "name": "Agent Marketplace API",
        "version": "1.0",
        "agents": 3,
        "endpoints": {
            "auth": [
                "/auth/login",
                "/auth/register"
            ],
            "agents": [
                "/agents",
                "/agents/{agent_id}"
            ],
            "communication": [
                "/agents/send-message",
                "/agents/{agent_id}/messages",
                "/agents/communication/history"
            ],
            "logs": [
                "/logs",
                "/logs/events",
                "/logs/delete"
            ],
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Agent Marketplace API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)