from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from tennants.models import Tenant, Payment, RentCharge, Issue


@login_required
def tenant_dashboard(request):
    if request.user.role != "tenant":
        return HttpResponseForbidden()

    tenant = Tenant.objects.get(user=request.user)

    payments = Payment.objects.filter(tenant=tenant).order_by("-date")
    charges = RentCharge.objects.filter(tenant=tenant).order_by("-month")
    issues = Issue.objects.filter(tenant=tenant).order_by("-created_at")

    total_paid = sum(p.amount for p in payments)
    total_due = sum(c.amount for c in charges)

    context = {
        "tenant": tenant,
        "payments": payments,
        "charges": charges,
        "issues": issues,
        "balance": total_due - total_paid,
    }

    return render(request, "tenant/dashboard.html", context)


@login_required
def report_issue(request):
    if request.user.role != "tenant":
        return HttpResponseForbidden()

    tenant = Tenant.objects.get(user=request.user)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")

        Issue.objects.create(
            tenant=tenant,
            title=title,
            description=description
        )

        return redirect("tenant_dashboard")

    return render(request, "tenant/report_issue.html")