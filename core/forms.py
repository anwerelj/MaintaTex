from datetime import date
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .models import Breakdown, Intervention, Machine, Profile

UserModel = get_user_model()

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email or username'
        self.fields['username'].widget.attrs['autocomplete'] = 'username'

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username and password:
            if '@' in username:
                matching_users = UserModel.objects.filter(email__iexact=username)
                if matching_users.count() > 1:
                    raise forms.ValidationError(
                        self.error_messages['invalid_login'],
                        code='invalid_login',
                        params={'username': self.username_field.verbose_name},
                    )
                user = matching_users.first()
                username = user.get_username() if user else username
            self.user_cache = authenticate(
                self.request, username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class SignUpForm(forms.Form):
    first_name = forms.CharField(max_length=150, label='First name')
    last_name = forms.CharField(max_length=150, label='Last name')
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=30, label='Phone number')
    role = forms.ChoiceField(choices=Profile.SIGNUP_ROLE_CHOICES)
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password_confirm = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if UserModel.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        if UserModel.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('This email is already used as a username.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'The passwords do not match.')
        return cleaned_data

    def save(self):
        user = UserModel.objects.create_user(
            username=self.cleaned_data['email'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=self.cleaned_data['password'],
        )
        Profile.objects.create(
            user=user,
            role=self.cleaned_data['role'],
            phone_number=self.cleaned_data['phone_number'],
        )
        return user


class UserForm(forms.ModelForm):
    """Used by the administrator to create and update user accounts."""

    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES)
    phone_number = forms.CharField(max_length=30, required=False, label='Phone number')
    password = forms.CharField(widget=forms.PasswordInput, required=False,
                               help_text='Enter any non-empty password.')
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=False,
                                       label='Confirm password')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {'is_active': 'Account active'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_active'].widget.attrs['class'] = 'form-check-input'
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        profile = getattr(self.instance, 'profile', None) if self.instance.pk else None
        if self.instance.pk:
            if profile:
                self.fields['role'].initial = profile.role
                self.fields['phone_number'].initial = profile.phone_number
            self.fields['password'].help_text = 'Leave empty to keep the current password.'
        else:
            self.fields['password'].required = True
            self.fields['password_confirm'].required = True

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password or password_confirm:
            if not password:
                self.add_error('password', 'Password cannot be empty.')
            elif password != password_confirm:
                self.add_error('password_confirm', 'The two passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        user.save()
        profile_defaults = {
            'role': self.cleaned_data['role'],
            'phone_number': self.cleaned_data.get('phone_number', ''),
        }
        Profile.objects.update_or_create(user=user, defaults=profile_defaults)
        return user


class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = ['name', 'code', 'machine_type', 'location', 'status']

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()


class ReportBreakdownForm(forms.ModelForm):
    """Form used by the production manager (no status field)."""

    class Meta:
        model = Breakdown
        fields = ['machine', 'category', 'description', 'breakdown_date', 'priority']
        widgets = {
            'breakdown_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_breakdown_date(self):
        breakdown_date = self.cleaned_data['breakdown_date']
        if breakdown_date > date.today():
            raise forms.ValidationError('The breakdown date cannot be in the future.')
        return breakdown_date

    def clean_description(self):
        description = self.cleaned_data['description'].strip()
        if len(description) < 10:
            raise forms.ValidationError('Please describe the breakdown in at least 10 characters.')
        return description


class BreakdownForm(ReportBreakdownForm):
    """Form used by the administrator (same fields + status)."""

    class Meta(ReportBreakdownForm.Meta):
        fields = ['machine', 'category', 'description', 'breakdown_date', 'priority', 'status']


class TechnicianInterventionForm(forms.ModelForm):
    """Form used by the technician: status, diagnosis and repair description."""

    class Meta:
        model = Intervention
        fields = ['status', 'diagnosis', 'repair_description']
        widgets = {
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'repair_description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('status') == 'completed':
            if not cleaned_data.get('diagnosis'):
                self.add_error('diagnosis', 'A diagnosis is required to complete the intervention.')
            if not cleaned_data.get('repair_description'):
                self.add_error('repair_description',
                               'A repair description is required to complete the intervention.')
        return cleaned_data


class InterventionForm(TechnicianInterventionForm):
    """Form used by the maintenance manager (all fields)."""

    class Meta(TechnicianInterventionForm.Meta):
        fields = ['breakdown', 'technician', 'intervention_date', 'status',
                  'diagnosis', 'repair_description']
        widgets = {
            'intervention_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'repair_description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_technicians = User.objects.filter(
            profile__role='technician', is_active=True)
        self.fields['technician'].queryset = active_technicians
        self.fields['technician'].label = 'Assigned technician'
        self.fields['technician'].label_from_instance = lambda u: u.get_full_name() or u.username
        self.no_active_technicians = not active_technicians.exists()
        if self.no_active_technicians:
            self.fields['technician'].help_text = (
                'No active technicians are available. Ask the administrator to create '
                'or approve a technician account.'
            )
        if not self.instance.pk:
            open_breakdowns = Breakdown.objects.exclude(
                status='resolved').select_related('machine')
            self.fields['breakdown'].queryset = open_breakdowns
            self.fields['breakdown'].label_from_instance = (
                lambda breakdown: (
                    f'#{breakdown.pk} · {breakdown.get_category_display()} · '
                    f'{breakdown.machine.name}'
                )
            )
            self.no_open_breakdowns = not open_breakdowns.exists()
            if not self.no_open_breakdowns:
                self.fields['breakdown'].help_text = (
                    'The incident type is shown next to each breakdown.'
                )
            else:
                self.fields['breakdown'].help_text = (
                    'No open breakdowns are available. Ask a production manager to '
                    'report an electrical, mechanical, or other breakdown first.'
                )
