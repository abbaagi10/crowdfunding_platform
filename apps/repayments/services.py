from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

from .models import RepaymentPlan, Repayment
from apps.investments.models import Investment
from apps.transactions.models import Transaction
from apps.wallets.models import Wallet


class RepaymentService:
    """
    Service de gestion des remboursements.
    """

    @staticmethod
    def generate_plan(project, interest_rate, number_of_installments, frequency_days=30):
        """
        Générer le plan de remboursement pour un projet.
        """
        investments = Investment.objects.filter(
            project=project,
            status='ACTIVE'
        )

        if not investments.exists():
            raise ValidationError("Aucun investissement actif pour ce projet.")

        plan = RepaymentPlan.objects.create(
            project=project,
            interest_rate=interest_rate,
            number_of_installments=number_of_installments,
            frequency_days=frequency_days,
            total_capital=Decimal('0.00'),
            total_interest=Decimal('0.00'),
            status=RepaymentPlan.Status.DRAFT
        )

        total_capital = Decimal('0.00')
        total_interest = Decimal('0.00')

        for investment in investments:
            amount = Decimal(str(investment.amount))

            monthly_rate = (interest_rate / 100) / 12
            installment_amount = amount / number_of_installments
            interest_total = amount * monthly_rate * number_of_installments

            total_capital += amount
            total_interest += interest_total

            start_date = timezone.now().date()

            for i in range(number_of_installments):
                due_date = start_date + timedelta(days=frequency_days * (i + 1))

                Repayment.objects.create(
                    plan=plan,
                    investment=investment,
                    installment_number=i + 1,
                    due_date=due_date,
                    capital_amount=installment_amount,
                    interest_amount=interest_total / number_of_installments,
                    status=Repayment.Status.SCHEDULED
                )

        plan.total_capital = total_capital
        plan.total_interest = total_interest
        plan.status = RepaymentPlan.Status.ACTIVE
        plan.save()

        return plan

    @staticmethod
    def pay_repayment(repayment_id):
        """
        Payer une échéance et créditer l'investisseur.
        """
        repayment = Repayment.objects.get(id=repayment_id)

        if repayment.status == Repayment.Status.PAID:
            raise ValidationError("Cette échéance est déjà payée.")

        if repayment.status == Repayment.Status.CANCELLED:
            raise ValidationError("Cette échéance a été annulée.")

        repayment.mark_as_paid()

        wallet = Wallet.objects.get(user=repayment.investment.investor_profile.user)
        total_amount = repayment.capital_amount + repayment.interest_amount

        wallet.credit(
            amount=total_amount,
            description=f"Remboursement échéance #{repayment.installment_number} - {repayment.investment.project.title}"
        )

        return repayment

    @staticmethod
    def cancel_investment(investment_id, reason=None):
        """
        Annuler un investissement et rembourser l'investisseur.
        Les fonds retournent dans le wallet de l'investisseur.
        """
        try:
            investment = Investment.objects.get(id=investment_id)
        except Investment.DoesNotExist:
            raise ValidationError("Investissement non trouvé.")

        project = investment.project

        # Vérifier que le projet n'a pas encore commencé
        if project.start_date and project.start_date <= timezone.now().date():
            raise ValidationError("Le projet a déjà commencé, annulation impossible.")

        if investment.status == 'REFUNDED':
            raise ValidationError("Cet investissement est déjà remboursé.")

        # Annuler les échéances
        repayments = Repayment.objects.filter(
            investment=investment,
            status__in=[Repayment.Status.SCHEDULED, Repayment.Status.LATE]
        )
        repayments.update(status=Repayment.Status.CANCELLED)

        # Récupérer le wallet de l'investisseur
        wallet = Wallet.objects.get(user=investment.investor_profile.user)
        amount = Decimal(str(investment.amount))

        # Créditer le wallet (remboursement intégral)
        wallet.credit(
            amount=amount,
            description=f"Annulation investissement - {project.title}"
        )

        # Mettre à jour le statut de l'investissement
        investment.status = 'REFUNDED'
        investment.save()

        # Créer une transaction de remboursement
        Transaction.objects.create(
            wallet=wallet,
            transaction_type='REFUND',
            amount=amount,
            status='COMPLETED',
            project=project,
            description=f"Annulation investissement - {project.title}"
        )

        return investment