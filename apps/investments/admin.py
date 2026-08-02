from django.contrib import admin
from .models import Investment


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    """
    Vue d'audit des positions d'investissement. STRICTEMENT en lecture seule --
    un Investment ne doit JAMAIS etre cree/modifie manuellement, uniquement
    via TransactionService.invest() (creation) ou le futur module Repayment
    (Etape 10, pour amount_refunded/status).
    """

    list_display = (
        'investor_profile', 'project', 'amount',
        'amount_refunded', 'remaining_amount_display', 'status', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('investor_profile__user__email', 'project__title')
    readonly_fields = (
        'investor_profile', 'project', 'transaction', 'amount',
        'amount_refunded', 'status', 'created_at', 'updated_at'
    )

    def remaining_amount_display(self, obj):
        return obj.remaining_amount
    remaining_amount_display.short_description = "Montant restant"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
