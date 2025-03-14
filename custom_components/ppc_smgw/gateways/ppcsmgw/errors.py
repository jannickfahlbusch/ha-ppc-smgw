"""Errors for the PPC-SMGW integration."""


class SessionCookieStillPresentError(Exception):
    """Exception raised when the session cookie is still present after deletion which prevents subsequent readings."""
