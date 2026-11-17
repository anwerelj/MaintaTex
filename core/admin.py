from django.contrib import admin

from .models import Breakdown, Intervention, Machine, Profile

admin.site.register(Profile)
admin.site.register(Machine)
admin.site.register(Breakdown)
admin.site.register(Intervention)
