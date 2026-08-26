# apps/transactions/admin.py
from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Interface d'audit des transactions. STRICTEMENT en lecture seule.
    """
    list_display = (
        'reference', 'transaction_type', 'amount', 'status',
        'source_wallet', 'destination_wallet',
        'project', 'created_at'
    )
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = (
        'reference',
        'source_wallet__user__email',
        'destination_wallet__user__email',
        'description'
    )
    readonly_fields = (
        'reference', 'wallet',
        'source_wallet', 'destination_wallet',
        'transaction_type', 'amount', 'amount_net',
        'fee_amount', 'fee_rate', 'status',
        'project', 'description', 'metadata',
        'external_reference', 'failure_reason',
        'completed_at', 'created_at', 'updated_at'
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False