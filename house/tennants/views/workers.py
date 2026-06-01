from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from tennants.models import Issue, Worker, MaintenanceBid, Expense, FlatBuilding
from tennants.forms import WorkerRegistrationForm, MaintenanceBidForm
from decimal import Decimal


def worker_login_view(request):
    """Alternative login page for workers"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("worker_dashboard")
        messages.error(request, "Invalid username or password.")
    return render(request, "workers/login.html")


def worker_register(request):
    """Worker self-registration"""
    if request.method == "POST":
        form = WorkerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password1"]
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
            messages.success(
                request,
                "Registration successful! Your profile is pending admin approval. "
                "You can still browse and bid on available jobs."
            )
            return redirect("worker_dashboard")
    else:
        form = WorkerRegistrationForm()
    return render(request, "workers/register.html", {"form": form})


@login_required
def worker_dashboard(request):
    """Worker dashboard - show open issues and their bids"""
    try:
        worker = request.user.worker_profile
    except Worker.DoesNotExist:
        messages.error(request, "Worker profile not found.")
        return redirect("login")

    open_issues = Issue.objects.filter(
        status__in=["pending", "approved"]
    ).select_related("tenant", "tenant__house", "tenant__house__flat_building").order_by("-created_at")

    my_bids = MaintenanceBid.objects.filter(worker=worker).select_related(
        "issue", "issue__tenant", "issue__tenant__house"
    ).order_by("-submitted_at")

    pending_bids = my_bids.filter(status="pending").count()
    accepted_bids = my_bids.filter(status="accepted").count()

    context = {
        "open_issues": open_issues,
        "my_bids": my_bids,
        "pending_bids": pending_bids,
        "accepted_bids": accepted_bids,
        "total_bids": my_bids.count(),
        "worker": worker,
    }
    return render(request, "workers/dashboard.html", context)


@login_required
def worker_place_bid(request, issue_id):
    """Worker places a bid on an issue"""
    try:
        worker = request.user.worker_profile
    except Worker.DoesNotExist:
        messages.error(request, "Worker profile not found.")
        return redirect("login")

    issue = get_object_or_404(Issue, pk=issue_id, status__in=["pending", "approved"])
    
    if request.method == "POST":
        form = MaintenanceBidForm(request.POST)
        if form.is_valid():
            bid = form.save(commit=False)
            bid.issue = issue
            bid.worker = worker
            bid.save()
            messages.success(request, f"Your bid of M{bid.amount:,.2f} has been submitted for review!")
            return redirect("worker_my_bids")
    else:
        form = MaintenanceBidForm()
    
    context = {
        "form": form,
        "issue": issue,
    }
    return render(request, "workers/place_bid.html", context)


@login_required
def worker_my_bids(request):
    """View all bids by this worker"""
    try:
        worker = request.user.worker_profile
    except Worker.DoesNotExist:
        messages.error(request, "Worker profile not found.")
        return redirect("login")
    
    bids = MaintenanceBid.objects.filter(worker=worker).select_related(
        "issue", "issue__tenant", "issue__tenant__house"
    ).order_by("-submitted_at")
    
    context = {
        "bids": bids,
    }
    return render(request, "workers/my_bids.html", context)


@login_required
def worker_withdraw_bid(request, bid_id):
    """Worker withdraws a pending bid"""
    try:
        worker = request.user.worker_profile
    except Worker.DoesNotExist:
        messages.error(request, "Worker profile not found.")
        return redirect("login")
    
    bid = get_object_or_404(MaintenanceBid, pk=bid_id, worker=worker, status="pending")
    bid.status = "withdrawn"
    bid.decided_at = timezone.now()
    bid.save(update_fields=["status", "decided_at"])
    
    messages.success(request, "Bid withdrawn successfully.")
    return redirect("worker_my_bids")


@login_required
def worker_profile(request):
    """View/edit worker profile"""
    try:
        worker = request.user.worker_profile
    except Worker.DoesNotExist:
        messages.error(request, "Worker profile not found.")
        return redirect("login")
    
    if request.method == "POST":
        from tennants.forms import WorkerProfileForm
        form = WorkerProfileForm(request.POST, instance=worker)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("worker_profile")
    else:
        from tennants.forms import WorkerProfileForm
        form = WorkerProfileForm(instance=worker)
    
    context = {
        "form": form,
        "worker": worker,
    }
    return render(request, "workers/profile.html", context)