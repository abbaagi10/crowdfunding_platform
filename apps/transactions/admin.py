from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Interface d'audit des transactions. STRICTEMENT en lecture seule --
    une transaction ne doit JAMAIS etre modifiee ou supprimee manuellement,
    exactement comme WalletHistory (Etape 7). Toute transaction est creee
    UNIQUEMENT via TransactionService, jamais depuis l'admin.
    """

    list_display = (
        'reference', 'wallet', 'transaction_type', 'amount',
        'status', 'project', 'created_at'
    )
    list_filter = ('transaction_type', 'status')
    search_fields = ('reference', 'wallet__user__email', 'description')
    readonly_fields = (
        'reference', 'wallet', 'transaction_type', 'amount', 'status',
        'project', 'description', 'failure_reason', 'created_at', 'updated_at'
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
