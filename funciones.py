# funciones.py
from functools import reduce

def filtrar_categoria(gastos, categoria):
    return list(filter(lambda g: g['categoria'] == categoria, gastos))

def obtener_montos(gastos):
    return list(map(lambda g: g['monto'], gastos))

def sumar_montos(montos):
    return reduce(lambda a, b: a + b, montos, 0)

def promedio_gastos(gastos):
    montos = obtener_montos(gastos)
    if not montos:
        return 0
    return sumar_montos(montos) / len(montos)
