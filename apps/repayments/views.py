from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Repayment, RepaymentPlan
from .serializers import (
    RepaymentSerializer,
    RepaymentPlanSerializer,
    GeneratePlanSerializer
)
from .services import RepaymentService
from apps.investments.models import Investment


class MyRepaymentsView(generics.ListAPIView):
    """
    Liste des échéances de l'investisseur connecté.
    GET /api/v1/repayments/me/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RepaymentSerializer

    def get_queryset(self):
        return Repayment.objects.filter(
            investment__investor_profile__user=self.request.user
        ).order_by('due_date')


class ProjectRepaymentPlanView(generics.RetrieveAPIView):
    """
    Récupérer le plan de remboursement d'un projet.
    GET /api/v1/repayments/plans/project/{project_id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RepaymentPlanSerializer

    def get_object(self):
        from apps.projects.models import Project
        project_id = self.kwargs['project_id']
        project = Project.objects.get(id=project_id)

        user = self.request.user

        if user.role in ['SUPERADMIN', 'USERADMIN']:
            pass
        elif user == project.company.user:
            pass
        else:
            has_invested = Investment.objects.filter(
                project=project,
                investor_profile__user=user
            ).exists()
            if not has_invested:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Vous n'avez pas accès à ce plan.")

        return RepaymentPlan.objects.get(project=project)


class GenerateRepaymentPlanView(APIView):
    """
    Générer le plan de remboursement (admin).
    POST /api/v1/repayments/plans/generate/{project_id}/
    """
    permission_classes = [IsAdminUser]

    def post(self, request, project_id):
        serializer = GeneratePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.projects.models import Project
        project = Project.objects.get(id=project_id)

        try:
            plan = RepaymentService.generate_plan(
                project=project,
                interest_rate=serializer.validated_data['interest_rate'],
                number_of_installments=serializer.validated_data['number_of_installments'],
                frequency_days=serializer.validated_data.get('frequency_days', 30)
            )

            return Response(
                RepaymentPlanSerializer(plan).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PayRepaymentView(APIView):
    """
    Payer une échéance (admin).
    POST /api/v1/repayments/{id}/pay/
    """
    permission_classes = [IsAdminUser]

    def post(self, request, id):
        try:
            repayment = RepaymentService.pay_repayment(id)
            return Response(RepaymentSerializer(repayment).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CancelInvestmentView(APIView):
    """
    Annuler un investissement (investisseur).
    POST /api/v1/repayments/cancel/{id}/ ou /api/v1/investments/{id}/cancel/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            print(f"🔍 [CANCEL] Tentative d'annulation de l'investissement {id}")
            print(f"🔍 [CANCEL] Utilisateur: {request.user.email}")

            investment = Investment.objects.get(id=id)
            print(f"🔍 [CANCEL] Investissement trouvé: {investment.id}")

            # Vérifier que l'utilisateur est le propriétaire
            if investment.investor_profile.user != request.user:
                print(f"❌ [CANCEL] Utilisateur non propriétaire")
                return Response(
                    {'error': 'Vous n\'êtes pas le propriétaire de cet investissement.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            reason = request.data.get('reason', '')
            print(f"🔍 [CANCEL] Motif: {reason}")

            investment = RepaymentService.cancel_investment(id, reason)
            print(f"✅ [CANCEL] Investissement annulé avec succès")

            return Response({
                'message': 'Investissement annulé avec succès. Les fonds ont été retournés dans votre portefeuille.',
                'investment_id': investment.id,
                'status': investment.status
            })
        except Investment.DoesNotExist:
            print(f"❌ [CANCEL] Investissement non trouvé: {id}")
            return Response(
                {'error': 'Investissement non trouvé.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ [CANCEL] Erreur: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )