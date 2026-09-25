"""
humana/app/api/customers.py
Customer (tenant) management endpoints.

GET    /customers             — list all
POST   /customers/            — create
GET    /customers/{id}        — get one
PUT    /customers/{id}        — update
DELETE /customers/{id}        — hard delete
POST   /customers/{id}/toggle — activate / pause
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.customer import Customer
from app.models.schemas import CustomerCreate, CustomerResponse, CustomerUpdate

log = get_logger(__name__)
router = APIRouter(prefix="/customers", tags=["Customers"])


# ── helpers ───────────────────────────────────────────────────────────────────
def _initials(name: str) -> str:
    parts = (name or "").split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return (name or "?")[0].upper()


async def _get_or_404(db: AsyncSession, customer_id: str) -> Customer:
    c = await db.get(Customer, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c


# ── LIST ──────────────────────────────────────────────────────────────────────
@router.get("", response_model=List[CustomerResponse])
async def list_customers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).order_by(Customer.created_at.desc()))
    return result.scalars().all()


# ── CREATE ────────────────────────────────────────────────────────────────────
@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(body: CustomerCreate, db: AsyncSession = Depends(get_db)):
    if body.owner_name:
        initials = _initials(body.owner_name)
    else:
        initials = body.business_name[0].upper()

    customer = Customer(
        business_name=body.business_name,
        business_url=body.business_url,
        owner_name=body.owner_name,
        owner_email=body.owner_email,
        owner_initials=initials,
        industry=body.industry,
        plan=body.plan,
        avatar_name=body.avatar_name,
        primary_color=body.primary_color,
        welcome_message=body.welcome_message,
        allowed_domains=body.allowed_domains or [],
        llm_provider=body.llm_provider,
        llm_model=body.llm_model,
    )
    db.add(customer)
    await db.flush()
    log.info("customer_created", id=customer.id, name=customer.business_name)
    return customer


# ── GET ONE ───────────────────────────────────────────────────────────────────
@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    return await _get_or_404(db, customer_id)


# ── UPDATE ────────────────────────────────────────────────────────────────────
@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str, body: CustomerUpdate, db: AsyncSession = Depends(get_db)
):
    c = await _get_or_404(db, customer_id)
    update_data = body.model_dump(exclude_unset=True)
    if "owner_name" in update_data and update_data["owner_name"]:
        update_data["owner_initials"] = _initials(update_data["owner_name"])
    for k, v in update_data.items():
        setattr(c, k, v)
    log.info("customer_updated", id=customer_id)
    return c


# ── DELETE ────────────────────────────────────────────────────────────────────
@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    c = await _get_or_404(db, customer_id)
    await db.delete(c)
    log.info("customer_deleted", id=customer_id)


# ── TOGGLE STATUS ─────────────────────────────────────────────────────────────
@router.post("/{customer_id}/toggle", response_model=CustomerResponse)
async def toggle_customer_status(
    customer_id: str, db: AsyncSession = Depends(get_db)
):
    c = await _get_or_404(db, customer_id)
    c.status = "paused" if c.status == "active" else "active"
    log.info("customer_toggled", id=customer_id, new_status=c.status)
    return c
