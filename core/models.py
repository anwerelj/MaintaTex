from datetime import date

from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    SIGNUP_ROLE_CHOICES = [
        ('production_manager', 'Production Manager'),
        ('maintenance_manager', 'Maintenance Manager'),
        ('technician', 'Maintenance Technician'),
    ]
    ROLE_CHOICES = [
        ('administrator', 'Administrator'),
        *SIGNUP_ROLE_CHOICES,
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'administrator'
    profile = getattr(user, 'profile', None)
    if profile is None:
        return None
    return profile.role


class Machine(models.Model):
    STATUS_CHOICES = [
        ('operational', 'Operational'),
        ('broken', 'Broken'),
        ('under_maintenance', 'Under Maintenance'),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField('Machine code', max_length=30, unique=True)
    machine_type = models.CharField('Machine type', max_length=100)
    location = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='operational')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def badge_class(self):
        """Bootstrap color used to display the status."""
        colors = {'operational': 'success', 'broken': 'danger', 'under_maintenance': 'warning'}
        return colors[self.status]


class Breakdown(models.Model):
    CATEGORY_CHOICES = [
        ('electrical', 'Electrical outage'),
        ('mechanical', 'Mechanical problem'),
        ('other', 'Other'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='breakdowns')
    category = models.CharField(
        'Breakdown type', max_length=20, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField()
    breakdown_date = models.DateField('Breakdown date', default=date.today)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported')
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='reported_breakdowns')

    class Meta:
        ordering = ['-breakdown_date', '-id']

    def __str__(self):
        return f"Breakdown #{self.id} - {self.machine.name}"

    @property
    def priority_badge(self):
        colors = {'low': 'success', 'medium': 'warning', 'high': 'danger'}
        return colors[self.priority]

    @property
    def badge_class(self):
        colors = {'reported': 'secondary', 'in_progress': 'warning', 'resolved': 'success'}
        return colors[self.status]


class Intervention(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    breakdown = models.ForeignKey(Breakdown, on_delete=models.CASCADE, related_name='interventions')
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='interventions')
    diagnosis = models.TextField(blank=True)
    repair_description = models.TextField(blank=True)
    intervention_date = models.DateField('Intervention date', default=date.today)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        ordering = ['-intervention_date', '-id']

    def __str__(self):
        return f"Intervention #{self.id} - {self.breakdown}"

    @property
    def badge_class(self):
        colors = {'pending': 'secondary', 'in_progress': 'warning', 'completed': 'success'}
        return colors[self.status]
