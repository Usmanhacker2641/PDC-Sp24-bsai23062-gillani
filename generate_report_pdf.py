"""
PDF Report Generator — PDC Assignment
Student: Muhammad Usman Gillani | bsai23062

This script programmatically generates a gorgeous, publication-quality,
3-page PDF report analyzing the three distributed systems bugs and
describing their architectural fixes (complete with a programmatically
drawn UML sequence diagram for optimistic locking).
"""

import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Group


def create_uml_diagram() -> Drawing:
    """Draws a premium UML sequence diagram for Optimistic Locking."""
    d = Drawing(480, 240)
    
    # Grid background for a technical blueprint feel
    d.add(Rect(0, 0, 480, 240, fillColor=colors.HexColor("#F8FAFC"), strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=1, rx=6, ry=6))
    
    # Horizontal/Vertical Lifelines
    x_user_a = 60
    x_fastapi = 240
    x_user_b = 420
    
    # Lifeline titles
    # Actor/System boxes
    # User A
    d.add(Rect(x_user_a - 40, 205, 80, 24, fillColor=colors.HexColor("#1E293B"), strokeColor=None, rx=4, ry=4))
    d.add(String(x_user_a, 212, "User A", textAnchor="middle", fontSize=9, fillColor=colors.white, fontName="Helvetica-Bold"))
    
    # FastAPI / Database
    d.add(Rect(x_fastapi - 55, 205, 110, 24, fillColor=colors.HexColor("#0F172A"), strokeColor=None, rx=4, ry=4))
    d.add(String(x_fastapi, 212, "FastAPI Server & DB", textAnchor="middle", fontSize=9, fillColor=colors.white, fontName="Helvetica-Bold"))
    
    # User B
    d.add(Rect(x_user_b - 40, 205, 80, 24, fillColor=colors.HexColor("#1E293B"), strokeColor=None, rx=4, ry=4))
    d.add(String(x_user_b, 212, "User B", textAnchor="middle", fontSize=9, fillColor=colors.white, fontName="Helvetica-Bold"))
    
    # Vertical lifeline dashed lines
    def draw_lifeline(x):
        line = Line(x, 25, x, 205, strokeColor=colors.HexColor("#94A3B8"), strokeWidth=1)
        line.strokeDashArray = [4, 4]
        d.add(line)
        
    draw_lifeline(x_user_a)
    draw_lifeline(x_fastapi)
    draw_lifeline(x_user_b)
    
    # Helper to draw arrows
    def draw_arrow(x1, x2, y, text, is_dashed=False, is_error=False, num_prefix=""):
        # Draw line
        color = colors.HexColor("#EF4444") if is_error else colors.HexColor("#334155")
        line = Line(x1, y, x2, y, strokeColor=color, strokeWidth=1.2)
        if is_dashed:
            line.strokeDashArray = [3, 3]
        d.add(line)
        
        # Draw arrowhead
        arrow_size = 5
        if x1 < x2: # Points right
            arrow = Polygon([x2, y, x2 - arrow_size, y + 2.5, x2 - arrow_size, y - 2.5], fillColor=color, strokeColor=color)
        else: # Points left
            arrow = Polygon([x2, y, x2 + arrow_size, y + 2.5, x2 + arrow_size, y - 2.5], fillColor=color, strokeColor=color)
        d.add(arrow)
        
        # Draw text label
        text_y = y + 4
        text_x = (x1 + x2) / 2
        lbl_color = colors.HexColor("#991B1B") if is_error else colors.HexColor("#1E293B")
        f_style = "Helvetica-Bold" if is_error else "Helvetica"
        d.add(String(text_x, text_y, text, textAnchor="middle", fontSize=7.5, fillColor=lbl_color, fontName=f_style))

    # Event sequence (Time goes down, y decreases)
    # 1. User A reads document
    draw_arrow(x_user_a, x_fastapi, 185, "1. Read Document (GET /documents/1)")
    draw_arrow(x_fastapi, x_user_a, 170, "2. Returns Document Content & Version 5", is_dashed=True)
    
    # 2. User B reads document (concurrently)
    draw_arrow(x_user_b, x_fastapi, 150, "3. Read Document (GET /documents/1)")
    draw_arrow(x_fastapi, x_user_b, 135, "4. Returns Document Content & Version 5", is_dashed=True)
    
    # 3. User A updates document (FastAPI updates DB version to 6)
    draw_arrow(x_user_a, x_fastapi, 110, "5. Update Request (PUT /documents/1, v=5)")
    draw_arrow(x_fastapi, x_user_a, 95, "6. DB Version matches (5)! Bumps to v6 & returns 200 OK", is_dashed=True)
    
    # 4. User B updates document (fails because current DB version is 6, B sent v=5)
    draw_arrow(x_user_b, x_fastapi, 65, "7. Update Request (PUT /documents/1, v=5)")
    draw_arrow(x_fastapi, x_user_b, 50, "8. DB version conflict (6 != 5)! Aborts & returns 409 Conflict", is_dashed=True, is_error=True)
    
    return d


def generate_pdf(filename: str):
    # Setup document
    # Top/Bottom margins set to 0.5 inches (36pt) to ensure the 3-page constraint is cleanly held.
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    # Style definitions
    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#0F172A") # Deep Slate
    accent_color = colors.HexColor("#4F46E5")  # Indigo
    dark_gray = colors.HexColor("#334155")
    light_blue = colors.HexColor("#EFF6FF")
    border_blue = colors.HexColor("#BFDBFE")
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=primary_color,
        alignment=TA_LEFT,
        spaceAfter=6
    )
    
    student_meta_style = ParagraphStyle(
        'StudentMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=accent_color,
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=8,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=accent_color,
        spaceBefore=8,
        spaceAfter=5,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextJustified',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=dark_gray,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )
    
    code_box_style = ParagraphStyle(
        'CodeBoxStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B"),
        alignment=TA_LEFT
    )
    
    caption_style = ParagraphStyle(
        'ImageCaption',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#64748B"),
        spaceBefore=4,
        spaceAfter=10
    )
    
    story = []
    
    # ══════════════════════════════════════════════
    # PAGE 1: TITLE BLOCK & PART 1: BUG ANALYSIS
    # ══════════════════════════════════════════════
    
    story.append(Paragraph("Building Resilient Distributed Systems", title_style))
    story.append(Paragraph("Muhammad Usman Gillani  |  Student ID: bsai23062", student_meta_style))
    
    # Separator line
    sep_table = Table([[""]], colWidths=[540])
    sep_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 1.5, primary_color),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(sep_table)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Part 1: Distributed Systems Bug Analysis (StudySync Scenario)", h1_style))
    
    # Bug 1
    story.append(Paragraph("1.1 The Synchronization Bug (Lost Update Anomaly)", h2_style))
    story.append(Paragraph(
        "In the initial StudySync collaborative document editor, concurrent updates are prone to a severe "
        "data loss pattern known as the <b>Lost Update Anomaly</b>. The root cause is a complete lack of concurrency control "
        "or isolation boundaries at the persistence and application layer. When User A and User B concurrently "
        "decide to edit the same lecture notes, they both perform an independent and overlapping <b>Read-Modify-Write cycle</b> "
        "simultaneously. Under naive operations, User A reads document state $S$ at timestamp $T_1$. Fractions of a second "
        "later, User B reads the identical state $S$ at timestamp $T_2$. "
        "User A completes their edits locally and submits their payload, which the backend blindly writes, updating the database state "
        "to $S'$. Immediately following, User B completes their independent edit (having no awareness of User A's intermediate submission) "
        "and submits their payload. The server receives User B's write and blindly overwrites the database with User B's state $S''. "
        "Consequently, User A's entire set of changes is permanently obliterated without warning. This is the classic lost update "
        "anomaly, arising because neither the application code nor the database enforces atomic version checks or transactional "
        "optimistic/pessimistic locking mechanisms.",
        body_style
    ))
    
    # Bug 2
    story.append(Paragraph("1.2 The Webhook Coordination Bug (Unreliable Message Delivery)", h2_style))
    story.append(Paragraph(
        "In the subscription cancellation flow, Clerk is configured to dispatch a single HTTP POST event notifying the "
        "StudySync backend of a cancellation. The fundamental defect is a coordination failure over an unreliable network. Clerk uses "
        "an <i>at-most-once</i> delivery paradigm in its native, non-retry configurations. Because HTTP is an unreliable, "
        "stateless protocol, packet drops, routing loops, or transient server-side crashes will prevent the webhook from being "
        "processed. Since the initial implementation contains no transaction deduplication, retry queues, or acknowledgment "
        "handshakes, a dropped HTTP request is permanently lost. The Clerk billing provider registers the user as 'Cancelled' (state $X$), "
        "while the local database continues to mark the user as 'Premium' (state $Y$), creating a permanent state inconsistency. "
        "This coordination mismatch permits cancelled users to bypass paywalls indefinitely, representing a significant loss of business integrity.",
        body_style
    ))
    
    # Bug 3
    story.append(Paragraph("1.3 The Fault Tolerance Bug (LLM API Timeout Cascading Failure)", h2_style))
    story.append(Paragraph(
        "The third defect is an architectural fault tolerance failure caused by wrapping slow, external, synchronous LLM calls directly "
        "inside a web service endpoint without isolating execution pools or establishing fail-fast thresholds. When an external LLM "
        "provider hangs, a single synchronous call ties up a FastAPI async worker thread for the entire 60-second timeout period. "
        "FastAPI handles incoming concurrent requests using a finite worker pool (or a thread pool for synchronous database/IO tasks). "
        "Under moderate traffic, if enough users concurrently hit the AI feature while the LLM is down, all available async workers "
        "and thread pools are quickly exhausted, blocking on the hanging downstream network sockets. "
        "As a result, the entire web server is rendered completely unresponsive, and even unrelated, instantaneous operations (like retrieving "
        "static notes or registering users) fail with Gateway Timeouts. This allows a slow, optional third-party service to act as a "
        "<b>Single Point of Failure (SPOF)</b>, cascading a localized dependency delay into a total system-wide blackout.",
        body_style
    ))
    
    story.append(PageBreak())
    
    # ══════════════════════════════════════════════
    # PAGE 2: PART 2: ARCHITECTURAL FIXES (SYNCHRONIZATION & DIAGRAM)
    # ══════════════════════════════════════════════
    
    story.append(Paragraph("Part 2: Resilient Distributed System Architecture Designs", h1_style))
    
    story.append(Paragraph("2.1 Synchronization Fix — Optimistic Locking", h2_style))
    story.append(Paragraph(
        "To resolve the Lost Update Anomaly, we implement <b>Optimistic Locking</b> using a dedicated <code>version</code> column "
        "in the database. Optimistic locking is an ideal concurrency control mechanism for read-heavy, low-contention environments "
        "like document editing. It avoids the heavy performance penalties and potential deadlock scenarios associated with pessimistic database "
        "row locks (e.g., <code>SELECT ... FOR UPDATE</code>).",
        body_style
    ))
    
    # Code box for SQL
    sql_text = (
        "<b>Database Schema and Atomic Query:</b><br/>"
        "<code>ALTER TABLE documents ADD COLUMN version INTEGER DEFAULT 1;<br/>"
        "<br/>"
        "/* The atomic write query executed on save */<br/>"
        "UPDATE documents <br/>"
        "SET content = :new_content, version = version + 1 <br/>"
        "WHERE id = :doc_id AND version = :client_read_version;</code>"
    )
    sql_table = Table([[Paragraph(sql_text, code_box_style)]], colWidths=[540])
    sql_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_blue),
        ('BOX', (0, 0), (-1, -1), 1, border_blue),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(sql_table)
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(
        "When a client requests a document (GET), the server returns the content alongside its current <code>version</code> integer. "
        "When submitting modifications, the client must send back that version number inside the payload. The database then executes "
        "the update query above. If another concurrent session (User A) has successfully saved its changes first, the database version "
        "will have already incremented, making User B's query criteria <code>WHERE version = 5</code> fail. No rows are modified. The "
        "backend detects that zero rows were updated, rolls back any associated changes, and returns an HTTP <b>409 Conflict</b> "
        "response. This alerts the client that a conflict occurred, prompting them to fetch the latest changes, resolve conflicts, and retry.",
        body_style
    ))
    
    # Embed the UML Sequence Diagram
    story.append(Spacer(1, 4))
    story.append(create_uml_diagram())
    story.append(Paragraph("Figure 1: Sequence diagram of concurrent edit resolution using version-based optimistic locking", caption_style))
    
    story.append(PageBreak())
    
    # ══════════════════════════════════════════════
    # PAGE 3: COORDINATION, FAULT TOLERANCE & CAP
    # ══════════════════════════════════════════════
    
    story.append(Paragraph("2.2 Webhook Coordination Fix — Idempotent Webhook Handler & Retries", h2_style))
    story.append(Paragraph(
        "To ensure reliable and consistent webhook state coordination between Clerk and StudySync, we establish an "
        "<b>Idempotent Webhook Handler</b>. We create a <code>processed_webhooks</code> table with a unique constraint on Clerk's "
        "<code>event_id</code> (provided in the webhook metadata). "
        "When an event is received, the backend executes the following atomic flow inside a single database transaction:<br/>"
        "1. Check if <code>event_id</code> already exists in the <code>processed_webhooks</code> database table. If yes, immediately abort "
        "and return a friendly <b>HTTP 200 OK</b> response (duplicate event is discarded safely without modifying state).<br/>"
        "2. If the event is new, execute the business logic (e.g., set <code>is_premium = False</code>) and insert the <code>event_id</code> "
        "into the <code>processed_webhooks</code> table.<br/>"
        "3. Commit the transaction. If a race condition occurs, the unique database constraint will abort the duplicate execution safely.<br/>"
        "In addition, we configure Clerk's webhook dashboard to implement <b>exponential backoff retries</b>. If our server is down, "
        "Clerk will continuously retry the cancellation. Once our server recovers, the first retry processes the event, and any "
        "redundant retries are safely ignored by our idempotent handler. For maximum durability, failed events after retries can "
        "be pushed to a <b>Dead-Letter Queue (DLQ)</b> in Redis, allowing automatic alerts and manual administrative replays.",
        body_style
    ))
    
    # Circuit Breaker Fix
    story.append(Paragraph("2.3 Fault Tolerance Fix — Three-State Circuit Breaker Pattern", h2_style))
    story.append(Paragraph(
        "To isolate slow AI processes and prevent application worker pool starvation, we wrap the downstream LLM service inside a "
        "<b>Circuit Breaker</b>. The breaker tracks the state of the LLM using a state machine consisting of three operational states:<br/>"
        "• <b>CLOSED:</b> All requests flow directly to the LLM. Every successful call clears the failure count. Every exception or timeout "
        "increments the failure counter. If failures exceed a defined threshold (e.g., 5 consecutive failures), the breaker trips to the OPEN state.<br/>"
        "• <b>OPEN:</b> Incoming requests are immediately short-circuited. No socket connections are made to the LLM, protecting server-side "
        "async resources and worker threads from hanging. The server instantly returns a predefined <b>degraded fallback response</b> "
        "(e.g., an HTTP 503 status code with a payload stating 'AI suggestions are temporarily unavailable') in under 10 milliseconds. "
        "A cooldown timer (e.g., 30 seconds) is initiated upon entering the OPEN state.<br/>"
        "• <b>HALF-OPEN:</b> Once the cooldown timer expires, the breaker transitions to the HALF-OPEN state. It permits a single 'trial' request "
        "to pass through. If this trial call succeeds, the breaker assumes the downstream service has recovered, resets the failure counter, and "
        "returns to the CLOSED state. If the trial call fails, the breaker assumes the service is still unhealthy, immediately returns "
        "to the OPEN state, and restarts the cooldown timer.",
        body_style
    ))
    
    # CAP Theorem
    story.append(Paragraph("2.4 Distributed Systems CAP Theorem Trade-offs", h2_style))
    story.append(Paragraph(
        "The architectural mitigations represent a classic study of trade-offs defined by the <b>CAP Theorem</b>. "
        "Our version-based <b>Optimistic Locking</b> design explicitly prioritizes <b>Consistency (C) over Availability (A)</b>. "
        "When concurrent write conflicts are detected, the system deliberately rejects edits (degrading write availability for the conflicting client) "
        "to guarantee that the database remains in a perfectly accurate, uncorrupted, and consistent state. "
        "Conversely, the <b>Circuit Breaker</b> pattern prioritizes <b>Availability (A) over Consistency (C)</b> (specifically in terms of query "
        "up-to-dateness or suggestion completeness). When the downstream AI service fails, the circuit breaker bypasses the LLM "
        "and immediately serves a stale, cached, or degraded placeholder fallback response. This ensures the application remains fully "
        "available and highly responsive for the end user, prioritizing usability and operational uptime over real-time computational accuracy.",
        body_style
    ))
    
    # Build PDF
    doc.build(story)
    print(f"Success: compiled report: {filename}")


if __name__ == "__main__":
    output_name = "PDC-Sp24-bsai23062-Gillani_Report.pdf"
    if len(sys.argv) > 1:
        output_name = sys.argv[1]
    generate_pdf(output_name)
