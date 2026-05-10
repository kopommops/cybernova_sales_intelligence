from fastapi import HTTPException, status

ROLE_LEVEL: dict[str, int] = {
    "salesperson":      1,
    "sales_manager":    2,
    "systems_manager":  3,
}

VALID_ROLES = set(ROLE_LEVEL.keys())


def require_role(current_role: str, minimum_role: str) -> None:
    """
    Raise HTTP 403 if current_role does not meet the minimum required level.

    Usage (inside a router):
        require_role(current_user["role"], "sales_manager")
    """
    current_level = ROLE_LEVEL.get(current_role, 0)
    minimum_level = ROLE_LEVEL.get(minimum_role, 99)

    if current_level < minimum_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required role: '{minimum_role}' "
                   f"or above. Your role: '{current_role}'.",
        )


def is_authorised(current_role: str, minimum_role: str) -> bool:
    """
    Boolean version of require_role — useful for conditional UI rendering.
    """
    return ROLE_LEVEL.get(current_role, 0) >= ROLE_LEVEL.get(minimum_role, 99)