"""Shared enums used across models and schemas."""
import enum


class UserTier(enum.Enum):
    FREE = "free"
    PAID = "paid"
