from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http import JsonResponse

from tennants.models import Tenant, Payment, RentCharge, Issue


def health(request):
    return JsonResponse({
        "status": "ok"
    })

@login_required
def tenant_dashboard(request):
    tenant = Tenant.objects.filter(user=request.user).first()
    if tenant is None:
        return HttpResponseForbidden()

    payments = Payment.objects.filter(tenant=tenant).order_by("-paid_at")
    charges = RentCharge.objects.filter(tenant=tenant).order_by("-month")
    issues = Issue.objects.filter(tenant=tenant).order_by("-created_at")

    total_paid = sum(p.amount for p in payments)
    total_due = sum(c.amount_due for c in charges)

    context = {
        "tenant": tenant,
        "payments": payments,
        "charges": charges,
        "issues": issues,
        "balance": total_due - total_paid,
    }

    return render(request, "tenants/dashboard.html", context)


@login_required
def report_issue(request):
    tenant = Tenant.objects.filter(user=request.user).first()
    if tenant is None:
        return HttpResponseForbidden()

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")

        Issue.objects.create(
            tenant=tenant,
            title=title,
            description=description
        )

        return redirect("tenant_dashboard")

    return render(request, "tenantviews/report_issue.html", {"tenant": tenant})
