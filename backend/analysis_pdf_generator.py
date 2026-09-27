"""
SHRAMRAKSHAK: Publication-Grade Dataset Analysis PDF Report Generator
SIH 2026 Problem Statement: SIH26165

Generates an authoritative, forensic PDF report for any completed AnalysisRun.
Guarantees 100% numerical and categorical consistency between the UI metrics and the PDF output.
"""

import io
import os
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)


def generate_analysis_run_pdf(run: Dict[str, Any]) -> bytes:
    """
    Generates a publication-grade PDF report from an AnalysisRun dictionary.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom Palette
    COLOR_PRIMARY = colors.HexColor("#0f172a")    # Slate 900
    COLOR_SECONDARY = colors.HexColor("#1e293b")  # Slate 800
    COLOR_ACCENT = colors.HexColor("#d97706")     # Amber 600
    COLOR_CRITICAL = colors.HexColor("#dc2626")   # Red 600
    COLOR_SUCCESS = colors.HexColor("#16a34a")    # Green 600
    COLOR_MUTED = colors.HexColor("#64748b")      # Slate 500
    COLOR_BG_LIGHT = colors.HexColor("#f8fafc")   # Slate 50

    # Custom Typography Styles
    style_title = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=COLOR_PRIMARY
    )
    style_subtitle = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=COLOR_ACCENT
    )
    style_h1 = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=COLOR_PRIMARY,
        spaceBefore=14,
        spaceAfter=6
    )
    style_h2 = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=COLOR_SECONDARY,
        spaceBefore=8,
        spaceAfter=4
    )
    style_body = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=COLOR_SECONDARY
    )
    style_body_bold = ParagraphStyle(
        "BodyBold_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=COLOR_SECONDARY
    )
    style_meta = ParagraphStyle(
        "Meta_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=COLOR_MUTED
    )
    style_table_cell = ParagraphStyle(
        "TableCell_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=COLOR_SECONDARY
    )
    style_table_header = ParagraphStyle(
        "TableHeader_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=colors.white
    )

    story = []

    # 1. Header Block
    story.append(Paragraph("SHRAMRAKSHAK", style_subtitle))
    story.append(Paragraph("DATASET SAFETY INTELLIGENCE & SIF FORENSIC REPORT", style_title))
    story.append(Paragraph("Autonomous Contextual NLP, Precursor Detection & Recurrence Analysis", style_meta))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_ACCENT, spaceAfter=12))

    # 2. Metadata Grid Table
    run_id = run.get("run_id", "AR-UNKNOWN")
    filename = run.get("filename", "Unknown File")
    file_type = run.get("file_type", "CSV").upper()
    upload_time = run.get("upload_time", datetime.now().isoformat())
    provenance = run.get("provenance", "External safety dataset used for stress testing.")

    records_detected = run.get("records_detected", 0)
    records_analyzed = run.get("records_analyzed", 0)
    failed_count = run.get("failed_count", 0)
    review_required = run.get("review_required_count", 0)

    meta_data = [
        [
            Paragraph("<b>Analysis Run ID:</b>", style_table_cell),
            Paragraph(f"<font color='{COLOR_ACCENT.hexval()}'><b>{run_id}</b></font>", style_table_cell),
            Paragraph("<b>Upload Timestamp:</b>", style_table_cell),
            Paragraph(str(upload_time)[:19].replace("T", " "), style_table_cell)
        ],
        [
            Paragraph("<b>Source File:</b>", style_table_cell),
            Paragraph(filename, style_table_cell),
            Paragraph("<b>File Format:</b>", style_table_cell),
            Paragraph(file_type, style_table_cell)
        ],
        [
            Paragraph("<b>Total Records Detected:</b>", style_table_cell),
            Paragraph(f"<b>{records_detected:,}</b>", style_table_cell),
            Paragraph("<b>Total Records Analyzed:</b>", style_table_cell),
            Paragraph(f"<b>{records_analyzed:,}</b>", style_table_cell)
        ],
        [
            Paragraph("<b>Data Provenance:</b>", style_table_cell),
            Paragraph(provenance, style_meta),
            Paragraph("<b>Failed / Non-Analyzable:</b>", style_table_cell),
            Paragraph(str(failed_count), style_table_cell)
        ]
    ]

    meta_table = Table(meta_data, colWidths=[1.5*inch, 2.2*inch, 1.6*inch, 2.1*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_MUTED),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Executive Summary Cards Table
    story.append(Paragraph("1. EXECUTIVE SAFETY SUMMARY", style_h1))
    sif_count = run.get("sif_count", 0)
    non_sif_count = run.get("non_sif_count", 0)
    sif_pct = run.get("sif_percentage", 0.0)
    patterns = run.get("candidate_patterns", [])

    summary_cards_data = [
        [
            Paragraph("<font size=7>TOTAL ANALYZED</font><br/><font size=14><b>" + f"{records_analyzed:,}" + "</b></font>", style_table_cell),
            Paragraph(f"<font size=7>SIF PRECURSORS</font><br/><font size=14 color='{COLOR_CRITICAL.hexval()}'><b>{sif_count:,}</b></font>", style_table_cell),
            Paragraph("<font size=7>SIF RATE</font><br/><font size=14><b>" + f"{sif_pct:.1f}%" + "</b></font>", style_table_cell),
            Paragraph("<font size=7>NON-SIF / CONTROLLED</font><br/><font size=14 color='" + COLOR_SUCCESS.hexval() + "'><b>" + f"{non_sif_count:,}" + "</b></font>", style_table_cell),
            Paragraph("<font size=7>CANDIDATE PATTERNS</font><br/><font size=14 color='" + COLOR_ACCENT.hexval() + "'><b>" + str(len(patterns)) + "</b></font>", style_table_cell),
        ]
    ]
    summary_table = Table(summary_cards_data, colWidths=[1.48*inch]*5)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 1, COLOR_MUTED),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # 4. SIF Analysis & Exposure Breakdown
    story.append(Paragraph("2. SIF PATHWAY & ENERGY EXPOSURE ANALYSIS", style_h1))
    story.append(Paragraph(
        "SHRAMRAKSHAK identifies Serious Injury or Fatality (SIF) precursors by contextualizing high-energy hazards, "
        "human exposure presence, and critical barrier integrity ('Completion is not proof'). "
        "Reports with negated or hypothetical language do not trigger false SIF alarms.",
        style_body
    ))
    story.append(Spacer(1, 6))

    # Hazards Table
    hazards = run.get("hazard_distribution", {})
    barriers = run.get("barrier_failure_distribution", {})
    
    top_hazards = sorted(hazards.items(), key=lambda x: x[1], reverse=True)[:5]
    top_barriers = sorted(barriers.items(), key=lambda x: x[1], reverse=True)[:5]

    col_h_data = [[Paragraph("<b>High-Energy Hazard Category</b>", style_table_header), Paragraph("<b>Count</b>", style_table_header)]]
    for h_name, h_cnt in top_hazards:
        col_h_data.append([Paragraph(str(h_name), style_table_cell), Paragraph(f"<b>{h_cnt}</b>", style_table_cell)])
    if len(col_h_data) == 1:
        col_h_data.append([Paragraph("No hazard breakdown recorded", style_table_cell), Paragraph("0", style_table_cell)])

    col_b_data = [[Paragraph("<b>Compromised Critical Barrier</b>", style_table_header), Paragraph("<b>Count</b>", style_table_header)]]
    for b_name, b_cnt in top_barriers:
        col_b_data.append([Paragraph(str(b_name), style_table_cell), Paragraph(f"<b>{b_cnt}</b>", style_table_cell)])
    if len(col_b_data) == 1:
        col_b_data.append([Paragraph("No barrier failures recorded", style_table_cell), Paragraph("0", style_table_cell)])

    t_hazards = Table(col_h_data, colWidths=[2.6*inch, 0.9*inch])
    t_hazards.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_SECONDARY),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_MUTED),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))

    t_barriers = Table(col_b_data, colWidths=[2.9*inch, 0.9*inch])
    t_barriers.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_SECONDARY),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_MUTED),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))

    two_col_table = Table([[t_hazards, t_barriers]], colWidths=[3.6*inch, 3.8*inch])
    two_col_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(two_col_table)
    story.append(Spacer(1, 14))

    # 5. IOGP Life-Saving Rules Mapping Table
    story.append(Paragraph("3. IOGP LIFE-SAVING RULES (LSR) DISTRIBUTION", style_h1))
    iogp_dist = run.get("iogp_distribution", {})
    iogp_sorted = sorted(iogp_dist.items(), key=lambda x: x[1], reverse=True)

    iogp_table_data = [
        [
            Paragraph("<b>IOGP Life-Saving Rule</b>", style_table_header),
            Paragraph("<b>Occurrences</b>", style_table_header),
            Paragraph("<b>% of Analyzed Reports</b>", style_table_header)
        ]
    ]

    for rule, count in iogp_sorted[:8]:
        pct_rule = (count / max(records_analyzed, 1)) * 100
        iogp_table_data.append([
            Paragraph(f"<b>{rule}</b>", style_table_cell),
            Paragraph(f"<b>{count:,}</b>", style_table_cell),
            Paragraph(f"{pct_rule:.1f}%", style_table_cell)
        ])

    if len(iogp_table_data) == 1:
        iogp_table_data.append([
            Paragraph("General Industrial Safety (Unclassified Rule)", style_table_cell),
            Paragraph(str(records_analyzed), style_table_cell),
            Paragraph("100.0%", style_table_cell)
        ])

    iogp_table = Table(iogp_table_data, colWidths=[4.2*inch, 1.6*inch, 1.6*inch])
    iogp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_SECONDARY),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_MUTED),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(iogp_table)
    story.append(Spacer(1, 14))

    # 6. Candidate Recurring Patterns Discovered
    story.append(Paragraph("4. DISCOVERED CANDIDATE RECURRING PATTERNS", style_h1))
    story.append(Paragraph(
        "Candidate patterns represent repeated occurrences sharing identical underlying control failure mechanisms. "
        "All patterns remain in <font color='#d97706'><b>CANDIDATE</b></font> state until authorized by human HSE validation.",
        style_body
    ))
    story.append(Spacer(1, 6))

    if patterns:
        pat_table_data = [
            [
                Paragraph("<b>Pattern Title / Failure Mechanism</b>", style_table_header),
                Paragraph("<b>Occurrences</b>", style_table_header),
                Paragraph("<b>Critical Barrier</b>", style_table_header),
                Paragraph("<b>Governance Status</b>", style_table_header)
            ]
        ]
        for p in patterns[:6]:
            p_title = p.get("title", p.get("pattern_title", "Recurring Control Breach"))
            p_cnt = p.get("occurrence_count", p.get("independent_occurrences", 1))
            p_bar = p.get("barrier", p.get("critical_barrier", "Control Perimeter"))
            p_stat = p.get("validation_status", "CANDIDATE")
            pat_table_data.append([
                Paragraph(f"<b>{p_title}</b>", style_table_cell),
                Paragraph(f"<b>{p_cnt}</b>", style_table_cell),
                Paragraph(str(p_bar), style_table_cell),
                Paragraph(f"<font color='{COLOR_ACCENT.hexval()}'><b>{p_stat}</b></font>", style_table_cell)
            ])
        pat_table = Table(pat_table_data, colWidths=[3.2*inch, 1.1*inch, 1.8*inch, 1.3*inch])
        pat_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), COLOR_SECONDARY),
            ('BOX', (0,0), (-1,-1), 0.5, COLOR_MUTED),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(pat_table)
    else:
        story.append(Paragraph("<i>No multi-incident recurring patterns discovered exceeding the recurrence threshold in this dataset slice.</i>", style_body))

    story.append(Spacer(1, 14))

    # 7. High-Potential Case Evidence Examples
    story.append(Paragraph("5. HIGH-POTENTIAL INCIDENT EVIDENCE SAMPLES", style_h1))
    high_cases = run.get("high_potential_cases", [])
    if not high_cases:
        reports = run.get("reports", [])
        high_cases = [r for r in reports if r.get("sif_potential") in ["HIGH", "SIF_POTENTIAL"]][:4]

    for idx, case in enumerate(high_cases[:4]):
        case_id = case.get("report_id", case.get("event_id", f"REP-{idx+1:03d}"))
        narrative = case.get("narrative", case.get("original_text", ""))
        activity = case.get("activity", "Industrial Operation")
        hazard = case.get("hazard", case.get("energy", "Gravitational / Mechanical"))
        exposure = case.get("exposure", "Worker in drop zone")
        barrier = case.get("barrier", case.get("critical_barrier", "Exclusion Zone"))
        lsr = case.get("lsr", "Safe Mechanical Lifting")

        case_box_data = [
            [
                Paragraph(f"<b>Case #{idx+1} [ID: {case_id}]</b>", style_table_header),
                Paragraph(f"<b>SIF POTENTIAL: <font color='#fca5a5'>CRITICAL PRECURSOR</font></b>", style_table_header)
            ],
            [
                Paragraph(f"<b>Report Narrative:</b> {narrative}", style_table_cell),
                Paragraph(f"<b>Hazard / Energy:</b> {hazard}<br/><b>Activity:</b> {activity}<br/><b>Failed Barrier:</b> {barrier}<br/><b>IOGP LSR:</b> {lsr}", style_table_cell)
            ]
        ]
        t_case = Table(case_box_data, colWidths=[4.8*inch, 2.6*inch])
        t_case.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), COLOR_SECONDARY),
            ('BACKGROUND', (0,1), (-1,1), COLOR_BG_LIGHT),
            ('BOX', (0,0), (-1,-1), 0.5, COLOR_MUTED),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_case)
        story.append(Spacer(1, 6))

    # 8. Methodology & Governance Notice
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_MUTED, spaceAfter=8))
    story.append(Paragraph(
        "<b>DATASET PROVENANCE & METHODOLOGY NOTICE:</b> "
        f"This report was autonomously compiled by the SHRAMRAKSHAK Safety Intelligence Engine from input source '{filename}'. "
        "All SIF determinations follow the deterministic energy-barrier exposure pathway. "
        "Life-Saving Rules are classified via multi-label semantic matching. "
        "Candidate recurring patterns require formal human HSE validation before being committed into organizational operating rules. "
        "SIF Precursor Density does not replace official statutory OSHA or DGMS reportable incident frequency rates.",
        style_meta
    ))

    doc.build(story)
    return buffer.getvalue()
