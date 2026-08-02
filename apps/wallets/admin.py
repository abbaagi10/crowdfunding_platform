from django.contrib import admin
from .models import Wallet, WalletHistory


class WalletHistoryInline(admin.TabularInline):
    """
    Affiche l'historique DIRECTEMENT dans la page du wallet (pratique pour l'audit).
    extra=0 : n'affiche pas de ligne vide supplémentaire pour ajouter un mouvement
    manuellement -- l'historique ne doit JAMAIS être modifié depuis l'admin,
    seulement consulté (voir readonly_fields + has_add_permission ci-dessous).
    """
    model = WalletHistory
    extra = 0
    readonly_fields = ('movement_type', 'amount', 'balance_after', 'description', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Empêche toute création manuelle d'un mouvement depuis l'admin :
        # les mouvements ne doivent JAMAIS être créés autrement que via
        # les méthodes credit()/debit()/lock_funds()/unlock_funds() du modèle Wallet,
        # qui garantissent la cohérence (calcul correct de balance_after, etc.)
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'locked_balance', 'available_balance_display', 'currency', 'updated_at')
    search_fields = ('user__email',)
    readonly_fields = ('balance', 'locked_balance', 'created_at', 'updated_at')
    inlines = [WalletHistoryInline]

    def available_balance_display(self, obj):
        return obj.available_balance
    available_balance_display.short_description = "Solde disponible"

    def has_add_permission(self, request):
        # Un wallet ne doit JAMAIS être créé manuellement depuis l'admin,
        # uniquement via le signal automatique post_save sur CustomUser.
        return False


@admin.register(WalletHistory)
class WalletHistoryAdmin(admin.ModelAdmin):
    """
    Vue globale de TOUS les mouvements, tous wallets confondus --
    utile pour un audit financier transversal.
    """
    list_display = ('wallet', 'movement_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('movement_type',)
    search_fields = ('wallet__user__email', 'description')
    readonly_fields = ('wallet', 'movement_type', 'amount', 'balance_after', 'description', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Lecture seule totale : un ledger financier ne se modifie JAMAIS a posteriori
        return False

    def has_delete_permission(self, request, obj=None):
        return False
