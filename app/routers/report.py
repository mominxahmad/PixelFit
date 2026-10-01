import io
import uuid
from datetime import datetime, timezone
from typing import Annotated
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .auth import current_user_auth
from ..models import MealPlan

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)


router = APIRouter(prefix="/report", tags=["Report"])


###  DEPENDENCIES
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


database_dependency = Annotated[Session, Depends(get_db)]

user_dependency = Annotated[dict, Depends(current_user_auth)]


###  PDF BUILDING HELPERS
def safe(text) -> str:
    """Escape &, <, > so LLM-generated text can't break ReportLab's Paragraph markup."""
    return escape(str(text))


def format_meals(meals: list, styles):
    flowables = []
    for i, meal in enumerate(meals, start=1):
        if not isinstance(meal, dict):
            flowables.append(Paragraph(f"<b>Meal {i}:</b> {safe(meal)}", styles["Normal"]))
            flowables.append(Spacer(1, 6))
            continue

        meal_name = meal.get("meal_name") or f"Meal {i}"
        dish = meal.get("name")
        title = f"{meal_name}: {dish}" if dish else meal_name
        flowables.append(Paragraph(f"<b>{safe(title)}</b>", styles["Heading4"]))

        items = meal.get("items", [])
        if isinstance(items, list):
            for item in items:
                flowables.append(Paragraph(f"&bull; {safe(item)}", styles["Normal"]))
        elif items:
            flowables.append(Paragraph(safe(items), styles["Normal"]))

        if "calories" in meal:
            flowables.append(Paragraph(f"<b>Calories:</b> {safe(meal['calories'])} kcal", styles["Normal"]))

        meal_macros = meal.get("macros")
        if isinstance(meal_macros, dict) and meal_macros:
            parts = [
                f"{safe(str(k).replace('_g', '').replace('_', ' ').title())}: {safe(v)}g"
                for k, v in meal_macros.items()
            ]
            flowables.append(Paragraph(f"<b>Macros:</b> {' | '.join(parts)}", styles["Normal"]))

        flowables.append(Spacer(1, 8))
    return flowables


def format_macros(macros: dict, styles):
    if not macros:
        return [Paragraph("No macro data available.", styles["Normal"])]
    data = [["Macro", "Value"]] + [
        [str(k).replace("_", " ").title(), str(v)] for k, v in macros.items()
    ]
    table = Table(data, colWidths=[2.5 * inch, 2.5 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [table]


def build_meal_plan_pdf(meal_plans: list[MealPlan]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Meal Plan Report", styles["Title"]))
    elements.append(Paragraph(
        datetime.now(timezone.utc).strftime("Generated %Y-%m-%d %H:%M UTC"),
        styles["Normal"]
    ))
    elements.append(Spacer(1, 20))

    for plan in meal_plans:
        elements.append(Paragraph(safe(plan.variant_label.replace("_", " ").title()), styles["Heading2"]))

        info_data = [
            ["Goal", plan.goal.value if plan.goal else "N/A"],
            ["Cuisine Preference", plan.cuisine_preference or "None specified"],
            ["Target Calories", str(plan.target_calories)],
        ]
        info_table = Table(info_data, colWidths=[2 * inch, 3.5 * inch])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 12))

        content = plan.plan_content or {}

        elements.append(Paragraph("Meals", styles["Heading3"]))
        elements.extend(format_meals(content.get("meals", []), styles))
        elements.append(Spacer(1, 8))

        elements.append(Paragraph("Macros", styles["Heading3"]))
        elements.extend(format_macros(content.get("macros", {}), styles))

        elements.append(Spacer(1, 24))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


"""===========================================ENDPOINTS==========================================="""
@router.get(path="/pdf/{generation_id}", status_code=status.HTTP_200_OK)
def get_meal_plan_report(db: database_dependency, user: user_dependency, generation_id: uuid.UUID):
    meal_plans = (
        db.query(MealPlan)
        # generation_id is stored as a String column, so compare as a string
        .filter(MealPlan.generation_id == str(generation_id), MealPlan.user_id == user.get("id"))
        .all()
    )
    if not meal_plans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    pdf_bytes = build_meal_plan_pdf(meal_plans)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="meal_plan_report_{generation_id}.pdf"'
        }
    )