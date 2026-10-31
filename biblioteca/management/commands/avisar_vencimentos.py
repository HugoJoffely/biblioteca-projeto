from datetime import timedelta

from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from biblioteca.models import Emprestimo


class Command(BaseCommand):
    help = 'Avisa por e-mail os membros cujo empréstimo vence em 2 dias.'

    def handle(self, *args, **options):
        alvo = timezone.localdate() + timedelta(days=2)
        emprestimos = Emprestimo.objects.filter(
            status='ATIVO', data_prevista_devolucao=alvo
        ).select_related('livro', 'membro')
        for emp in emprestimos:
            send_mail(
                subject='Seu empréstimo vence em 2 dias',
                message=(
                    f'Olá, {emp.membro.nome}! O livro "{emp.livro.titulo}" '
                    f'deve ser devolvido até {emp.data_prevista_devolucao:%d/%m/%Y}.'
                ),
                from_email=None,
                recipient_list=[emp.membro.email],
            )
        self.stdout.write(f'{len(emprestimos)} aviso(s) enviado(s).')