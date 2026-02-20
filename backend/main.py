from fastapi import FastAPI, Body
from rag import load_kb, search_kb
from groq import Groqfrom 
import json
import uuid
import os
import mysql.connector
from dotenv import load_dotenv

# ---------------------------------------------------------
# LOAD ENV VARIABLES
# ---------------------------------------------------------
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# GROQ CLIENT
# ---------------------------------------------------------
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# ---------------------------------------------------------
# MYSQL CONNECTION
# ---------------------------------------------------------
def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

# ---------------------------------------------------------
# CREATE SESSION IF NOT EXISTS
# ---------------------------------------------------------
def create_session_if_not_exists(session_id):

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT IGNORE INTO sessions (session_id)
        VALUES (%s)
    """, (session_id,))

    db.commit()

    cursor.close()
    db.close()

# ---------------------------------------------------------
# LOAD SESSION HISTORY
# ---------------------------------------------------------
def load_session_history(session_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT role, content
        FROM conversation_history
        WHERE session_id = %s
        ORDER BY created_at ASC
        LIMIT 10
    """, (session_id,))

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    history = []

    for row in rows:
        history.append({
            "role": row["role"],
            "content": row["content"]
        })

    return history

# ---------------------------------------------------------
# SAVE MESSAGE
# ---------------------------------------------------------
def save_message(session_id, role, content, tier=None, severity=None, confidence=None):

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO conversation_history
        (session_id, role, content, tier, severity, confidence)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (session_id, role, content, tier, severity, confidence))

    db.commit()

    cursor.close()
    db.close()

# ---------------------------------------------------------
# SAVE TICKET
# ---------------------------------------------------------
def save_ticket(ticket_id, session_id, message, severity, tier):

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO tickets
        (ticket_id, session_id, message, severity, tier, status)
        VALUES (%s, %s, %s, %s, %s, 'OPEN')
    """, (ticket_id, session_id, message, severity, tier))

    db.commit()

    cursor.close()
    db.close()

# ---------------------------------------------------------
# SAVE GUARDRAIL EVENT
# ---------------------------------------------------------
def save_guardrail_event(session_id, message, reason):

    #print("INSERTING GUARDRAIL EVENT:", session_id, message, reason)

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO guardrail_events
        (session_id, message, reason)
        VALUES (%s, %s, %s)
    """, (session_id, message, reason))

    db.commit()

    #print("INSERT SUCCESS")

    cursor.close()
    db.close()


# ---------------------------------------------------------
# METRICS STORAGE (IN MEMORY)
# ---------------------------------------------------------
# ---------------------------------------------------------
def save_metric(session_id, tier, severity, blocked, escalated):

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO metrics
        (session_id, tier, severity, blocked, escalated)
        VALUES (%s, %s, %s, %s, %s)
    """, (session_id, tier, severity, blocked, escalated))

    db.commit()

    cursor.close()
    db.close()


# ---------------------------------------------------------
# STARTUP
# --------------------------------------------------------

# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"status": "backend is running"}
# ---------------------------------------------------------
# LOAD SESSION HISTORY FROM MYSQL
# ---------------------------------------------------------

# ---------------------------------------------------------
# LLM CALL FUNCTION WITH HISTORY
# ---------------------------------------------------------
def call_groq_cleaner(user_message: str, kb_chunks: list, history: list):

    kb_text = json.dumps(kb_chunks, indent=2)

    prompt = f"""
You are EasyStepIn CyberLab AI Help Desk Assistant.

You MUST follow these rules exactly.

--------------------------------------------------
RULE 1 — CYBERLAB IN-SCOPE TOPICS
--------------------------------------------------

The following topics are ALWAYS in scope:

- virtual machine
- vm crash
- vm froze
- vm not responding
- lab crash
- lab environment failure
- container failure
- login issues
- authentication issues
- dns issues
- cyberlab training environment
- infrastructure troubleshooting

If user mentions ANY of the above, you MUST treat it as IN-SCOPE.

NEVER classify VM crash, lab crash, or environment crash as out-of-scope.

--------------------------------------------------
RULE 2 — SECURITY POLICY BLOCK
--------------------------------------------------

If user asks for:

- credentials
- passwords
- secrets
- root access
- hypervisor access
- host machine access
- destructive commands

Return ONLY:

{{
 "answer":"I cannot help with that request due to policy restrictions.",
 "kbReferences":[],
 "confidence":0.1,
 "tier":"TIER_1",
 "severity":"CRITICAL",
 "needsEscalation":False,
 "guardrail":{{"blocked":true,"reason":"policy_violation"}}
}}

--------------------------------------------------
RULE 3 — OUT-OF-SCOPE QUESTIONS
--------------------------------------------------

Only classify as out-of-scope if question is unrelated to CyberLab, VMs, containers, authentication, or infrastructure.

Return ONLY:

{{
 "answer":"This question is outside the CyberLab knowledge base.",
 "kbReferences":[],
 "confidence":0.3,
 "tier":"TIER_1",
 "severity":"LOW",
 "needsEscalation":false,
 "guardrail":{{"blocked":false,"reason":null}}
}}

--------------------------------------------------
RULE 4 — KB USAGE
--------------------------------------------------

If KB CONTENT contains recovery steps, you MUST use them.

NEVER say KB missing if KB CONTENT exists.

--------------------------------------------------
RULE 5 — OUTPUT FORMAT
--------------------------------------------------

Return STRICT JSON ONLY.

Return this exact structure:

{{
 "answer":"...",
 "kbReferences":[],
 "confidence":0.85,
 "tier":"TIER_1|TIER_2|TIER_3",
 "severity":"LOW|MEDIUM|HIGH|CRITICAL",
 "needsEscalation":true/false,
 "guardrail":{{"blocked":false,"reason":null}}
}}

--------------------------------------------------
KB CONTENT
--------------------------------------------------

{json.dumps(kb_chunks, indent=2)}

--------------------------------------------------
USER QUESTION
--------------------------------------------------

{user_message}
"""



    messages = [
        {
            "role": "system",
            "content": "You are a strict JSON API. Return valid JSON only."
        }
    ]

    # Add history
    for msg in history:
        messages.append(msg)

    # Add current prompt
    messages.append({
        "role": "user",
        "content": prompt
    })

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0,
        max_completion_tokens=512,
    )

    raw_output = completion.choices[0].message.content

    try:

        raw_output = raw_output.strip()

        json_start = raw_output.find("{")
        json_end = raw_output.rfind("}") + 1

        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON found in model output")

        json_text = raw_output[json_start:json_end]

        parsed = json.loads(json_text)

        parsed.setdefault("answer", "")
        parsed.setdefault("kbReferences", [])
        parsed.setdefault("confidence", 0.5)
        parsed.setdefault("tier", "TIER_1")
        parsed.setdefault("severity", "LOW")
        parsed.setdefault("needsEscalation", False)
        parsed.setdefault("guardrail", {"blocked": False, "reason": None})

        return parsed

    except Exception as e:

        print("JSON PARSE ERROR:", str(e))
        print("RAW OUTPUT:", raw_output)

        return {
            "answer": raw_output,
            "kbReferences": [],
            "confidence": 0.5,
            "tier": "TIER_2",
            "severity": "HIGH",
            "needsEscalation": False,
            "guardrail": {
                "blocked": False,
                "reason": "parse_failed_raw_return"
            }
        }

def apply_escalation_rules(message: str, tier: str, severity: str, needsEscalation: bool):

    msg = message.lower()

    critical_keywords = [
        "vm crash",
        "vm crashed",
        "vm froze",
        "kernel panic",
        "lab crash",
        "environment failure",
        "container failure"
    ]

    for keyword in critical_keywords:
        if keyword in msg:
            return True, "TIER_3", "CRITICAL"

    return needsEscalation, tier, severity

        

# ---------------------------------------------------------
# CHAT ENDPOINT
# ---------------------------------------------------------
@app.post("/api/chat")
def chat(body: dict = Body(...)):

    message = body.get("message", "").strip()
    session_id = body.get("sessionId")

    if not session_id:
        session_id = str(uuid.uuid4())

    create_session_if_not_exists(session_id)

    print("MESSAGE:", message)

    history = load_session_history(session_id)

    results = search_kb(message)
    kb_chunks = [r["text"] for r in results[:2]] if results else []

    # save user message
    save_message(session_id, "user", message)

    llm_output = call_groq_cleaner(message, kb_chunks, history)

    tier = llm_output.get("tier")
    severity = llm_output.get("severity")
    confidence = llm_output.get("confidence")
    needsEscalation = llm_output.get("needsEscalation")

    needsEscalation, tier, severity = apply_escalation_rules(
    message,
    tier,
    severity,
    needsEscalation
)


    guardrail_info = llm_output.get("guardrail", {})
    blocked = guardrail_info.get("blocked", False)

    # save assistant message
    save_message(
        session_id,
        "assistant",
        llm_output.get("answer"),
        tier,
        severity,
        confidence
    )

    # save guardrail event
    if blocked:
        save_guardrail_event(
            session_id,
            message,
            guardrail_info.get("reason")
        )
    # save metrics to MySQL
    save_metric(
        session_id,
        tier,
        severity,
        blocked,
        needsEscalation
        )


    ticket_id = None

    # Create ticket ONLY for real infrastructure escalation
    # NOT for guardrail violations
    # NOT for parse failures
    if (
        needsEscalation is True
        and blocked is False
        and guardrail_info.get("reason") != "policy_violation"
    ):

        ticket_id = str(uuid.uuid4())

        save_ticket(
            ticket_id,
            session_id,
            message,
            severity,
            tier
        )


    return {
        "sessionId": session_id,
        "answer": llm_output.get("answer"),
        "kbReferences": llm_output.get("kbReferences"),
        "confidence": confidence,
        "tier": tier,
        "severity": severity,
        "needsEscalation": needsEscalation,
        "ticketId": ticket_id,
        "guardrail": guardrail_info
    }


# ---------------------------------------------------------
# GET ALL TICKETS
# ---------------------------------------------------------
@app.get("/api/tickets")
def get_all_tickets():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM tickets
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return {
        "tickets": rows,
        "count": len(rows)
    }


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM tickets
        WHERE ticket_id = %s
    """, (ticket_id,))

    ticket = cursor.fetchone()

    cursor.close()
    db.close()

    if not ticket:
        return {"error": "Ticket not found"}

    return ticket

# ---------------------------------------------------------
# METRICS SUMMARY
# ---------------------------------------------------------
@app.get("/api/metrics/summary")
def metrics_summary():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as totalChats FROM metrics")
    total = cursor.fetchone()["totalChats"]

    cursor.execute("SELECT COUNT(*) as guardrailBlocks FROM metrics WHERE blocked = TRUE")
    guardrailBlocks = cursor.fetchone()["guardrailBlocks"]

    cursor.execute("SELECT COUNT(*) as escalations FROM metrics WHERE escalated = TRUE")
    escalations = cursor.fetchone()["escalations"]

    cursor.execute("""
        SELECT tier, COUNT(*) as count
        FROM metrics
        GROUP BY tier
    """)
    byTier = {row["tier"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT severity, COUNT(*) as count
        FROM metrics
        GROUP BY severity
    """)
    bySeverity = {row["severity"]: row["count"] for row in cursor.fetchall()}

    cursor.close()
    db.close()

    deflection = (total - escalations) / total if total > 0 else 0

    return {
        "totalChats": total,
        "guardrailBlocks": guardrailBlocks,
        "escalations": escalations,
        "deflectionRate": round(deflection, 2),
        "byTier": byTier,
        "bySeverity": bySeverity
    }

@app.get("/api/metrics/trends")
def metrics_trends():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as chatCount
        FROM metrics
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
    """)

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return {"dailyChatVolume": rows}
