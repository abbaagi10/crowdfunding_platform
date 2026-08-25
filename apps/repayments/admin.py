from django.contrib import admin
from .models import RepaymentPlan, Repayment


@admin.register(RepaymentPlan)
class RepaymentPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'interest_rate', 'number_of_installments', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('project__title',)
    readonly_fields = ('total_capital', 'total_interest', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'investment', 'installment_number', 'due_date', 'total_amount', 'status', 'paid_at')
    list_filter = ('status', 'due_date', 'paid_at')
    search_fields = ('investment__investor_profile__user__email', 'investment__project__title')
    readonly_fields = ('capital_amount', 'interest_amount', 'created_at')
    ordering = ('due_date',)
    
    def total_amount(self, obj):
        return obj.total_amount
    total_amount.short_description = 'Montant total'