import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

def create_l2_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=HexColor('#0ea5e9'),
        spaceAfter=15
    )
    
    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=HexColor('#0284c7'),
        spaceBefore=10,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=HexColor('#1e293b'),
        spaceAfter=12
    )

    story = []
    
    # --- PAGE 1: SYSTEM OVERVIEW ---
    story.append(Paragraph("🛡️ GOVSHIELD SECURE SYSTEM OVERVIEW", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "Welcome to the GovShield Secure System Infrastructure Overview documentation. "
        "This manual covers all core hosting platforms, site structures, and physical server locations. "
        "GovShield is designed to provide fully isolated, air-gapped computing environments for sensitive municipal operations.",
        body_style
    ))
    story.append(Paragraph(
        "Our hardware nodes are divided across multiple facilities, with the primary operations hosted "
        "in the central civic data center. Standard physical access is restricted to credentialed IT personnel.",
        body_style
    ))
    story.append(Paragraph("FACILITY LOCATIONS:", h2_style))
    story.append(Paragraph(
        "• Facility Alpha: Main administration servers and public portal routing node.<br/>"
        "• Facility Beta: Cryptographic core storage and biometric gate controls.<br/>"
        "• Central Civic Facility: Server Room A and secure operations command room.",
        body_style
    ))
    
    # End Page 1
    story.append(PageBreak())
    
    # --- PAGE 2: OPERATING PARAMETERS (L2 CLEARANCE) ---
    story.append(Paragraph("🔒 FACILITY BETA: OPERATING PARAMETERS [L2 SECURITY CLEARANCE]", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "WARNING: The contents of this page are classified at Level 2 (Top Secret). Unauthorised extraction or "
        "viewing is strictly prohibited and subject to immediate administrative action.",
        body_style
    ))
    story.append(Paragraph("ENVIRONMENTAL CONTROLS:", h2_style))
    story.append(Paragraph(
        "To ensure maximum hardware lifespan and prevent thermal throttling of the cryptographic processing units, "
        "the temperature inside Facility Beta's main Server Room A must be maintained at exactly 19.5 degrees Celsius at all times. "
        "Any variance exceeding 1.5 degrees will trigger an automated climate warning to security teams.",
        body_style
    ))
    story.append(Paragraph("CRYPTOGRAPHIC ROTATIONS:", h2_style))
    story.append(Paragraph(
        "Core symmetric system keys (AES-GCM-256) are stored in hardware security modules (HSMs). "
        "These cryptographic keys must be manually rotated every 90 days. The manual rotation sequence requires "
        "two authorised L2 officers inputting their physical keycards simultaneously at the primary control desk.",
        body_style
    ))
    
    # End Page 2
    story.append(PageBreak())
    
    # --- PAGE 3: BIOMETRIC GATE PROTOCOLS (L2 CLEARANCE) ---
    story.append(Paragraph("🚨 EMERGENCY BIOMETRIC GATE OVERRIDES [L2 SECURITY CLEARANCE]", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "This page contains emergency procedures regarding biological boundary gates and security lockdowns. "
        "Only security officers of Level 2 clearance are authorized to execute manual overrides on the perimeter gates.",
        body_style
    ))
    story.append(Paragraph("BIOMETRIC OVERRIDE PROTOCOL:", h2_style))
    story.append(Paragraph(
        "In the event of a network outage or system lockup, the biometric gates at Facility Beta can be bypassed. "
        "To perform a manual override, insert the physical override key into the base of gate terminal B-1. "
        "Then, enter the master keycode sequence: '7-3-9-2-Star-Hash-9' on the physical keypad. "
        "This will release the electromagnetic lock and keep the gate open for exactly 45 seconds before re-engaging.",
        body_style
    ))
    
    doc.build(story)
    print(f"L2 PDF successfully created at: {filename}")

def create_l1_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=HexColor('#e11d48'),
        spaceAfter=15
    )
    
    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=HexColor('#be123c'),
        spaceBefore=10,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=HexColor('#1e293b'),
        spaceAfter=12
    )

    story = []
    
    # --- PAGE 1: OFFICE POLICIES & HOURS ---
    story.append(Paragraph("📂 GOVSHIELD ADMINISTRATIVE POLICIES [L1 CLEARANCE]", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "This document contains standard operating procedures and general office policies "
        "applicable to all GovShield personnel holding Level 1 security clearance or above.",
        body_style
    ))
    story.append(Paragraph("OFFICE HOURS:", h2_style))
    story.append(Paragraph(
        "Standard administrative working hours at all facilities are scheduled from 08:00 to 18:00 (8:00 AM to 6:00 PM), "
        "Monday through Friday. Flexible scheduling is allowed with department head approval, but core operating hours "
        "of 10:00 to 15:00 must be observed by all active staff.",
        body_style
    ))
    story.append(Paragraph("BADGE GUIDELINES:", h2_style))
    story.append(Paragraph(
        "Security identification badges must be worn visible and positioned above the waist at all times "
        "while inside any GovShield municipal building. Visitors must be escorted by credentialed personnel "
        "and wear a temporary red visitor badge.",
        body_style
    ))
    
    # End Page 1
    story.append(PageBreak())
    
    # --- PAGE 2: IT SUPPORT & NETWORK FAQS ---
    story.append(Paragraph("🔌 IT SUPPORT & NETWORK CONFIGURATION [L1 CLEARANCE]", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("SECURE WIFI ACCESS:", h2_style))
    story.append(Paragraph(
        "Level 1 personnel can connect their authorized company-issued laptops to the secure internal wireless network. "
        "The network SSID is 'GovSecure-Net' and uses WPA3-Enterprise authentication. "
        "Use your standard system login credentials and select the primary root security certificate when prompting.",
        body_style
    ))
    story.append(Paragraph("HARDWARE REPLACEMENTS:", h2_style))
    story.append(Paragraph(
        "If you encounter hardware issues or require peripheral replacements (keyboards, mice, monitors), "
        "please submit a support ticket via the internal IT portal. Routine desktop hardware requests are processed "
        "within 24 hours. For emergency replacement requests, contact the IT service desk directly at extension 404.",
        body_style
    ))
    
    doc.build(story)
    print(f"L1 PDF successfully created at: {filename}")

if __name__ == "__main__":
    os.makedirs("./data", exist_ok=True)
    create_l2_pdf("./data/L2_internal_procedures.pdf")
    create_l1_pdf("./data/L1_office_policies.pdf")
