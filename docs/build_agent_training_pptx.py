#!/usr/bin/env python3
"""Build SkyKin agent training PowerPoint."""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import nsmap
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

NAVY = RGBColor(0x00, 0x47, 0xAB)
NAVY_DARK = RGBColor(0x00, 0x2F, 0x6C)
GOLD = RGBColor(0xD4, 0xA0, 0x17)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x1E, 0x29, 0x3B)
MUTED = RGBColor(0x47, 0x55, 0x69)
RED = RGBColor(0xC6, 0x28, 0x28)
GREEN = RGBColor(0x1B, 0x7A, 0x3A)
LIGHT = RGBColor(0xF4, 0xF7, 0xFB)
CARD = RGBColor(0xE8, 0xF0, 0xFA)

OUT = Path(__file__).resolve().parent / "SkyKin_Agent_Training.pptx"
LOGO = Path(__file__).resolve().parents[1] / "website" / "public" / "images" / "skykin_logo.png"


def set_run(run, text, size=18, bold=False, color=INK, font="Calibri"):
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font


def add_text_box(slide, l, t, w, h, text, size=18, bold=False, color=INK, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    set_run(p.add_run() if p.runs else p.runs[0] if False else _ensure_run(p), text, size, bold, color)
    return box


def _ensure_run(p):
    if p.runs:
        return p.runs[0]
    return p.add_run()


def tb(slide, l, t, w, h, lines, size=18, color=INK, bold_first=False, spacing=8):
    """lines: list of str, or (text, bold, color, size) tuples."""
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(spacing)
        if isinstance(item, str):
            set_run(_ensure_run(p), item, size, bold_first and i == 0, color)
        else:
            text, b, c, sz = item
            set_run(_ensure_run(p), text, sz, b, c)
    return box


def bullets(slide, l, t, w, h, items, size=18):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = 0
        p.space_after = Pt(10)
        if isinstance(item, tuple):
            text, c = item
            set_run(_ensure_run(p), "•  " + text, size, False, c)
        else:
            set_run(_ensure_run(p), "•  " + item, size, False, INK)
    return box


def bar(slide, color=NAVY, h=1.15):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    gold = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(h), Inches(13.333), Inches(0.06))
    gold.fill.solid()
    gold.fill.fore_color.rgb = GOLD
    gold.line.fill.background()


def footer(slide, n, total):
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(7.28), Inches(13.333), Inches(0.22)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = NAVY
    line.line.fill.background()
    box = slide.shapes.add_textbox(Inches(0.4), Inches(7.28), Inches(10), Inches(0.22))
    p = box.text_frame.paragraphs[0]
    set_run(_ensure_run(p), "SkyKin Technologies  ·  Agent Training  ·  Confidential", 10, False, WHITE)
    num = slide.shapes.add_textbox(Inches(11.6), Inches(7.28), Inches(1.4), Inches(0.22))
    p = num.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    set_run(_ensure_run(p), f"{n}  /  {total}", 10, False, WHITE)


def card(slide, l, t, w, h, fill=CARD):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.fill.background()
    try:
        s.adjustments[0] = 0.08
    except Exception:
        pass
    return s


def title_slide_header(slide, title, subtitle=None):
    bar(slide)
    tb(slide, 0.5, 0.28, 12, 0.55, [(title, True, WHITE, 28)])
    if subtitle:
        tb(slide, 0.5, 0.72, 12, 0.35, [(subtitle, False, RGBColor(0xD6, 0xE4, 0xF7), 14)])


def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def build():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    slides = []

    def new():
        s = prs.slides.add_slide(blank)
        slides.append(s)
        return s

    # 1 Title
    s = new()
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY_DARK
    bg.line.fill.background()
    accent = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.18), prs.slide_height)
    accent.fill.solid()
    accent.fill.fore_color.rgb = GOLD
    accent.line.fill.background()
    if LOGO.exists():
        s.shapes.add_picture(str(LOGO), Inches(0.7), Inches(1.15), height=Inches(0.85))
    tb(s, 0.7, 2.15, 12, 1.1, [("Agent Training", True, WHITE, 48)])
    tb(s, 0.7, 3.25, 12, 0.5, [("Softphone, inbound, outbound, and wrap-up", False, RGBColor(0xC5, 0xD4, 0xEA), 22)])
    tb(
        s,
        0.7,
        4.3,
        12,
        1.2,
        [
            ("SkyKin Technologies  ·  Call Center", False, GOLD, 16),
            ("For agents 101 and 102  ·  Chrome + headset  ·  45 minutes", False, RGBColor(0xA8, 0xBB, 0xD4), 15),
        ],
    )
    add_notes(s, "Welcome. Goal: every agent can log in, register the phone, take a call, hang up, and complete ACW without help.")

    # 2 Agenda
    s = new()
    title_slide_header(s, "Agenda")
    items = [
        ("1", "Start of shift — login, headset, Registered"),
        ("2", "Your status — Available, Break, Logout"),
        ("3", "Incoming calls — Answer and Decline"),
        ("4", "During the call — Hold, Mute, Transfer"),
        ("5", "After the call — wrap-up (ACW)"),
        ("6", "Outbound calls — 755 and 756"),
        ("7", "Tickets, lookup, callbacks"),
        ("8", "If something goes wrong"),
    ]
    for i, (num, txt) in enumerate(items):
        col = i % 2
        row = i // 2
        x = 0.55 + col * 6.35
        y = 1.55 + row * 1.25
        card(s, x, y, 6.05, 1.05)
        tb(s, x + 0.2, y + 0.22, 0.7, 0.6, [(num, True, NAVY, 28)])
        tb(s, x + 1.0, y + 0.32, 4.8, 0.5, [(txt, False, INK, 16)])
    add_notes(s, "Walk the agenda. Training is hands-on: agents should have Chrome open on the dashboard.")

    # 3 Tools
    s = new()
    title_slide_header(s, "What you use", "One browser. One headset. No extra phone app.")
    for i, (h, body) in enumerate(
        [
            ("Chrome", "Use Google Chrome only.\nEdge or Firefox will not work reliably."),
            ("Headset", "USB or 3.5 mm headset with a mic.\nAllow microphone when Chrome asks."),
            ("Dashboard", "This is your phone and your work screen.\nKeep this tab open all shift."),
        ]
    ):
        x = 0.5 + i * 4.2
        card(s, x, 1.7, 3.95, 4.4, WHITE)
        top = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(1.7), Inches(3.95), Inches(0.12))
        top.fill.solid()
        top.fill.fore_color.rgb = GOLD if i == 1 else NAVY
        top.line.fill.background()
        tb(s, x + 0.25, 2.1, 3.45, 0.6, [(h, True, NAVY, 24)])
        tb(s, x + 0.25, 2.85, 3.45, 2.8, [(body, False, MUTED, 16)])
    add_notes(s, "Demo: plug headset, open Chrome. Do not use two tabs of the same agent.")

    # 4 Login
    s = new()
    title_slide_header(s, "Start of shift", "Do these four steps in order")
    steps = [
        ("1", "Open the agent page in Chrome", "https://196.189.236.140:8188\n(Your supervisor will confirm the URL.)"),
        ("2", "Sign in with your agent account", "Agent 1 → extension 101\nAgent 2 → extension 102"),
        ("3", "Allow the microphone", "Click the padlock in the address bar\n→ Microphone → Allow"),
        ("4", "Open the phone panel", "Bottom-right phone button.\nWait until it says Registered (101) or (102)."),
    ]
    for i, (n, h, b) in enumerate(steps):
        y = 1.5 + i * 1.3
        circ = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.55), Inches(y + 0.15), Inches(0.55), Inches(0.55))
        circ.fill.solid()
        circ.fill.fore_color.rgb = NAVY
        circ.line.fill.background()
        box = s.shapes.add_textbox(Inches(0.55), Inches(y + 0.22), Inches(0.55), Inches(0.45))
        p = box.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        set_run(_ensure_run(p), n, 18, True, WHITE)
        tb(s, 1.35, y + 0.05, 11, 0.4, [(h, True, INK, 18)])
        tb(s, 1.35, y + 0.45, 11, 0.7, [(b, False, MUTED, 15)])
    add_notes(s, "Never use port 8088 if you were told to use 8188. Same public IP, different system.")

    # 5 Registered
    s = new()
    title_slide_header(s, "You are ready when you see both")
    card(s, 0.5, 1.6, 6.0, 4.7, WHITE)
    tb(s, 0.8, 1.9, 5.4, 0.5, [("Phone panel", True, NAVY, 20)])
    tb(
        s,
        0.8,
        2.5,
        5.4,
        3.4,
        [
            ("Green dot + Registered (101) or (102)", True, GREEN, 18),
            ("", False, INK, 8),
            ("If it says Connecting, Not Registered,", False, MUTED, 16),
            ("or Failed — you will not receive calls.", False, MUTED, 16),
            ("", False, INK, 8),
            ("Reload the page (Ctrl+F5), allow the mic,", False, INK, 16),
            ("and wait 10 seconds.", False, INK, 16),
        ],
    )
    card(s, 6.8, 1.6, 6.0, 4.7, WHITE)
    tb(s, 7.1, 1.9, 5.4, 0.5, [("Status menu (top right)", True, NAVY, 20)])
    tb(
        s,
        7.1,
        2.5,
        5.4,
        3.4,
        [
            ("Available  —  you can take calls", True, GREEN, 18),
            ("", False, INK, 8),
            ("Idle / On Break / Logout  —  you will", False, MUTED, 16),
            ("not be offered new inbound calls the", False, MUTED, 16),
            ("same way. Stay Available when you", False, MUTED, 16),
            ("are at the desk and ready.", False, MUTED, 16),
        ],
    )
    add_notes(s, "Have each agent show you Registered + Available before continuing.")

    # 6 Status
    s = new()
    title_slide_header(s, "Status menu", "Choose the status that matches what you are doing")
    rows = [
        ("Available", "At your desk, headset on, ready for customers.", GREEN),
        ("Idle", "At the desk but not taking queue work right now.", MUTED),
        ("On Break", "Sends a request. Stay Available until a supervisor approves.", RGBColor(0x0E, 0xA5, 0xE9)),
        ("Wrap-up (ACW)", "Finishing notes after a call. Opens automatically after hangup.", RGBColor(0x63, 0x66, 0xF1)),
        ("Logout", "End of shift. Phone unregister. Use Sign Out when you leave.", RED),
    ]
    for i, (name, desc, col) in enumerate(rows):
        y = 1.45 + i * 1.05
        card(s, 0.5, y, 12.3, 0.92, WHITE)
        pill = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.75), Inches(y + 0.22), Inches(2.4), Inches(0.48))
        pill.fill.solid()
        pill.fill.fore_color.rgb = col
        pill.line.fill.background()
        box = s.shapes.add_textbox(Inches(0.75), Inches(y + 0.28), Inches(2.4), Inches(0.4))
        p = box.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        set_run(_ensure_run(p), name, 13, True, WHITE)
        tb(s, 3.4, y + 0.28, 9.1, 0.5, [(desc, False, INK, 16)])
    add_notes(s, "On Break is not instant. Supervisor must approve. Idle timeout will log them out if they leave the PC.")

    # 7 Incoming
    s = new()
    title_slide_header(s, "When a customer calls", "The phone panel switches to Incoming Call")
    bullets(
        s,
        0.55,
        1.55,
        12.2,
        5.3,
        [
            "You will hear ring in the headset and see Answer / Decline.",
            "The number on screen is the customer (for example 2519…).",
            "Put the headset on before you press Answer.",
            "Speak after you hear the customer — do not shout “hello” into a muted mic.",
            "Stay on this Chrome tab. Do not refresh during a ringing or live call.",
            "One customer at a time on the same company number. If you are talking on 755, a second caller to 755 hears busy. 756 can still ring the free agent.",
        ],
        18,
    )
    add_notes(s, "Demo an inbound to 755 and 756. Explain one-call-per-DID.")

    # 8 Answer / Decline
    s = new()
    title_slide_header(s, "Answer vs Decline", "These two buttons do very different things")
    card(s, 0.5, 1.55, 6.0, 5.0, WHITE)
    head = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.55), Inches(6.0), Inches(0.7))
    head.fill.solid()
    head.fill.fore_color.rgb = GREEN
    head.line.fill.background()
    tb(s, 0.5, 1.68, 6.0, 0.5, [("ANSWER  (green)", True, WHITE, 20)],)
    bullets(
        s,
        0.75,
        2.5,
        5.5,
        3.8,
        [
            "Connects you to the customer.",
            "The customer’s phone timer starts.",
            "Greet: company name, your name, how can I help.",
            "Use Hold / Mute / Transfer as needed.",
            "Hang up when the conversation is finished.",
        ],
        16,
    )
    card(s, 6.85, 1.55, 6.0, 5.0, WHITE)
    head = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.85), Inches(1.55), Inches(6.0), Inches(0.7))
    head.fill.solid()
    head.fill.fore_color.rgb = RED
    head.line.fill.background()
    tb(s, 6.85, 1.68, 6.0, 0.5, [("DECLINE  (red)", True, WHITE, 20)],)
    bullets(
        s,
        7.1,
        2.5,
        5.5,
        3.8,
        [
            "Ends the customer’s call immediately.",
            "It does not send the call to the other agent.",
            "Use only if you cannot take the call at all (wrong headset, emergency).",
            "If you are already on a call, extra rings should not steal your live call.",
            "Prefer letting it ring if you simply missed it — do not Decline out of habit.",
        ],
        16,
    )
    add_notes(s, "This is the most important slide. Decline = caller dropped. Practice once so they feel the difference.")

    # 9 During call
    s = new()
    title_slide_header(s, "During the call")
    tools = [
        ("Hang up", "Ends the call for both sides. Complete ACW after."),
        ("Hold", "Customer waits. Tell them before you hold. Take them off hold when you return."),
        ("Mute", "Customer cannot hear you. Use if you need to cough or ask a colleague. Unmute before you speak."),
        ("Transfer", "Sends the customer to another available agent. Confirm the extension first."),
        ("Keypad", "Press digits if an IVR or confirmation code is needed."),
        ("Timer", "Shows talk time. The customer’s mobile also shows talk time after you Answer."),
    ]
    for i, (h, b) in enumerate(tools):
        col = i % 3
        row = i // 3
        x = 0.45 + col * 4.25
        y = 1.5 + row * 2.6
        card(s, x, y, 4.05, 2.35, WHITE)
        tb(s, x + 0.25, y + 0.25, 3.55, 0.45, [(h, True, NAVY, 20)])
        tb(s, x + 0.25, y + 0.8, 3.55, 1.3, [(b, False, MUTED, 15)])
    add_notes(s, "Live demo Hold and Mute. Transfer only if a second agent is Registered.")

    # 10 ACW
    s = new()
    title_slide_header(s, "After the call — wrap-up (ACW)", "This window opens when the call ends. Do not skip unless the call was a true misdial.")
    bullets(
        s,
        0.55,
        1.5,
        7.3,
        5.4,
        [
            "Disposition (required): Resolved, Follow-Up, Escalated, Completed Normally, or Invalid.",
            "Call reason (required): short phrase — billing, SIM, internet, complaint, info.",
            "Notes: what the customer needed and what you did. Write so a supervisor can understand later.",
            "Submit & Return Available — go back on duty.",
            "If you opened a ticket during the call, say so in the notes.",
            "Do not sit in wrap-up chatting. Other customers are waiting.",
        ],
        17,
    )
    card(s, 8.1, 1.55, 4.7, 5.0, CARD)
    tb(s, 8.35, 1.85, 4.25, 0.5, [("Good note example", True, NAVY, 16)])
    tb(
        s,
        8.35,
        2.5,
        4.25,
        3.7,
        [
            ("Caller asked why data stopped.", False, INK, 15),
            ("Checked package — expired yesterday.", False, INK, 15),
            ("Explained renewal. Customer will recharge today.", False, INK, 15),
            ("Disposition: Resolved.", False, INK, 15),
            ("", False, INK, 8),
            ("Bad note: “ok” or blank.", True, RED, 15),
        ],
    )
    add_notes(s, "Show the ACW modal. Have them submit one dummy wrap-up.")

    # 11 Outbound
    s = new()
    title_slide_header(s, "Making an outbound call")
    bullets(
        s,
        0.55,
        1.5,
        12.2,
        2.4,
        [
            "Open the phone panel. You must be Registered.",
            "Dial the mobile the way customers use it, then press Call.",
            "Wait for ring. Talk. Hang up. Complete ACW the same as inbound.",
        ],
        18,
    )
    card(s, 0.5, 4.05, 6.05, 2.55, WHITE)
    tb(s, 0.75, 4.25, 5.6, 0.4, [("From line 755  (Agent default)", True, NAVY, 16)])
    tb(s, 0.75, 4.8, 5.6, 1.5, [("Dial  0902xxxxxxx\nor  902xxxxxxx", False, INK, 20)])
    card(s, 6.8, 4.05, 6.05, 2.55, WHITE)
    tb(s, 7.05, 4.25, 5.6, 0.4, [("From line 756", True, NAVY, 16)])
    tb(s, 7.05, 4.8, 5.6, 1.5, [("Dial  7560902xxxxxxx\nor  756902xxxxxxx", False, INK, 20)])
    add_notes(s, "Customer sees CLI 755 or 756 depending on how they dialed. Callbacks should use the same line the customer called.")

    # 12 Two lines
    s = new()
    title_slide_header(s, "Two company numbers", "Customers may call either line. You handle both.")
    card(s, 0.5, 1.55, 6.05, 5.05, WHITE)
    tb(s, 0.8, 1.8, 5.5, 0.5, [("111 138 755", True, NAVY, 28)])
    tb(s, 0.8, 2.5, 5.5, 3.7, [("Inbound DID for line 1.\nShows in history as 251111138755.\nOutbound CLI when you dial 09…", False, MUTED, 18)])
    card(s, 6.8, 1.55, 6.05, 5.05, WHITE)
    tb(s, 7.1, 1.8, 5.5, 0.5, [("111 138 756", True, NAVY, 28)])
    tb(s, 7.1, 2.5, 5.5, 3.7, [("Inbound DID for line 2.\nShows in history as 251111138756.\nOutbound CLI when you prefix 756.", False, MUTED, 18)])
    add_notes(s, "History Destination 755/756 is the company line, not the agent. Agent column is 101/102.")

    # 13 Other screens
    s = new()
    title_slide_header(s, "Other screens you will use")
    items = [
        ("Call History", "Your recent answered and missed calls."),
        ("Recordings", "Play back a call if the customer disputes what was said. Use headset."),
        ("ACW History", "Wrap-ups you already submitted."),
        ("New Ticket", "Open a case when the issue cannot be finished on the phone."),
        ("Customer Lookup", "Search a number before or during a call."),
        ("Callbacks", "Numbers that need a return call. Dial, then mark completed."),
        ("Ahununu.com", "Reference site. Do not let it steal focus during a live call."),
        ("Phone Settings", "Only if a supervisor asks you to change them."),
    ]
    for i, (h, b) in enumerate(items):
        col = i % 4
        row = i // 4
        x = 0.4 + col * 3.2
        y = 1.5 + row * 2.7
        card(s, x, y, 3.05, 2.45, WHITE)
        tb(s, x + 0.18, y + 0.25, 2.7, 0.7, [(h, True, NAVY, 16)])
        tb(s, x + 0.18, y + 1.0, 2.7, 1.2, [(b, False, MUTED, 14)])
    add_notes(s, "Quick tour of the sidebar. Do not spend training time on supervisor screens.")

    # 14 Rules
    s = new()
    title_slide_header(s, "Do  /  Don’t")
    card(s, 0.45, 1.5, 6.1, 5.15, WHITE)
    tb(s, 0.7, 1.7, 5.6, 0.45, [("Do", True, GREEN, 22)])
    bullets(
        s,
        0.7,
        2.3,
        5.6,
        4.1,
        [
            "Keep Chrome on Registered + Available.",
            "Wear the headset before Answer.",
            "Greet, listen, confirm, close.",
            "Complete ACW after every real call.",
            "Ask the supervisor if audio is one-way.",
        ],
        16,
    )
    card(s, 6.8, 1.5, 6.1, 5.15, WHITE)
    tb(s, 7.05, 1.7, 5.6, 0.45, [("Don’t", True, RED, 22)])
    bullets(
        s,
        7.05,
        2.3,
        5.6,
        4.1,
        [
            "Don’t open two agent logins on one PC.",
            "Don’t use port 8088 if your URL is 8188.",
            "Don’t Decline just to stop the ring.",
            "Don’t refresh or close Chrome mid-call.",
            "Don’t leave Available and walk away (idle logout).",
        ],
        16,
    )
    add_notes(s, "Idle logout is configured by the supervisor. If they step away, they should go On Break / Logout.")

    # 15 Troubleshooting
    s = new()
    title_slide_header(s, "If something goes wrong")
    rows = [
        ("Not Registered", "Ctrl+F5. Allow microphone. Check headset. Tell the supervisor if it stays red."),
        ("Ring but no voice", "Confirm headset selected in Chrome. Mute off. Ask the customer to speak again. If still silent, hang up and tell the supervisor."),
        ("Cannot click Answer", "Microphone blocked. Padlock → Microphone → Allow, then reload."),
        ("Logged out suddenly", "Idle timeout or session expired. Log in again. Do not leave the page overnight."),
        ("Wrong number on outbound", "755 = dial 09….  756 = dial 75609…. Don’t mix them on a callback."),
        ("Call History looks odd", "Destination 755/756 is the company line. Agent 1/102 is you. Ignore random letters — that is the browser phone id."),
    ]
    for i, (h, b) in enumerate(rows):
        y = 1.42 + i * 0.9
        tb(s, 0.55, y, 3.3, 0.7, [(h, True, NAVY, 15)])
        tb(s, 4.0, y, 8.8, 0.8, [(b, False, INK, 14)])
    add_notes(s, "History letters like o8kqslls are WebRTC ids — do not read them to customers.")

    # 16 Practice
    s = new()
    title_slide_header(s, "Practice on the floor", "Do this with a trainer before you take live customers")
    checks = [
        "Log in and reach Registered (your extension).",
        "Set Available.",
        "Receive one inbound on 755. Answer. Two-way talk. Hang up. Submit ACW.",
        "Receive one inbound on 756. Same steps.",
        "Decline one test call and confirm the caller is dropped (not sent to the other agent).",
        "Place one outbound 09… and one outbound 75609….",
        "Hold 5 seconds, unmute, transfer if a second agent is free.",
        "Open a sample ticket. Find a number in Customer Lookup.",
        "Logout and Sign Out at the end of the drill.",
    ]
    bullets(s, 0.55, 1.5, 12.2, 5.5, checks, 17)
    add_notes(s, "Tick these off on paper. Do not skip Decline — they must understand it.")

    # 17 Recap
    s = new()
    title_slide_header(s, "Remember")
    recap = [
        ("Registered + Available", "You can take calls"),
        ("Answer", "You are speaking to the customer"),
        ("Decline", "The customer is gone"),
        ("Hang up → ACW", "Then Available again"),
        ("09… / 75609…", "Which company number you call from"),
        ("One Chrome tab", "Headset on, mic allowed"),
    ]
    for i, (h, b) in enumerate(recap):
        col = i % 3
        row = i // 3
        x = 0.45 + col * 4.25
        y = 1.55 + row * 2.55
        card(s, x, y, 4.05, 2.3, WHITE)
        tb(s, x + 0.25, y + 0.4, 3.55, 0.7, [(h, True, NAVY, 20)])
        tb(s, x + 0.25, y + 1.2, 3.55, 0.7, [(b, False, MUTED, 16)])
    add_notes(s, "Ask each agent to repeat Answer vs Decline in their own words.")

    # 18 Close
    s = new()
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY_DARK
    bg.line.fill.background()
    accent = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.18), prs.slide_height)
    accent.fill.solid()
    accent.fill.fore_color.rgb = GOLD
    accent.line.fill.background()
    tb(s, 0.7, 2.2, 12, 0.8, [("Questions?", True, WHITE, 44)])
    tb(
        s,
        0.7,
        3.2,
        12,
        1.8,
        [
            ("Ask your supervisor before you take the next live customer.", False, RGBColor(0xC5, 0xD4, 0xEA), 20),
            ("SkyKin Technologies  ·  Agent desk 101 / 102", False, GOLD, 16),
        ],
    )
    add_notes(s, "Collect headset serials / Chrome version if audio issues appear in week one.")

    total = len(slides)
    for i, sl in enumerate(slides, 1):
        if i not in (1, total):
            footer(sl, i, total)

    prs.save(str(OUT))
    print("wrote", OUT, "slides", total)


if __name__ == "__main__":
    build()
