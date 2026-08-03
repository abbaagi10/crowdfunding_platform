from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.investments.models import Investment
from apps.projects.models import Project
from .models import RepaymentPlan, Repayment


class RepaymentService:
    """
    Couche service : genere et gere les plans de remboursement.

    Le calcul au prorata est le coeur de cette classe -- voir
    _split_amount_among_investments() pour la gestion des arrondis.
    """

    @staticmethod
    def _split_amount_among_investments(total_amount: Decimal, investments: list) -> list:
        """
        Repartit `total_amount` entre plusieurs `investments`, au prorata
        du montant de chaque investissement, en garantissant que la SOMME
        des parts est EXACTEMENT egale a total_amount (aucune perte/gain
        de centime du a l'arrondi).

        Technique : chaque investissement (sauf le DERNIER) recoit sa part
        arrondie normalement. Le DERNIER investissement recoit le RESTE EXACT
        (total_amount moins la somme deja distribuee), ce qui absorbe
        automatiquement toute erreur d'arrondi cumulee.

        Retourne une liste de tuples (investment, part_amount), dans le
        MEME ordre que `investments` en entree.
        """
        if not investments:
            return []

        total_invested = sum(inv.amount for inv in investments)
        if total_invested == 0:
            raise ValidationError("Le montant total investi ne peut pas etre zero.")

        results = []
        distributed_so_far = Decimal('0.00')

        for index, investment in enumerate(investments):
            is_last = (index == len(investments) - 1)

            if is_last:
                # Le dernier recoit le reste EXACT -- absorbe l'erreur d'arrondi cumulee
                part = total_amount - distributed_so_far
            else:
                # Part au prorata, arrondie au centime le plus proche
                proportion = investment.amount / total_invested
                part = (total_amount * proportion).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            results.append((investment, part))
            distributed_so_far += part

        return results

    @staticmethod
    @db_transaction.atomic
    def generate_plan(project: Project, interest_rate: Decimal, number_of_installments: int,
                       frequency_days: int = 30) -> RepaymentPlan:
        """
        Genere le RepaymentPlan ET toutes les echeances (Repayment) individuelles
        pour CHAQUE investissement actif sur ce projet, au prorata de leur montant.

        Ne peut etre genere qu'UNE FOIS par projet (OneToOneField sur project).
        """
        if hasattr(project, 'repayment_plan'):
            raise ValidationError(
                f"Un plan de remboursement existe deja pour le projet '{project.title}'."
            )

        active_investments = list(
            Investment.objects.filter(project=project, status=Investment.Status.ACTIVE)
        )
        if not active_investments:
            raise ValidationError(
                "Impossible de generer un plan de remboursement : aucun investissement actif sur ce projet."
            )

        total_capital = project.current_amount
        # Interet simple sur la duree totale : capital * taux_annuel * (duree_totale_en_annees)
        total_duration_years = Decimal(number_of_installments * frequency_days) / Decimal('365')
        total_interest = (total_capital * (interest_rate / Decimal('100')) * total_duration_years).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        plan = RepaymentPlan.objects.create(
            project=project,
            interest_rate=interest_rate,
            number_of_installments=number_of_installments,
            frequency_days=frequency_days,
            total_capital=total_capital,
            total_interest=total_interest,
            status=RepaymentPlan.Status.ACTIVE,
        )

        # Montant de CAPITAL et d'INTERETS par echeance (avant repartition entre investisseurs)
        capital_per_installment = (total_capital / number_of_installments).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        interest_per_installment = (total_interest / number_of_installments).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        today = timezone.now().date()

        for installment_number in range(1, number_of_installments + 1):
            due_date = today + timezone.timedelta(days=frequency_days * installment_number)

            # Pour la DERNIERE echeance globale, on ajuste pour absorber
            # l'arrondi cumule sur capital_per_installment/interest_per_installment,
            # exactement le meme principe que _split_amount_among_investments.
            is_last_installment = (installment_number == number_of_installments)
            if is_last_installment:
                capital_this_installment = total_capital - (capital_per_installment * (number_of_installments - 1))
                interest_this_installment = total_interest - (interest_per_installment * (number_of_installments - 1))
            else:
                capital_this_installment = capital_per_installment
                interest_this_installment = interest_per_installment

            # Repartition de CETTE echeance entre tous les investisseurs, au prorata
            capital_splits = RepaymentService._split_amount_among_investments(
                capital_this_installment, active_investments
            )
            interest_splits = RepaymentService._split_amount_among_investments(
                interest_this_installment, active_investments
            )

            # capital_splits et interest_splits sont dans le MEME ordre que active_investments
            for (investment, capital_part), (_, interest_part) in zip(capital_splits, interest_splits):
                Repayment.objects.create(
                    plan=plan,
                    investment=investment,
                    installment_number=installment_number,
                    due_date=due_date,
                    capital_amount=capital_part,
                    interest_amount=interest_part,
                    status=Repayment.Status.SCHEDULED,
                )

        return plan
