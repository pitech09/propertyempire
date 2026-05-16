from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http import JsonResponse

from tennants.models import Tenant, Payment, RentCharge, Issue


def health(request):
    return JsonResponse({
        "status": "ok"
    })

from django.shortcuts import get_object_or_404
from django.contrib import messages
from tennants.models import PaymentRequest

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

    return render(request, "tenantviews/dashboard.html", context)

@login_required
def initiate_payment(request, charge_id):
    tenant = Tenant.objects.filter(user=request.user).first()
    if tenant is None:
        return HttpResponseForbidden()
    
    charge = get_object_or_404(RentCharge, id=charge_id, tenant=tenant)
    
    if request.method == "POST":
        amount = request.POST.get("amount")
        payment_method = request.POST.get('payment_method')
        reference = request.POST.get('reference')

        if not amount or not payment_method:
            messages.error(request, "Amount and Payment Method are required.")
            return redirect("initiate_payment", charge_id=charge.id)

        if payment_method != "cash" and not reference:
            messages.error(request, "Reference is required for non-cash payments.")
            return redirect("initiate_payment", charge_id=charge.id)
        
        PaymentRequest.objects.create(
            tenant=tenant,
            rent_charge=charge,
            amount=amount,
            payment_method=payment_method,
            payment_reference=reference,
            status='pending'
        )
        
        messages.success(request, "Payment request submitted successfully. Waiting for landlord approval.")
        return redirect("tenant_dashboard")

    return render(request, "tenantviews/initiate_payment.html", {"charge": charge, "tenant": tenant})


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



