from django.contrib import admin
from .models import RepaymentPlan, Repayment


class RepaymentInline(admin.TabularInline):
    """Affiche les echeances directement dans la page du plan, en lecture seule."""
    model = Repayment
    extra = 0
    readonly_fields = (
        'investment', 'installment_number', 'due_date',
        'capital_amount', 'interest_amount', 'status', 'paid_at'
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RepaymentPlan)
class RepaymentPlanAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'interest_rate', 'number_of_installments',
        'total_capital', 'total_interest', 'status', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('project__title',)
    readonly_fields = (
        'project', 'interest_rate', 'number_of_installments', 'frequency_days',
        'total_capital', 'total_interest', 'created_at', 'updated_at'
    )
    inlines = [RepaymentInline]

    def has_add_permission(self, request):
        # Un plan se genere UNIQUEMENT via RepaymentService.generate_plan(),
        # jamais manuellement depuis l'admin (calculs trop complexes/critiques).
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    """
    Vue d'audit des echeances individuelles. Le CHANGEMENT DE STATUT reel
    (paiement) passe exclusivement par RepaymentService.pay_installment(),
    jamais par une modification directe ici -- pour garantir que chaque
    paiement cree bien ses Transactions et met a jour Investment.
    """
    list_display = (
        'investment', 'installment_number', 'due_date',
        'capital_amount', 'interest_amount', 'total_amount_display', 'status'
    )
    list_filter = ('status', 'due_date')
    search_fields = ('investment__investor_profile__user__email', 'plan__project__title')
    readonly_fields = (
        'plan', 'investment', 'installment_number', 'due_date',
        'capital_amount', 'interest_amount', 'status', 'paid_at', 'created_at', 'updated_at'
    )

    def total_amount_display(self, obj):
        return obj.total_amount
    total_amount_display.short_description = "Montant total"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
