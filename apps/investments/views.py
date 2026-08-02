from django.db.models import Sum
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin
from .models import Investment
from .serializers import InvestmentSerializer


class MyInvestmentListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/investments/me/
    Le "portefeuille" de l'investisseur connecte : tous ses investissements,
    tous projets confondus, du plus recent au plus ancien.
    """
    serializer_class = InvestmentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        investor_profile = getattr(self.request.user, 'investor_profile', None)
        if investor_profile is None:
            return Investment.objects.none()
        return Investment.objects.filter(
            investor_profile=investor_profile
        ).select_related('project', 'project__company', 'transaction')


class MyInvestmentSummaryView(APIView):
    """
    Endpoint GET /api/v1/investments/me/summary/
    Resume agrege du portefeuille : total investi, nombre de projets distincts,
    total encore actif (non rembourse). Utile pour un tableau de bord investisseur.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        investor_profile = getattr(request.user, 'investor_profile', None)
        if investor_profile is None:
            return Response({
                "total_invested": "0.00",
                "total_remaining": "0.00",
                "projects_count": 0,
            })

        investments = Investment.objects.filter(investor_profile=investor_profile)

        total_invested = investments.aggregate(total=Sum('amount'))['total'] or 0
        total_refunded = investments.aggregate(total=Sum('amount_refunded'))['total'] or 0
        projects_count = investments.values('project').distinct().count()

        return Response({
            "total_invested": str(total_invested),
            "total_remaining": str(total_invested - total_refunded),
            "projects_count": projects_count,
        })


class ProjectInvestmentListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/investments/project/<project_id>/
    Reserve a l'administration ET a l'entreprise proprietaire du projet :
    liste de tous les investissements recus par CE projet precis.
    Utile pour qu'une entreprise suive qui a investi dans SA campagne.
    """
    serializer_class = InvestmentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        user = self.request.user

        base_qs = Investment.objects.filter(project_id=project_id).select_related(
            'project', 'investor_profile__user', 'transaction'
        )

        # Admin : voit tout
        if user.role in (user.Role.USERADMIN, user.Role.SUPERADMIN):
            return base_qs

        # Entreprise : uniquement si c'est SON projet
        company_profile = getattr(user, 'company_profile', None)
        if company_profile is not None:
            return base_qs.filter(project__company=company_profile)

        # Tout autre role (investisseur, etc.) : aucun acces a cette vue globale
        return Investment.objects.none()


class InvestmentListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/investments/
    Reserve a l'administration : audit global de TOUS les investissements.
    """
    queryset = Investment.objects.all().select_related(
        'investor_profile__user', 'project', 'transaction'
    )
    serializer_class = InvestmentSerializer
    permission_classes = (IsAdminOrSuperAdmin,)
