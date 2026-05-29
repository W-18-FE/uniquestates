from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseRedirect
from datetime import timedelta
from django.db import models
from functools import wraps
from .models import (
    Estate, UserProfile, WaterVendor, WaterOrder, GarbageSchedule,
    ServiceCategory, ServiceProvider, Booking, SecurityAlert, LostItem,
    Gig, MarketItem, BillReminder, FundiRequest, Notification,
    EstateAdmin, CustomTab
)
from .forms import (
    OrderWaterForm, ReportIncidentForm, ReportLostItemForm,
    PostGigForm, SellItemForm, BookFundiForm, SignUpForm
)


def require_permission(permission_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
                if not getattr(ea, permission_name, False):
                    messages.error(request, "You don't have permission.")
                    return redirect('dashboard')
            except EstateAdmin.DoesNotExist:
                messages.error(request, "Admin privileges required.")
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ==============================================
#  DASHBOARD
# ==============================================
@login_required
def dashboard(request):
    try:
        estate = request.user.userprofile.estate
    except (UserProfile.DoesNotExist, AttributeError):
        de = Estate.objects.first() or Estate.objects.create(name='Default Estate', location='Unknown')
        UserProfile.objects.get_or_create(user=request.user, defaults={'estate': de})
        estate = de

    water_order = WaterOrder.objects.filter(customer=request.user, status__in=['Pending','Accepted','On The Way']).last()
    garbage = GarbageSchedule.objects.filter(estate=estate).first()
    alerts = SecurityAlert.objects.filter(estate=estate).order_by('-created_at')[:2]
    recent_notifications = Notification.objects.filter(
        user=request.user,
        notification_type__in=['broadcast', 'broadcast_sent'],
        deleted_at__isnull=True
    ).order_by('-created_at')[:5]
    gigs = Gig.objects.filter(estate=estate).order_by('-id')[:3]
    items = MarketItem.objects.filter(estate=estate).order_by('-id')[:4]
    bills = BillReminder.objects.filter(user=request.user, is_paid=False, status='active').order_by('due_date')[:3]

    is_ea = False; ea = None; fr = []; aa = []; un = 0; eu = []; pu = []; wv_list = []; gs = []; pb = []
    tab = request.GET.get('tab', 'overview'); search = request.GET.get('search', '').strip()
    analytics = None; alert_form = ReportIncidentForm()

    if request.user.is_staff:
        try:
            ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True); is_ea = True
            if ea.can_manage_requests: fr = FundiRequest.objects.filter(estate=ea.estate, status='pending').order_by('-created_at')[:10]
            if ea.can_manage_alerts: aa = SecurityAlert.objects.filter(estate=ea.estate).order_by('-created_at')[:10]
            if ea.can_manage_users:
                qs = User.objects.filter(userprofile__estate=ea.estate, is_superuser=False, is_staff=False).select_related('userprofile')
                if search: qs = qs.filter(models.Q(username__icontains=search) | models.Q(email__icontains=search))
                eu = qs[:50]; pu = qs.filter(is_active=False)
            if ea.can_manage_services: wv_list = WaterVendor.objects.filter(estate=ea.estate); gs = GarbageSchedule.objects.filter(estate=ea.estate)
            if ea.can_manage_bills: pb = BillReminder.objects.filter(estate=ea.estate, status='pending_confirmation').select_related('user').order_by('-created_at')[:20]
            un = Notification.objects.filter(user=request.user, is_read=False).count()

            if tab == 'analytics' and ea.can_view_analytics:
                estate_obj = ea.estate
                analytics = {
                    'total_users': UserProfile.objects.filter(estate=estate_obj).count(),
                    'active_users': User.objects.filter(userprofile__estate=estate_obj, is_active=True, is_staff=False, is_superuser=False).count(),
                    'pending_users': User.objects.filter(userprofile__estate=estate_obj, is_active=False, is_staff=False, is_superuser=False).count(),
                    'fundi_requests_total': FundiRequest.objects.filter(estate=estate_obj).count(),
                    'fundi_requests_pending': FundiRequest.objects.filter(estate=estate_obj, status='pending').count(),
                    'fundi_requests_accepted': FundiRequest.objects.filter(estate=estate_obj, status='accepted').count(),
                    'fundi_requests_completed': FundiRequest.objects.filter(estate=estate_obj, status='completed').count(),
                    'fundi_requests_cancelled': FundiRequest.objects.filter(estate=estate_obj, status='cancelled').count(),
                    'water_orders_total': WaterOrder.objects.filter(vendor__estate=estate_obj).count(),
                    'water_orders_pending': WaterOrder.objects.filter(vendor__estate=estate_obj, status='Pending').count(),
                    'water_orders_accepted': WaterOrder.objects.filter(vendor__estate=estate_obj, status='Accepted').count(),
                    'water_orders_ontheway': WaterOrder.objects.filter(vendor__estate=estate_obj, status='On The Way').count(),
                    'water_orders_delivered': WaterOrder.objects.filter(vendor__estate=estate_obj, status='Delivered').count(),
                    'water_orders_declined': WaterOrder.objects.filter(vendor__estate=estate_obj, status='Declined').count(),
                    'bills_total': BillReminder.objects.filter(estate=estate_obj).count(),
                    'bills_active': BillReminder.objects.filter(estate=estate_obj, status='active', is_paid=False).count(),
                    'bills_pending_confirmation': BillReminder.objects.filter(estate=estate_obj, status='pending_confirmation').count(),
                    'bills_completed': BillReminder.objects.filter(estate=estate_obj, status='completed').count(),
                    'security_alerts': SecurityAlert.objects.filter(estate=estate_obj).count(),
                    'marketplace_items': MarketItem.objects.filter(estate=estate_obj).count(),
                    'lost_items': LostItem.objects.filter(estate=estate_obj).count(),
                    'lost_items_found': LostItem.objects.filter(estate=estate_obj, is_found=True).count(),
                    'gigs': Gig.objects.filter(estate=estate_obj).count(),
                }

            if request.method == 'POST' and 'post_alert' in request.POST and ea.can_manage_alerts:
                af = ReportIncidentForm(request.POST)
                if af.is_valid():
                    inc = af.save(commit=False); inc.estate = ea.estate; inc.reported_by = request.user; inc.save()
                    messages.success(request, "Alert posted to your estate!")
                    return HttpResponseRedirect('/?tab=alerts')

            if request.method == 'POST' and 'send_broadcast' in request.POST and ea.can_broadcast:
                broadcast_title = request.POST.get('broadcast_title', '').strip()
                broadcast_message = request.POST.get('broadcast_message', '').strip()
                if broadcast_title and broadcast_message:
                    estate_residents = User.objects.filter(
                        userprofile__estate=ea.estate, is_superuser=False, is_staff=False, is_active=True
                    )
                    count = 0
                    for resident in estate_residents:
                        Notification.objects.create(
                            user=resident, title=f"[{ea.estate.name}] {broadcast_title}",
                            message=f"From your estate admin ({request.user.username}): {broadcast_message}",
                            notification_type='broadcast', related_id=0
                        )
                        count += 1
                    Notification.objects.create(
                        user=request.user, title="Broadcast Sent",
                        message=f"Your message titled '{broadcast_title}' was sent to {count} residents in {ea.estate.name}.",
                        notification_type='broadcast_sent', related_id=0
                    )
                    messages.success(request, f"Broadcast sent to {count} residents!")
                    return HttpResponseRedirect('/?tab=broadcast')
                else:
                    messages.error(request, "Please provide both a title and message.")
        except EstateAdmin.DoesNotExist: pass

    is_vendor = False; vendor = None; vendor_pending = []; vendor_active = []
    try:
        vendor = WaterVendor.objects.get(user=request.user); is_vendor = True
        vendor_pending = WaterOrder.objects.filter(vendor=vendor, status='Pending').order_by('-created_at')[:20]
        vendor_active = WaterOrder.objects.filter(vendor=vendor, status__in=['Accepted','On The Way']).order_by('-created_at')[:20]
    except WaterVendor.DoesNotExist: pass

    return render(request, 'core/dashboard.html', {
        'water_order': water_order, 'garbage': garbage, 'alerts': alerts,
        'recent_notifications': recent_notifications, 'gigs': gigs, 'items': items, 'bills': bills,
        'is_estate_admin': is_ea, 'estate_admin': ea, 'fundi_requests': fr, 'all_alerts': aa, 'unread_notifications': un,
        'estate_users': eu, 'pending_users': pu, 'water_vendors': wv_list, 'garbage_schedules': gs, 'pending_bills': pb,
        'tab': tab, 'search': search, 'analytics': analytics, 'alert_form': alert_form,
        'total_users': eu.count() if ea and ea.can_manage_users else 0,
        'total_pending': pu.count() if ea and ea.can_manage_users else 0,
        'is_vendor': is_vendor, 'vendor': vendor,
        'vendor_pending_orders': vendor_pending, 'vendor_active_orders': vendor_active,
    })


# ==============================================
#  WATER
# ==============================================
@login_required
def water_view(request):
    estate = request.user.userprofile.estate
    vendors = WaterVendor.objects.filter(estate=estate).exclude(user=request.user).order_by('-is_subscribed', 'name')
    active_order = WaterOrder.objects.filter(customer=request.user, status__in=['Pending','Accepted','On The Way']).last()
    my_orders = WaterOrder.objects.filter(customer=request.user).order_by('-created_at')[:10]

    if request.method == 'POST':
        form = OrderWaterForm(request.POST, estate=estate, user=request.user)
        if form.is_valid():
            order = form.save(commit=False); order.customer = request.user; order.status = 'Pending'; order.save()
            vendor = order.vendor
            if vendor.estate == estate and vendor.user:
                Notification.objects.create(user=vendor.user, title="New Water Order", message=f"{request.user.username} wants {order.litres}L at KSh {order.price}. Accept or decline.", notification_type='water_order', related_id=order.id)
                messages.success(request, f"Order sent to {vendor.name}!")
            else:
                for admin in EstateAdmin.objects.filter(estate=estate, is_subscribed=True):
                    Notification.objects.create(user=admin.user, title="External Water Order", message=f"{request.user.username} ordered {order.litres}L from {vendor.name} (external) at KSh {order.price}.", notification_type='water_order', related_id=order.id)
                messages.success(request, "Order placed! Admin notified.")
            return redirect('water')
    else:
        form = OrderWaterForm(estate=estate, user=request.user)

    return render(request, 'core/water.html', {'vendors': vendors, 'active_order': active_order, 'form': form, 'my_orders': my_orders})


@login_required
def vendor_respond_water(request, order_id):
    order = get_object_or_404(WaterOrder, id=order_id)
    is_vendor = False
    try: vendor = WaterVendor.objects.get(user=request.user)
    except WaterVendor.DoesNotExist: pass
    else: is_vendor = (vendor == order.vendor)
    is_admin = EstateAdmin.objects.filter(user=request.user, is_subscribed=True, estate=order.customer.userprofile.estate).exists()
    if not is_vendor and not is_admin and not request.user.is_superuser:
        messages.error(request, "Permission denied."); return redirect('dashboard')
    if request.method == 'POST':
        action = request.POST.get('action'); msg = request.POST.get('response_message', '').strip()
        driver = request.POST.get('driver_name', ''); eta = request.POST.get('eta_minutes', '')
        if action == 'accept':
            order.status = 'Accepted'; order.vendor_response = msg; order.driver_name = driver or 'TBD'; order.eta_minutes = int(eta) if eta else None; order.save()
            Notification.objects.create(user=order.customer, title="Water Order Accepted!", message=f"Your {order.litres}L order ACCEPTED.\nResponse: {msg}\nDriver: {order.driver_name}\nETA: {order.eta_minutes or 'TBD'} min\nPrice: KSh {order.price}", notification_type='water_response', related_id=order.id)
        elif action == 'decline':
            order.status = 'Declined'; order.vendor_response = msg; order.save()
            Notification.objects.create(user=order.customer, title="Water Order Declined", message=f"Your {order.litres}L order declined.\nReason: {msg}", notification_type='water_response', related_id=order.id)
        elif action == 'on_the_way': order.status = 'On The Way'; order.save()
        elif action == 'delivered': order.status = 'Delivered'; order.save()
        messages.success(request, "Response sent."); return redirect('dashboard')
    return render(request, 'core/vendor_respond_water.html', {'order': order})


# ==============================================
#  GARBAGE
# ==============================================
@login_required
def garbage_view(request):
    return render(request, 'core/garbage.html', {'schedules': GarbageSchedule.objects.filter(estate=request.user.userprofile.estate)})


# ==============================================
#  FUNDI
# ==============================================
@login_required
def fundi_view(request):
    estate = request.user.userprofile.estate
    categories = ServiceCategory.objects.all(); providers = ServiceProvider.objects.filter(available=True).select_related('category')
    my_requests = FundiRequest.objects.filter(requester=request.user).order_by('-created_at')[:10]
    if request.method == 'POST':
        pid = request.POST.get('provider'); ft = request.POST.get('fundi_type', ''); ct = request.POST.get('custom_type', ''); tn = request.POST.get('time_needed', ''); desc = request.POST.get('description', '')
        rn = request.POST.get('requester_name', request.user.get_full_name() or request.user.username); rp = request.POST.get('requester_phone', request.user.userprofile.phone if hasattr(request.user, 'userprofile') else '')
        fft = ct if (ft == 'Other' and ct) else (ft or 'Not specified')
        fr = FundiRequest.objects.create(estate=estate, requester=request.user, requester_name=rn, requester_phone=rp, fundi_type=fft, time_needed=tn if tn else None, description=desc, status='pending')
        if pid:
            try: p = ServiceProvider.objects.get(id=pid); fr.provider = p; fr.save(); Booking.objects.create(customer=request.user, provider=p, description=f"[{fft}] {desc}"); Notification.objects.create(user=p.user, title="New Booking", message=f"{rn} wants to book you as {fft}.", notification_type='fundi_request', related_id=fr.id)
            except ServiceProvider.DoesNotExist: pass
        for admin in EstateAdmin.objects.filter(estate=estate, is_subscribed=True): Notification.objects.create(user=admin.user, title="New Fundi Request", message=f"{rn} needs {fft}.", notification_type='fundi_request', related_id=fr.id)
        messages.success(request, "Request submitted!"); return redirect('fundi')
    return render(request, 'core/fundi.html', {'categories': categories, 'providers': providers, 'form': BookFundiForm(), 'my_requests': my_requests})


@login_required
def fundi_requests_view(request):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except EstateAdmin.DoesNotExist: messages.error(request, "Permission denied."); return redirect('dashboard')
    reqs = FundiRequest.objects.filter(estate=ea.estate).order_by('-created_at')
    if request.method == 'POST':
        rid = request.POST.get('request_id'); action = request.POST.get('action'); rm = request.POST.get('response_message', '')
        try:
            fr = FundiRequest.objects.get(id=rid, estate=ea.estate)
            if action == 'accept': fr.status = 'accepted'; fr.admin_response = rm; fr.save(); Notification.objects.create(user=fr.requester, title="Request Accepted", message=f"Admin: {rm}", notification_type='fundi_response', related_id=fr.id)
            elif action == 'decline': fr.status = 'cancelled'; fr.admin_response = rm; fr.save(); Notification.objects.create(user=fr.requester, title="Request Declined", message=f"Admin: {rm}", notification_type='fundi_response', related_id=fr.id)
            elif action == 'complete': fr.status = 'completed'; fr.save()
        except FundiRequest.DoesNotExist: pass
        return redirect('fundi_requests')
    return render(request, 'core/fundi_requests.html', {'requests': reqs, 'estate_admin': ea})


@login_required
def admin_respond_view(request, request_id):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except EstateAdmin.DoesNotExist: messages.error(request, "Permission denied."); return redirect('dashboard')
    fr = get_object_or_404(FundiRequest, id=request_id, estate=ea.estate)
    if request.method == 'POST':
        action = request.POST.get('action'); rm = request.POST.get('response_message', '').strip()
        if not rm: messages.error(request, "Please write a response."); return redirect('admin_respond', request_id=request_id)
        if action == 'accept': fr.status = 'accepted'; fr.admin_response = rm; fr.save(); Notification.objects.create(user=fr.requester, title="Fundi Request Accepted!", message=f"Your {fr.fundi_type} request ACCEPTED.\n\nAdmin: {rm}", notification_type='fundi_response', related_id=fr.id)
        elif action == 'decline': fr.status = 'cancelled'; fr.admin_response = rm; fr.save(); Notification.objects.create(user=fr.requester, title="Fundi Request Update", message=f"Your {fr.fundi_type} request not fulfilled.\n\nAdmin: {rm}", notification_type='fundi_response', related_id=fr.id)
        elif action == 'complete': fr.status = 'completed'; fr.save()
        messages.success(request, "Response sent."); return redirect('dashboard')
    return render(request, 'core/admin_respond.html', {'fundi_request': fr})


@login_required
def my_notifications_feedback(request):
    return render(request, 'core/my_feedback.html', {
        'fundi_responses': FundiRequest.objects.filter(requester=request.user).exclude(admin_response='').order_by('-created_at')[:20],
        'water_responses': WaterOrder.objects.filter(customer=request.user).exclude(vendor_response='').order_by('-created_at')[:20],
    })


# ==============================================
#  SECURITY, LOST&FOUND, JOBS, MARKETPLACE
# ==============================================
@login_required
def security_view(request):
    e = request.user.userprofile.estate
    if request.method == 'POST': f = ReportIncidentForm(request.POST)
    else: f = ReportIncidentForm()
    if request.method == 'POST' and f.is_valid(): inc = f.save(commit=False); inc.estate = e; inc.reported_by = request.user; inc.save(); messages.success(request, "Incident reported."); return redirect('security')
    return render(request, 'core/security.html', {'alerts': SecurityAlert.objects.filter(estate=e).order_by('-created_at'), 'form': f})

@login_required
def lost_found_view(request):
    e = request.user.userprofile.estate
    if request.method == 'POST': f = ReportLostItemForm(request.POST)
    else: f = ReportLostItemForm()
    if request.method == 'POST' and f.is_valid(): lost = f.save(commit=False); lost.estate = e; lost.posted_by = request.user; lost.save(); messages.success(request, "Lost item reported."); return redirect('lost_found')
    return render(request, 'core/lost_found.html', {'items': LostItem.objects.filter(estate=e).order_by('-id'), 'form': f})

@login_required
def jobs_view(request):
    e = request.user.userprofile.estate
    if request.method == 'POST': f = PostGigForm(request.POST)
    else: f = PostGigForm()
    if request.method == 'POST' and f.is_valid(): gig = f.save(commit=False); gig.estate = e; gig.posted_by = request.user; gig.save(); messages.success(request, "Job posted!"); return redirect('jobs')
    return render(request, 'core/jobs.html', {'gigs': Gig.objects.filter(estate=e).order_by('-id'), 'form': f})

@login_required
def marketplace_view(request):
    e = request.user.userprofile.estate
    if request.method == 'POST': f = SellItemForm(request.POST, request.FILES)
    else: f = SellItemForm()
    if request.method == 'POST' and f.is_valid(): item = f.save(commit=False); item.estate = e; item.seller = request.user; item.save(); messages.success(request, "Item listed!"); return redirect('marketplace')
    return render(request, 'core/marketplace.html', {'items': MarketItem.objects.filter(estate=e).order_by('-featured', '-id'), 'form': f})


# ==============================================
#  BILLS
# ==============================================
@login_required
def bills_view(request):
    return render(request, 'core/bills.html', {
        'bills': BillReminder.objects.filter(user=request.user, status='active', is_paid=False).order_by('due_date'),
        'pending_bills': BillReminder.objects.filter(user=request.user, status='pending_confirmation').order_by('due_date'),
        'today': timezone.now().date()
    })

@login_required
def mark_bill_paid(request, bill_id):
    bill = get_object_or_404(BillReminder, id=bill_id, user=request.user, status='active'); bill.status = 'pending_confirmation'; bill.paid_at = timezone.now(); bill.save()
    for admin in EstateAdmin.objects.filter(estate=bill.estate, is_subscribed=True, can_manage_bills=True): Notification.objects.create(user=admin.user, title="Bill Payment Confirmation", message=f"{request.user.username} marked '{bill.title}' (KSh {bill.amount}) as paid.", notification_type='bill_confirmation', related_id=bill.id)
    messages.success(request, "Payment marked!"); return redirect('bills')

@login_required
@require_permission('can_manage_bills')
def admin_confirm_bill(request, bill_id):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except: return redirect('dashboard')
    bill = get_object_or_404(BillReminder, id=bill_id, estate=ea.estate, status='pending_confirmation'); bill.status = 'completed'; bill.is_paid = True; bill.confirmed_by = request.user; bill.confirmed_at = timezone.now(); bill.save()
    Notification.objects.create(user=bill.user, title="Bill Confirmed", message=f"Payment for '{bill.title}' confirmed.", notification_type='bill_confirmed', related_id=bill.id)
    messages.success(request, "Bill confirmed."); return redirect('dashboard')

@login_required
@require_permission('can_manage_bills')
def admin_delete_bill(request, bill_id):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except: return redirect('dashboard')
    get_object_or_404(BillReminder, id=bill_id, estate=ea.estate).delete(); messages.success(request, "Bill deleted."); return redirect('dashboard')

@login_required
@require_permission('can_manage_bills')
def admin_add_bill(request):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except: return redirect('dashboard')
    if request.method == 'POST':
        un = request.POST.get('username'); ti = request.POST.get('title'); am = request.POST.get('amount'); dd = request.POST.get('due_date')
        try: u = User.objects.get(username=un, userprofile__estate=ea.estate); b = BillReminder.objects.create(user=u, estate=ea.estate, title=ti, amount=am, due_date=dd, status='active', created_by=request.user); Notification.objects.create(user=u, title="New Bill", message=f"'{ti}' (KSh {am}) due {dd}.", notification_type='new_bill', related_id=b.id); messages.success(request, f"Bill added for {un}.")
        except User.DoesNotExist: messages.error(request, "User not found.")
    return redirect('dashboard')


# ==============================================
#  VENDOR PROMOTION
# ==============================================
@login_required
@require_permission('can_manage_services')
def admin_promote_vendor(request):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except: messages.error(request, "Permission denied."); return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip(); vendor_name = request.POST.get('vendor_name', '').strip()
        if not username or not vendor_name: messages.error(request, "Username and vendor name required."); return redirect('dashboard')
        try:
            user = User.objects.get(username=username, userprofile__estate=ea.estate, is_superuser=False, is_staff=False)
        except User.DoesNotExist: messages.error(request, "User not found in your estate."); return redirect('dashboard')
        if WaterVendor.objects.filter(user=user).exists(): messages.error(request, f"{user.username} is already a vendor."); return redirect('dashboard')
        vendor = WaterVendor.objects.create(name=vendor_name, user=user, estate=ea.estate, is_subscribed=True)
        for su in User.objects.filter(is_superuser=True): Notification.objects.create(user=su, title="New Water Vendor Added", message=f"{request.user.username} ({ea.estate.name}) promoted {user.username} as vendor '{vendor_name}'.", notification_type='vendor_created', related_id=vendor.id)
        Notification.objects.create(user=user, title="You are now a Water Vendor!", message=f"You have been promoted to a water vendor for {ea.estate.name}. Your vendor name is '{vendor_name}'. Log out and back in to see the Vendor Panel.", notification_type='vendor_created', related_id=vendor.id)
        messages.success(request, f"{user.username} is now a vendor as '{vendor_name}'.")
    return redirect('dashboard')


# ==============================================
#  NOTIFICATIONS
# ==============================================
@login_required
def notifications_view(request):
    n = Notification.objects.filter(user=request.user).order_by('-created_at'); return render(request, 'core/notifications.html', {'notifications': n, 'unread_count': n.filter(is_read=False).count()})

@login_required
def mark_notification_read(request, notification_id): n = get_object_or_404(Notification, id=notification_id, user=request.user); n.is_read = True; n.save(); return redirect('notifications')

@login_required
def mark_all_notifications_read(request): Notification.objects.filter(user=request.user, is_read=False).update(is_read=True); return redirect('notifications')


# ==============================================
#  DELETE BROADCAST (Estate Admin)
# ==============================================
@login_required
@require_permission('can_broadcast')
def delete_broadcast(request, notification_id):
    """Delete a broadcast sent by the estate admin (removes from all residents' notifications)"""
    try:
        ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
        
        # Get the broadcast_sent record (admin's own copy)
        admin_broadcast = get_object_or_404(
            Notification, 
            id=notification_id, 
            user=request.user, 
            notification_type='broadcast_sent'
        )
        
        # Find matching resident broadcasts (same title, message, and approximate time)
        resident_broadcasts = Notification.objects.filter(
            notification_type='broadcast',
            title=admin_broadcast.title,
            message=admin_broadcast.message,
            created_at__date=admin_broadcast.created_at.date(),
            deleted_at__isnull=True
        )
        
        # Mark them as deleted
        for notification in resident_broadcasts:
            notification.deleted_at = timezone.now()
            notification.save()
        
        # Also mark the admin's broadcast_sent as deleted
        admin_broadcast.deleted_at = timezone.now()
        admin_broadcast.save()
        
        messages.success(request, f"Broadcast '{admin_broadcast.title}' has been deleted for all residents.")
        
    except EstateAdmin.DoesNotExist:
        messages.error(request, "Admin privileges required.")
    except Exception as e:
        messages.error(request, f"Failed to delete broadcast: {str(e)}")
    
    return redirect('dashboard')


# ==============================================
#  AUTH
# ==============================================
def signup_view(request):
    if request.method == 'POST': f = SignUpForm(request.POST)
    else: f = SignUpForm()
    if request.method == 'POST' and f.is_valid(): f.save(); return render(request, 'core/signup_pending.html')
    return render(request, 'core/signup.html', {'form': f})

@staff_member_required
def approve_users_view(request):
    p = User.objects.filter(is_active=False)
    if request.method == 'POST': uid = request.POST.get('user_id'); action = request.POST.get('action'); u = User.objects.get(id=uid)
    if request.method == 'POST':
        if action == 'approve': u.is_active = True; u.save()
        elif action == 'reject': u.delete()
        return redirect('approve_users')
    return render(request, 'core/approve_users.html', {'pending_users': p})

@staff_member_required
def admin_management_view(request):
    from django.db.models import Q as DQ
    s = request.GET.get('search', '').strip(); tab = request.GET.get('tab', 'admins')
    admins = EstateAdmin.objects.select_related('user', 'estate', 'approved_by').all(); users = User.objects.filter(is_superuser=False, is_staff=False).select_related('userprofile__estate')
    if s: admins = admins.filter(DQ(user__username__icontains=s) | DQ(estate__name__icontains=s) | DQ(estate__location__icontains=s)); users = users.filter(DQ(username__icontains=s) | DQ(email__icontains=s) | DQ(userprofile__estate__name__icontains=s))
    return render(request, 'core/admin_management.html', {'admin_data': [{'admin': a, 'user_count': UserProfile.objects.filter(estate=a.estate, user__is_superuser=False, user__is_staff=False).count(), 'estate': a.estate} for a in admins], 'all_users': users[:50], 'search': s, 'tab': tab, 'total_admins': admins.count(), 'total_users': users.count()})

@login_required
@require_permission('can_manage_users')
def admin_approve_resident(request, user_id):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except: return redirect('dashboard')
    u = get_object_or_404(User, id=user_id, userprofile__estate=ea.estate); u.is_active = True; u.save(); messages.success(request, f"{u.username} approved."); return redirect('dashboard')

@login_required
@require_permission('can_manage_users')
def admin_remove_resident(request, user_id):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except: return redirect('dashboard')
    get_object_or_404(User, id=user_id, userprofile__estate=ea.estate, is_superuser=False, is_staff=False).delete(); messages.success(request, "Resident removed."); return redirect('dashboard')

@login_required
@require_permission('can_manage_services')
def admin_add_water_vendor(request):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except: return redirect('dashboard')
    if request.method == 'POST' and request.POST.get('name'): WaterVendor.objects.create(name=request.POST['name'], estate=ea.estate); messages.success(request, "Vendor added.")
    return redirect('dashboard')

@login_required
@require_permission('can_manage_services')
def admin_add_garbage_schedule(request):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except: return redirect('dashboard')
    if request.method == 'POST': d = request.POST.get('day'); t = request.POST.get('time')
    if request.method == 'POST' and d and t: GarbageSchedule.objects.create(estate=ea.estate, collection_day=d, time=t); messages.success(request, "Schedule added.")
    return redirect('dashboard')

@login_required
@require_permission('can_manage_alerts')
def admin_resolve_alert(request, alert_id):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except: return redirect('dashboard')
    get_object_or_404(SecurityAlert, id=alert_id, estate=ea.estate).delete(); messages.success(request, "Alert resolved."); return redirect('dashboard')

@login_required
def manage_tabs_view(request):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True)
    except EstateAdmin.DoesNotExist: messages.error(request, "Permission denied."); return redirect('dashboard')
    tabs = CustomTab.objects.filter(estate=ea.estate, created_by=request.user)
    if request.method == 'POST': n = request.POST.get('name'); u = request.POST.get('url'); c = request.POST.get('color', '#00f2fe')
    if request.method == 'POST' and n and u: CustomTab.objects.create(estate=ea.estate, name=n, url=u, color=c, created_by=request.user); messages.success(request, "Tab added!"); return redirect('manage_tabs')
    return render(request, 'core/manage_tabs.html', {'tabs': tabs, 'estate_admin': ea})

@login_required
def delete_tab_view(request, tab_id):
    try: ea = EstateAdmin.objects.get(user=request.user, is_subscribed=True); CustomTab.objects.get(id=tab_id, estate=ea.estate, created_by=request.user).delete(); messages.success(request, "Tab deleted.")
    except: messages.error(request, "Permission denied.")
    return redirect('manage_tabs')

@staff_member_required
def approve_estate_admin_view(request):
    p = EstateAdmin.objects.filter(is_subscribed=False)
    if request.method == 'POST': aid = request.POST.get('admin_id'); action = request.POST.get('action'); ea = EstateAdmin.objects.get(id=aid)
    if request.method == 'POST':
        if action == 'approve': ea.is_subscribed = True; ea.approved_by = request.user; ea.save(); messages.success(request, f"{ea.user.username} approved.")
        elif action == 'reject': ea.delete()
        return redirect('approve_estate_admin')
    return render(request, 'core/approve_estate_admin.html', {'pending': p})


def latest_alert_count(request):
    eid = request.GET.get('estate')
    if not eid: return JsonResponse({'count': 0})
    try: c = SecurityAlert.objects.filter(estate_id=eid, created_at__gte=timezone.now() - timedelta(minutes=5)).count()
    except: c = 0
    return JsonResponse({'count': c})


def access_denied_view(request, exception=None):
    return render(request, 'core/access_denied.html')
