from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from apps.accounts.permissions import IsAdminOrSuperAdmin
from apps.projects.models import Project
from .models import RepaymentPlan, Repayment
from .services import RepaymentService
from .serializers import RepaymentPlanSerializer, GeneratePlanRequestSerializer, RepaymentSerializer

@extend_schema(
    tags=['repayments'],
    request=GeneratePlanRequestSerializer,
    responses={201: RepaymentPlanSerializer}
)
class GeneratePlanView(APIView):
    """
    Endpoint POST /api/v1/repayments/plans/generate/<project_id>/
    Reserve a l'administration : genere le plan de remboursement d'un projet.
    """
    permission_classes = (IsAdminOrSuperAdmin,)

    def post(self, request, project_id):
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return Response({"detail": "Projet introuvable."}, status=status.HTTP_404_NOT_FOUND)

        serializer = GeneratePlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            plan = RepaymentService.generate_plan(
                project,
                interest_rate=serializer.validated_data['interest_rate'],
                number_of_installments=serializer.validated_data['number_of_installments'],
                frequency_days=serializer.validated_data['frequency_days'],
            )
        except DjangoValidationError as e:
            message = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RepaymentPlanSerializer(plan).data, status=status.HTTP_201_CREATED)

@extend_schema(
    tags=['repayments'],
    request=None,
    responses={200: RepaymentSerializer}
)
class PayInstallmentView(APIView):
    """
    Endpoint POST /api/v1/repayments/<id>/pay/
    Reserve a l'administration : declenche le paiement REEL d'une echeance
    (simule ici -- en production, ce serait typiquement automatise par
    une tache planifiee verifiant les due_date, hors scope de cette etape).
    """
    permission_classes = (IsAdminOrSuperAdmin,)

    def post(self, request, pk):
        try:
            repayment = Repayment.objects.select_related(
                'investment', 'plan__project__company'
            ).get(pk=pk)
        except Repayment.DoesNotExist:
            return Response({"detail": "Echeance introuvable."}, status=status.HTTP_404_NOT_FOUND)

        try:
            repayment = RepaymentService.pay_installment(repayment)
        except DjangoValidationError as e:
            message = e.messages[0] if hasattr(e, 'messages') else str(e)
            return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RepaymentSerializer(repayment).data, status=status.HTTP_200_OK)


class MyRepaymentListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/repayments/me/
    Toutes les echeances (passees et a venir) de l'investisseur connecte,
    tous projets confondus -- son "calendrier de remboursements".
    """
    serializer_class = RepaymentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        investor_profile = getattr(self.request.user, 'investor_profile', None)
        if investor_profile is None:
            return Repayment.objects.none()
        return Repayment.objects.filter(
            investment__investor_profile=investor_profile
        ).select_related('investment', 'plan__project')


class ProjectRepaymentPlanView(generics.RetrieveAPIView):
    """
    Endpoint GET /api/v1/repayments/plans/project/<project_id>/
    Consultation du plan de remboursement d'un projet : accessible a
    l'entreprise proprietaire, aux investisseurs ayant investi dans ce
    projet, et a l'administration.
    """
    serializer_class = RepaymentPlanSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        from django.shortcuts import get_object_or_404
        project_id = self.kwargs['project_id']
        plan = get_object_or_404(RepaymentPlan, project_id=project_id)

        user = self.request.user
        if user.role in (user.Role.USERADMIN, user.Role.SUPERADMIN):
            return plan

        company_profile = getattr(user, 'company_profile', None)
        if company_profile is not None and plan.project.company == company_profile:
            return plan

        investor_profile = getattr(user, 'investor_profile', None)
        if investor_profile is not None:
            has_invested = plan.project.investments.filter(investor_profile=investor_profile).exists()
            if has_invested:
                return plan

        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Vous n'avez pas acces au plan de remboursement de ce projet.")
