from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (BreakdownForm, InterventionForm, MachineForm, ReportBreakdownForm,
                    SignUpForm, TechnicianInterventionForm, UserForm)
from .models import Breakdown, Intervention, Machine, Profile, get_user_role



def update_statuses_after_intervention(intervention):
    breakdown = intervention.breakdown
    machine = breakdown.machine
    if intervention.status == 'completed':
        breakdown.status = 'resolved'
        machine.status = 'operational'
    else:
        breakdown.status = 'in_progress'
        machine.status = 'under_maintenance'
    breakdown.save()
    machine.save()


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


@login_required
def dashboard(request):
    role = get_user_role(request.user)
    if role is None:
        messages.error(request, 'Your account has no role. Please contact the administrator.')
        logout(request)
        return redirect('login')
    context = {}
    if role == 'administrator':
        context = {
            'users_count': User.objects.count(),
            'machines_count': Machine.objects.count(),
            'breakdowns_count': Breakdown.objects.count(),
            'interventions_count': Intervention.objects.count(),
            'recent_breakdowns': Breakdown.objects.select_related('machine')[:5],
        }
    elif role == 'production_manager':
        my_breakdowns = Breakdown.objects.filter(reported_by=request.user)
        context = {
            'operational_count': Machine.objects.filter(status='operational').count(),
            'broken_count': Machine.objects.filter(status='broken').count(),
            'maintenance_count': Machine.objects.filter(status='under_maintenance').count(),
            'my_breakdowns_count': my_breakdowns.count(),
            'recent_breakdowns': my_breakdowns.select_related('machine')[:5],
        }
    elif role == 'maintenance_manager':
        context = {
            'reported_count': Breakdown.objects.filter(status='reported').count(),
            'pending_count': Intervention.objects.filter(status='pending').count(),
            'in_progress_count': Intervention.objects.filter(status='in_progress').count(),
            'completed_count': Intervention.objects.filter(status='completed').count(),
            'new_breakdowns': Breakdown.objects.filter(status='reported').select_related('machine')[:5],
        }
    elif role == 'technician':
        my_interventions = Intervention.objects.filter(technician=request.user)
        context = {
            'pending_count': my_interventions.filter(status='pending').count(),
            'in_progress_count': my_interventions.filter(status='in_progress').count(),
            'completed_count': my_interventions.filter(status='completed').count(),
            'recent_interventions': my_interventions.select_related('breakdown__machine')[:5],
        }

    return render(request, f'{role}/dashboard.html', context)


def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            'Account created. You can log in now.',
        )
        return redirect('login')
    return render(request, 'registration/signup.html', {'form': form})


def role_required(*allowed_roles):
    def decorator(view_function):
        @login_required
        @wraps(view_function)
        def wrapper(request, *args, **kwargs):
            if get_user_role(request.user) in allowed_roles:
                return view_function(request, *args, **kwargs)
            messages.error(request, 'You are not allowed to access this page.')
            return redirect('dashboard')

        return wrapper

    return decorator


@role_required('administrator')
def user_list(request):
    users = User.objects.select_related('profile').order_by('username')
    return render(request, 'administrator/user_list.html', {'users': users})


@role_required('administrator')
def user_add(request):
    form = UserForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'User account created successfully.')
            return redirect('user_list')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'common/form.html', {'form': form, 'title': 'Add a user',
                                         'cancel_url': 'user_list'})

@role_required('administrator')
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserForm(request.POST or None, instance=user)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'User account updated successfully.')
            return redirect('user_list')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'common/form.html', {'form': form, 'title': f'Edit user: {user.username}',
                                         'cancel_url': 'user_list'})


@role_required('administrator')
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User account deleted.')
        return redirect('user_list')
    return render(request, 'common/confirm_delete.html', {'object_name': f'the user "{user.username}"',
                                                   'cancel_url': 'user_list'})


@role_required('administrator', 'production_manager', 'maintenance_manager')
def machine_list(request):
    role = get_user_role(request.user)
    machines = Machine.objects.all()
    return render(request, f'{role}/machine_list.html', {'machines': machines})


@role_required('administrator')
def machine_add(request):
    form = MachineForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Machine added successfully.')
            return redirect('machine_list')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'common/form.html', {'form': form, 'title': 'Add a machine',
                                         'cancel_url': 'machine_list'})


@role_required('administrator')
def machine_edit(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    form = MachineForm(request.POST or None, instance=machine)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Machine updated successfully.')
            return redirect('machine_list')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'common/form.html', {'form': form, 'title': f'Edit machine: {machine.name}',
                                         'cancel_url': 'machine_list'})


@role_required('administrator')
def machine_delete(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    if request.method == 'POST':
        machine.delete()
        messages.success(request, 'Machine deleted.')
        return redirect('machine_list')
    return render(request, 'common/confirm_delete.html', {
        'object_name': f'the machine "{machine.name}" (its breakdowns and interventions will also be deleted)',
        'cancel_url': 'machine_list'})


@role_required('administrator', 'production_manager', 'maintenance_manager')
def breakdown_list(request):
    role = get_user_role(request.user)
    breakdowns = Breakdown.objects.select_related('machine', 'reported_by')
    if role == 'production_manager':
        breakdowns = breakdowns.filter(reported_by=request.user)
    return render(request, f'{role}/breakdown_list.html', {'breakdowns': breakdowns})


@role_required('administrator', 'production_manager')
def breakdown_add(request):
    role = get_user_role(request.user)
    form_class = BreakdownForm if role == 'administrator' else ReportBreakdownForm
    form = form_class(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            breakdown = form.save(commit=False)
            breakdown.reported_by = request.user
            breakdown.save()
            machine = breakdown.machine
            if machine.status == 'operational':
                machine.status = 'broken'
                machine.save()
            messages.success(request, 'Breakdown reported successfully.')
            return redirect('breakdown_list')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'common/form.html', {'form': form, 'title': 'Report a breakdown',
                                         'cancel_url': 'breakdown_list'})


def get_editable_breakdown(request, pk):
    breakdowns = Breakdown.objects.all()
    if get_user_role(request.user) == 'production_manager':
        breakdowns = breakdowns.filter(reported_by=request.user)
    return get_object_or_404(breakdowns, pk=pk)


@role_required('administrator', 'production_manager')
def breakdown_edit(request, pk):
    breakdown = get_editable_breakdown(request, pk)
    form_class = BreakdownForm if get_user_role(request.user) == 'administrator' else ReportBreakdownForm
    form = form_class(request.POST or None, instance=breakdown)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Breakdown updated successfully.')
            return redirect('breakdown_list')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'common/form.html', {'form': form, 'title': f'Edit breakdown #{breakdown.id}',
                                         'cancel_url': 'breakdown_list'})


@role_required('administrator', 'production_manager')
def breakdown_delete(request, pk):
    breakdown = get_editable_breakdown(request, pk)
    if request.method == 'POST':
        breakdown.delete()
        messages.success(request, 'Breakdown deleted.')
        return redirect('breakdown_list')
    return render(request, 'common/confirm_delete.html', {
        'object_name': f'breakdown #{breakdown.id} (its interventions will also be deleted)',
        'cancel_url': 'breakdown_list'})


@role_required('administrator', 'maintenance_manager', 'technician')
def intervention_list(request):
    role = get_user_role(request.user)
    interventions = Intervention.objects.select_related('breakdown__machine', 'technician')
    if role == 'technician':
        interventions = interventions.filter(technician=request.user)
    return render(request, f'{role}/intervention_list.html', {'interventions': interventions})


@role_required('maintenance_manager')
def intervention_add(request):
    initial = {}
    if request.GET.get('breakdown'):
        initial['breakdown'] = request.GET['breakdown']
    form = InterventionForm(request.POST or None, initial=initial)
    if request.method == 'POST':
        if form.is_valid():
            intervention = form.save()
            update_statuses_after_intervention(intervention)
            messages.success(request, 'Intervention created successfully.')
            return redirect('intervention_list')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'common/form.html', {'form': form, 'title': 'Create an intervention',
                                         'cancel_url': 'intervention_list'})


@role_required('maintenance_manager')
def intervention_edit(request, pk):
    intervention = get_object_or_404(Intervention, pk=pk)
    form = InterventionForm(request.POST or None, instance=intervention)
    if request.method == 'POST':
        if form.is_valid():
            intervention = form.save()
            update_statuses_after_intervention(intervention)
            messages.success(request, 'Intervention updated successfully.')
            return redirect('intervention_list')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'common/form.html', {'form': form, 'title': f'Edit intervention #{intervention.id}',
                                         'cancel_url': 'intervention_list'})


@role_required('maintenance_manager')
def intervention_delete(request, pk):
    intervention = get_object_or_404(Intervention, pk=pk)
    if request.method == 'POST':
        intervention.delete()
        messages.success(request, 'Intervention deleted.')
        return redirect('intervention_list')
    return render(request, 'common/confirm_delete.html', {
        'object_name': f'intervention #{intervention.id}',
        'cancel_url': 'intervention_list'})


@role_required('technician')
def intervention_detail(request, pk):
    intervention = get_object_or_404(Intervention, pk=pk, technician=request.user)
    return render(request, 'technician/intervention_detail.html', {'intervention': intervention})


@role_required('technician')
def intervention_update(request, pk):
    """The technician updates the status, the diagnosis and the repair description."""
    intervention = get_object_or_404(Intervention, pk=pk, technician=request.user)
    form = TechnicianInterventionForm(request.POST or None, instance=intervention)
    if request.method == 'POST':
        if form.is_valid():
            intervention = form.save()
            update_statuses_after_intervention(intervention)
            messages.success(request, 'Intervention updated successfully.')
            return redirect('intervention_detail', pk=intervention.pk)
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'common/form.html', {'form': form, 'title': f'Update intervention #{intervention.id}',
                                         'cancel_url': 'intervention_list'})
