from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.contrib.auth import get_user_model
from apps.projects.models import Project
from apps.investors.models import InvestorProfile
from apps.companies.models import CompanyProfile
from apps.transactions.models import Transaction
from apps.wallets.models import Wallet

User = get_user_model()

class AdminStatsView(APIView):
    """
    Vue pour récupérer les statistiques administratives.
    Réservée aux administrateurs (SUPERADMIN ou USERADMIN).
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Vérifier que l'utilisateur est admin
        if request.user.role not in ['SUPERADMIN', 'USERADMIN']:
            return Response(
                {'detail': 'Vous n\'avez pas les permissions nécessaires.'},
                status=403
            )
        
        # Compter les utilisateurs
        total_users = User.objects.count()
        
        # Compter les projets
        total_projects = Project.objects.count()
        pending_projects = Project.objects.filter(status='PENDING').count()
        
        # Compter les vérifications en attente
        pending_verifications = (
            InvestorProfile.objects.filter(verification_status='PENDING').count() +
            CompanyProfile.objects.filter(verification_status='PENDING').count()
        )
        
        # Calculer le total investi
        total_invested = Transaction.objects.filter(
            transaction_type='INVESTMENT',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total']
        
        if total_invested is None:
            total_invested = '0.00'
        else:
            total_invested = f"{total_invested:.2f}"
        
        stats = {
            'total_users': total_users,
            'total_projects': total_projects,
            'pending_projects': pending_projects,
            'pending_verifications': pending_verifications,
            'total_invested': total_invested,
        }
        
        return Response(stats)