from datetime import timedelta
from decimal import Decimal

from django.db.models import Count
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Autor, Emprestimo, Livro, Membro


class RegrasDeNegocioTest(TestCase):
    def setUp(self):
        self.autor = Autor.objects.create(nome='Machado de Assis', nacionalidade='Brasileira')
        self.livro = Livro.objects.create(
            titulo='Dom Casmurro', autor=self.autor, isbn='111',
            copias_totais=1, copias_disponiveis=1)
        self.sem_copia = Livro.objects.create(
            titulo='O Cortico', autor=self.autor, isbn='222',
            copias_totais=1, copias_disponiveis=0)
        self.membro = Membro.objects.create(nome='Ana', email='ana@iesb.br')

    def test_emprestar_define_prazo_e_decrementa(self):
        r = self.client.post(
            reverse('emprestar_livro', args=[self.livro.id]),
            {'membro_id': self.membro.id})
        self.assertEqual(r.status_code, 302)
        emp = Emprestimo.objects.get()
        self.assertEqual(
            emp.data_prevista_devolucao,
            timezone.localdate() + timedelta(days=14))
        self.assertEqual(emp.status, 'ATIVO')
        self.livro.refresh_from_db()
        self.assertEqual(self.livro.copias_disponiveis, 0)

    def test_bloqueia_sem_copias(self):
        self.client.post(
            reverse('emprestar_livro', args=[self.sem_copia.id]),
            {'membro_id': self.membro.id})
        self.assertEqual(Emprestimo.objects.count(), 0)
        self.sem_copia.refresh_from_db()
        self.assertEqual(self.sem_copia.copias_disponiveis, 0)

    def test_get_nao_emprestar(self):
        r = self.client.get(reverse('emprestar_livro', args=[self.livro.id]))
        self.assertEqual(r.status_code, 405)

    def test_devolver_repoe_estoque_e_nao_duplica(self):
        self.client.post(
            reverse('emprestar_livro', args=[self.livro.id]),
            {'membro_id': self.membro.id})
        emp = Emprestimo.objects.get()
        self.client.post(reverse('devolver_livro', args=[emp.id]))
        self.client.post(reverse('devolver_livro', args=[emp.id]))  # segunda vez: ignorada
        emp.refresh_from_db()
        self.livro.refresh_from_db()
        self.assertEqual(emp.status, 'DEVOLVIDO')
        self.assertEqual(emp.data_devolucao, timezone.localdate())
        self.assertEqual(self.livro.copias_disponiveis, 1)

    def test_esta_atrasado(self):
        hoje = timezone.localdate()
        atrasado = Emprestimo.objects.create(
            livro=self.livro, membro=self.membro,
            data_prevista_devolucao=hoje - timedelta(days=1))
        no_prazo = Emprestimo.objects.create(
            livro=self.livro, membro=self.membro,
            data_prevista_devolucao=hoje + timedelta(days=3))
        devolvido = Emprestimo.objects.create(
            livro=self.livro, membro=self.membro,
            data_prevista_devolucao=hoje - timedelta(days=5),
            status='DEVOLVIDO')
        self.assertTrue(atrasado.esta_atrasado)
        self.assertFalse(no_prazo.esta_atrasado)
        self.assertFalse(devolvido.esta_atrasado)

    def test_meus_emprestimos_mostra_badge(self):
        Emprestimo.objects.create(
            livro=self.livro, membro=self.membro,
            data_prevista_devolucao=timezone.localdate() - timedelta(days=2))
        r = self.client.get(reverse('meus_emprestimos', args=[self.membro.id]))
        self.assertContains(r, 'Atrasado')

    def test_related_name_e_ranking(self):
        self.assertEqual(self.autor.livros.count(), 2)
        for _ in range(3):
            Emprestimo.objects.create(
                livro=self.livro, membro=self.membro,
                data_prevista_devolucao=timezone.localdate())
        Emprestimo.objects.create(
            livro=self.sem_copia, membro=self.membro,
            data_prevista_devolucao=timezone.localdate())
        ranking = list(
            Livro.objects.annotate(total=Count('emprestimo')).order_by('-total'))
        self.assertEqual(ranking[0].titulo, 'Dom Casmurro')
        self.assertEqual(ranking[0].total, 3)
        self.assertEqual(self.client.get(reverse('relatorio_livros')).status_code, 200)
        self.assertEqual(self.client.get(reverse('lista_livros')).status_code, 200)

    def test_admin_registrado(self):
        from django.contrib import admin
        for m in (Autor, Livro, Membro):
            self.assertIn(m, admin.site._registry)

    def test_limite_de_3_emprestimos_ativos(self):
        livro = Livro.objects.create(
            titulo='Livro Extra', autor=self.autor, isbn='333',
            copias_totais=5, copias_disponiveis=5)
        for _ in range(4):
            self.client.post(
                reverse('emprestar_livro', args=[livro.id]),
                {'membro_id': self.membro.id})
        self.assertEqual(Emprestimo.objects.filter(membro=self.membro).count(), 3)
        livro.refresh_from_db()
        self.assertEqual(livro.copias_disponiveis, 2)

    def test_multa_por_atraso(self):
        emp = Emprestimo.objects.create(
            livro=self.livro, membro=self.membro,
            data_prevista_devolucao=timezone.localdate() - timedelta(days=3))
        self.assertEqual(emp.dias_atraso, 3)
        self.assertEqual(emp.multa, Decimal('1.50'))