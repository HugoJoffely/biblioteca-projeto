from django.db import models
from django.utils import timezone


class Autor(models.Model):
    nome = models.CharField(max_length=150)
    nacionalidade = models.CharField(max_length=80)
    data_nascimento = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.nome


class Livro(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.ForeignKey(Autor, on_delete=models.CASCADE, related_name='livros')
    isbn = models.CharField(max_length=20, unique=True)
    copias_totais = models.PositiveIntegerField()
    copias_disponiveis = models.PositiveIntegerField()

    def __str__(self):
        return self.titulo


class Membro(models.Model):
    nome = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    data_cadastro = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.nome


class Emprestimo(models.Model):
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('DEVOLVIDO', 'Devolvido'),
        ('ATRASADO', 'Atrasado'),
    ]

    livro = models.ForeignKey(Livro, on_delete=models.CASCADE)
    membro = models.ForeignKey(Membro, on_delete=models.CASCADE)
    data_emprestimo = models.DateField(auto_now_add=True)
    data_prevista_devolucao = models.DateField()
    data_devolucao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ATIVO')

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ATIVO')

    @property
    def esta_atrasado(self):
        return self.status == 'ATIVO' and self.data_prevista_devolucao < timezone.localdate()

    def __str__(self):
        return f'{self.membro} -> {self.livro}'
    
    def __str__(self):
        return f'{self.membro} -> {self.livro}'