"""Guesthouse logout view.

Logs the user out of the session and redirects them to the public landing
page. A GET request also works (handy for a plain link) while POST is the
preferred method to guard against CSRF-initiated logouts from external sites.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log the user out and redirect to the landing page."""
    auth_logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("landing")
