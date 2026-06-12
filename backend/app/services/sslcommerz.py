"""
SSLCommerz payment gateway service.

Sandbox API: https://sandbox.sslcommerz.com/gwprocess/v4/api.php
Live API:    https://securepay.sslcommerz.com/gwprocess/v4/api.php

In production set SSLCOMMERZ_SANDBOX=false and configure real store credentials.
IPN callbacks require a publicly accessible BACKEND_URL — for local sandbox
testing the browser-redirect flow (success/fail/cancel) works without a public URL.
"""
from __future__ import annotations

import httpx
import structlog
from fastapi import HTTPException, status

from app.config import get_settings

logger = structlog.get_logger(__name__)

_SANDBOX_INIT     = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
_LIVE_INIT        = "https://securepay.sslcommerz.com/gwprocess/v4/api.php"

_SANDBOX_VALIDATE = "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
_LIVE_VALIDATE    = "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"


def _init_url() -> str:
    return _SANDBOX_INIT if get_settings().SSLCOMMERZ_SANDBOX else _LIVE_INIT


def _validate_url() -> str:
    return _SANDBOX_VALIDATE if get_settings().SSLCOMMERZ_SANDBOX else _LIVE_VALIDATE


async def init_payment(
    *,
    tran_id: str,
    amount: float,
    plan: str,
    cus_name: str,
    cus_email: str,
    cus_phone: str,
) -> str:
    """
    Open a payment session with SSLCommerz.
    Returns the GatewayPageURL to redirect the browser to.
    """
    settings = get_settings()

    payload = {
        "store_id":          settings.SSLCOMMERZ_STORE_ID,
        "store_passwd":      settings.SSLCOMMERZ_STORE_PASSWORD,
        "total_amount":      str(amount),
        "currency":          "BDT",
        "tran_id":           tran_id,
        "success_url":       f"{settings.BACKEND_URL}/api/payments/success",
        "fail_url":          f"{settings.BACKEND_URL}/api/payments/fail",
        "cancel_url":        f"{settings.BACKEND_URL}/api/payments/cancel",
        "ipn_url":           f"{settings.BACKEND_URL}/api/payments/ipn",
        "cus_name":          cus_name,
        "cus_email":         cus_email,
        "cus_phone":         cus_phone,
        "cus_add1":          "Dhaka",
        "cus_city":          "Dhaka",
        "cus_country":       "Bangladesh",
        "product_name":      "হ্যালো এ্যাডভকেট প্রো",
        "product_category":  "SaaS",
        "product_profile":   "non-physical-goods",
        "shipping_method":   "NO",
        "num_of_item":       "1",
        "weight_of_items":   "0",
        "product_amount":    str(amount),
        "vat":               "0",
        "discount_amount":   "0",
        "convenience_fee":   "0",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(_init_url(), data=payload)
            resp.raise_for_status()
            data: dict = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("sslcommerz_init_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="পেমেন্ট গেটওয়ে সংযোগ ব্যর্থ হয়েছে। পুনরায় চেষ্টা করুন।",
            )

    if data.get("status") != "SUCCESS":
        logger.error("sslcommerz_session_rejected", failedreason=data.get("failedreason", ""))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="পেমেন্ট গেটওয়ে সেশন তৈরি হয়নি। পুনরায় চেষ্টা করুন।",
        )

    gateway_url: str = data.get("GatewayPageURL", "")
    if not gateway_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="পেমেন্ট URL পাওয়া যায়নি।",
        )

    return gateway_url


async def verify_payment(val_id: str) -> dict:
    """
    Validate a completed payment using the SSLCommerz validation API.
    Returns the full response dict; caller checks response["status"] == "VALID".
    """
    settings = get_settings()

    params = {
        "val_id":       val_id,
        "store_id":     settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
        "format":       "json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(_validate_url(), params=params)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("sslcommerz_verify_failed", val_id=val_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="পেমেন্ট যাচাই ব্যর্থ হয়েছে।",
            )
