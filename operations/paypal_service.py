
import re
import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import requests
from django.conf import settings


class PayPalAPIError(Exception):
    """Raised when a PayPal API request fails."""


def get_paypal_base_url():
    if settings.PAYPAL_MODE == "sandbox":
        return "https://api-m.sandbox.paypal.com"

    if settings.PAYPAL_MODE == "live":
        return "https://api-m.paypal.com"

    raise PayPalAPIError("Invalid PayPal configuration.")


def get_access_token():
    client_id = settings.PAYPAL_CLIENT_ID
    client_secret = settings.PAYPAL_CLIENT_SECRET

    if not client_id or not client_secret:
        raise PayPalAPIError(
            "PayPal credentials are not configured."
        )

    url = f"{get_paypal_base_url()}/v1/oauth2/token"

    try:
        response = requests.post(
            url,
            auth=(client_id, client_secret),
            headers={
                "Accept": "application/json",
                "Accept-Language": "en_US",
            },
            data={"grant_type": "client_credentials"},
            timeout=20,
        )

        response.raise_for_status()
        data = response.json()

        token = data.get("access_token")

        if not token:
            raise PayPalAPIError(
                "PayPal did not return an access token."
            )

        return token

    except requests.RequestException as exc:
        raise PayPalAPIError(
            "Could not authenticate with PayPal. "
            "Check your Sandbox credentials and connection."
        ) from exc

    except ValueError as exc:
        raise PayPalAPIError(
            "PayPal returned an invalid authentication response."
        ) from exc


def _paypal_request(method, endpoint, payload=None):
    token = get_access_token()

    url = f"{get_paypal_base_url()}{endpoint}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    except requests.HTTPError as exc:
        response = exc.response
        error_message = "PayPal rejected the request."

        if response is not None:
            try:
                error_data = response.json()
                error_message = (
                    error_data.get("message")
                    or error_data.get("name")
                    or error_message
                )
            except ValueError:
                pass

        raise PayPalAPIError(
            f"PayPal API error: {error_message}"
        ) from exc

    except requests.RequestException as exc:
        raise PayPalAPIError(
            "Could not communicate with PayPal. "
            "Check your internet connection."
        ) from exc

    except ValueError as exc:
        raise PayPalAPIError(
            "PayPal returned an invalid API response."
        ) from exc


def _validate_local_or_https_url(url):
    if not isinstance(url, str):
        raise PayPalAPIError("Invalid PayPal return URL.")

    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise PayPalAPIError("Invalid PayPal return URL.") from exc

    if parsed.scheme == "https" and parsed.netloc:
        return

    if (
        parsed.scheme == "http"
        and parsed.hostname in ("localhost", "127.0.0.1")
    ):
        return

    raise PayPalAPIError(
        "PayPal URLs must use HTTPS, or localhost during development."
    )


def create_paypal_order(amount, currency, return_url, cancel_url):
    try:
        amount = Decimal(str(amount)).quantize(
            Decimal("0.01")
        )
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PayPalAPIError("Invalid payment amount.") from exc

    if not amount.is_finite() or amount <= 0:
        raise PayPalAPIError(
            "Payment amount must be greater than zero."
        )

    if not isinstance(currency, str):
        raise PayPalAPIError("Invalid currency code.")

    currency = currency.upper()

    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise PayPalAPIError("Invalid currency code.")

    _validate_local_or_https_url(return_url)
    _validate_local_or_https_url(cancel_url)

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": str(uuid.uuid4()),
                "description": "AUVRION AI Agent Task Plan",
                "amount": {
                    "currency_code": currency,
                    "value": format(amount, ".2f"),
                },
            }
        ],
        "application_context": {
            "brand_name": "AUVRION",
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }

    result = _paypal_request(
        "POST",
        "/v2/checkout/orders",
        payload
    )

    order_id = result.get("id")

    if not order_id:
        raise PayPalAPIError(
            "PayPal created no identifiable order."
        )

    approval_url = None

    for link in result.get("links", []):
        if link.get("rel") in ("approve", "payer-action"):
            approval_url = link.get("href")
            break

    if not approval_url:
        raise PayPalAPIError(
            "PayPal did not return a buyer approval URL."
        )

    return {
        "order_id": order_id,
        "approval_url": approval_url,
        "status": result.get("status"),
    }


def capture_paypal_order(order_id):
    if (
        not isinstance(order_id, str)
        or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", order_id)
    ):
        raise PayPalAPIError("Invalid PayPal order ID.")

    return _paypal_request(
        "POST",
        f"/v2/checkout/orders/{order_id}/capture",
        payload={},
    )
