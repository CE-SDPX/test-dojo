"""Error codes, HTTP statuses and messages — docs/design/api.md sections 3-4."""
from __future__ import annotations

from flask import jsonify

# code -> (http_status, message)
CATALOG = {
    "VALIDATION_ERROR": (400, "One or more fields are invalid."),
    "INVALID_JSON": (400, "Request body must be valid JSON."),
    "INVALID_CURRENT_PASSWORD": (400, "Current password is incorrect."),
    "UNAUTHENTICATED": (401, "Authentication is required."),
    "INVALID_CREDENTIALS": (401, "Invalid username or password."),
    "FORBIDDEN": (403, "You do not have permission to perform this action."),
    "ACCOUNT_DISABLED": (403, "Your account has been locked by an administrator."),
    "PASSWORD_CHANGE_REQUIRED": (403, "You must change your password before continuing."),
    "REVIEW_NOT_ALLOWED": (403, "You can review a product only after receiving it."),
    "NOT_FOUND": (404, "The requested resource was not found."),
    "METHOD_NOT_ALLOWED": (405, "Method not allowed."),
    "USERNAME_TAKEN": (409, "This username is already taken."),
    "QUANTITY_LIMIT": (409, "You can add at most 10 of each product."),
    "CART_LINE_LIMIT": (409, "Your cart can hold at most 20 different products."),
    "INSUFFICIENT_STOCK": (409, "This product is out of stock."),
    "CART_EMPTY": (409, "Your cart is empty."),
    "COUPON_INVALID": (409, "This coupon code is not valid."),
    "INVALID_TRANSITION": (409, "This order cannot be changed from its current status."),
    "RETURN_WINDOW_CLOSED": (409, "The 7-day return period has ended."),
    "ADDRESS_LIMIT": (409, "You can save at most 5 addresses."),
    "ALREADY_IN_WISHLIST": (409, "This product is already in your wishlist."),
    "WISHLIST_LIMIT": (409, "Your wishlist can hold at most 50 products."),
    "REVIEW_EXISTS": (409, "You have already reviewed this product."),
    "STOCK_NEGATIVE": (409, "Stock cannot be negative."),
    "SKU_TAKEN": (409, "This SKU is already in use."),
    "COUPON_CODE_TAKEN": (409, "This coupon code is already in use."),
    "ACCOUNT_ALREADY_LOCKED": (409, "This account is already locked."),
    "ACCOUNT_NOT_LOCKED": (409, "This account is not locked."),
    "SELF_LOCK_FORBIDDEN": (409, "You cannot lock your own account."),
    "LAST_ADMIN": (409, "At least one unlocked administrator must remain."),
    "JOB_ALREADY_RUNNING": (409, "This job is already running."),
    "ACCOUNT_LOCKED": (423, "Your account is temporarily locked. Please try again in {n} minute(s)."),
    "INTERNAL_ERROR": (500, "An unexpected error occurred."),
}


class ApiError(Exception):
    def __init__(self, code, message=None, details=None, reason=None, fmt=None):
        http_status, default_message = CATALOG[code]
        self.http_status = http_status
        self.code = code
        msg = message or default_message
        if fmt:
            msg = msg.format(**fmt)
        self.message = msg
        self.details = details
        self.reason = reason
        super().__init__(self.message)

    def to_response(self):
        body = {"error": {"code": self.code, "message": self.message}}
        if self.details:
            body["error"]["details"] = self.details
        if self.reason:
            body["error"]["reason"] = self.reason
        resp = jsonify(body)
        resp.status_code = self.http_status
        return resp


def validation_error(details):
    return ApiError("VALIDATION_ERROR", details=details)


def not_found():
    return ApiError("NOT_FOUND")


def forbidden():
    return ApiError("FORBIDDEN")


def unauthenticated():
    return ApiError("UNAUTHENTICATED")


def conflict(code, **kwargs):
    return ApiError(code, **kwargs)


# Field-level validation messages — docs/design/api.md section 4
FIELD_MESSAGES = {
    "required": "This field is required.",
    "username": "Username must be 4 to 20 characters and contain only letters, digits and underscores.",
    "password": "Password must be 8 to 20 characters with at least one letter and one digit, and no spaces.",
    "new_password_same": "New password must be different from the current password.",
    "display_name": "Display name must be 2 to 50 characters.",
    "birthdate_format": "Enter a valid date in the format YYYY-MM-DD.",
    "birthdate_age": "You must be at least 18 years old to register.",
    "phone": "Phone number must be 10 digits starting with 0.",
    "label": "Label must be 1 to 30 characters.",
    "recipient_name": "Recipient name must be 2 to 50 characters.",
    "line1": "Address line 1 must be 5 to 100 characters.",
    "line2": "Address line 2 must be at most 100 characters.",
    "province": "Province must be 2 to 50 characters.",
    "postal_code": "Postal code must be 5 digits.",
    "whole_number": "This field must be a whole number.",
    "quantity": "Quantity must be a whole number from 1 to 10.",
    "rating": "Rating must be a whole number from 1 to 5.",
    "comment": "Comment must be at most 500 characters.",
    "q": "Search text must be at most 100 characters.",
    "category": "Category must be one of: Drinkware, Apparel, Stationery, Electronics, Home.",
    "price_format": "Price must be a number with at most 2 decimal places.",
    "price_range": "Minimum price must not be greater than maximum price.",
    "sort": "Sort must be one of: name_asc, name_desc, price_asc, price_desc.",
    "page": "Page must be a whole number of 1 or more.",
    "page_size": "Page size must be a whole number from 1 to 50.",
    "limit": "Limit must be a whole number from 1 to 20.",
    "status": "Status is not valid.",
    "coupon_code": "Coupon code must be 4 to 20 letters or digits.",
    "sku": "SKU must be 3 to 20 characters using A-Z, 0-9 and hyphens.",
    "name": "Name must be 2 to 100 characters.",
    "description": "Description must be at most 1000 characters.",
    "amount_default": "Amount must be between 0.01 and 99999.99.",
    "amount_min_spend": "Amount must be between 0.00 and 99999.99.",
    "percent_off": "Percent must be a whole number from 1 to 100.",
    "per_user_limit": "Limit per user must be a whole number from 1 to 99.",
    "total_limit": "Total limit must be a whole number of 1 or more.",
    "type": "Type must be PERCENT or FIXED.",
    "datetime_minute": "Enter a date and time in the format YYYY-MM-DDTHH:mm+07:00.",
    "expires_before_starts": "Expiry must not be before the start.",
    "range_invalid": "The time range is not valid.",
    "date_format": "Enter a valid date in the format YYYY-MM-DD.",
    "date_range_order": "Start date must not be after end date.",
    "date_range_too_long": "The date range must not exceed 366 days.",
    "delta": "Quantity change must be a non-zero whole number up to 100000.",
    "delta_receive": "Received stock must be a positive number.",
    "delta_damage": "Damaged stock must be a negative number.",
    "reason": "Reason must be one of: RECEIVE, DAMAGE, CORRECTION.",
    "role": "Role must be one of: customer, staff, manager, admin.",
    "method": "Payment method must be CARD or PROMPTPAY.",
    "active": "Active must be true or false.",
    "image_format": "Image must be a JPEG file (.jpg).",
    "image_size": "Image must be at most 2 MB.",
    "invalid": "This field is invalid.",
}


def field_error(field, key):
    return {"field": field, "message": FIELD_MESSAGES[key]}
