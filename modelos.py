# modelos.py

class Usuario:
    def __init__(self, id, nombre, correo):
        self.id = id
        self.nombre = nombre
        self.correo = correo

    def mensaje_bienvenida(self):
        return f"Bienvenido {self.nombre}, sigue ahorrando!"


class Gasto:
    def __init__(self, id, categoria, monto):
        self.id = id
        self.categoria = categoria
        self.monto = monto


class AnalizadorGastos:
    def __init__(self, gastos):
        self.gastos = gastos

    def total_gastado(self):
        total = 0
        for g in self.gastos:
            total += g.monto
        return total

    def gasto_por_categoria(self, categoria):
        return sum(g.monto for g in self.gastos if g.categoria == categoria)
