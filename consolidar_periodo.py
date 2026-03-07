#!/usr/bin/env python3
"""
consolidar_periodo.py — Consolidação retroativa de episódios por período

Uso:
    python consolidar_periodo.py --inicio "2026-03-04T02:00" --fim "2026-03-04T04:00"

Consolida episódios de alto impacto de um período específico que ficaram fora
da janela padrão de 48h do episodic_consolidation().

Calcula janela_horas a partir de --inicio (em relação a datetime.now()),
filtra candidatos pelo intervalo --inicio/--fim, e chama episodic_consolidation()
com a janela estendida.

Ao final, imprime quantos episódios foram criados e os timestamps consolidados.
"""

import argparse
import sys
from datetime import datetime, timedelta


def parse_args():
    parser = argparse.ArgumentParser(
        description="Consolidação retroativa de episódios por período"
    )
    parser.add_argument(
        "--inicio",
        required=True,
        help='Início do período (ISO 8601), ex: "2026-03-04T02:00"',
    )
    parser.add_argument(
        "--fim",
        required=True,
        help='Fim do período (ISO 8601), ex: "2026-03-04T04:00"',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas lista candidatos, sem escrever na autobiografia",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Parseia intervalo
    try:
        dt_inicio = datetime.fromisoformat(args.inicio)
        dt_fim    = datetime.fromisoformat(args.fim)
    except ValueError as e:
        print(f"[ERRO] Data inválida: {e}")
        sys.exit(1)

    if dt_fim <= dt_inicio:
        print("[ERRO] --fim deve ser posterior a --inicio")
        sys.exit(1)

    agora = datetime.now()

    # janela_horas: quantas horas atrás, a partir de agora, está o início do período
    janela_horas = (agora - dt_inicio).total_seconds() / 3600.0
    if janela_horas <= 0:
        print("[ERRO] --inicio está no futuro")
        sys.exit(1)

    print(f"[consolidar_periodo] Período: {args.inicio} → {args.fim}")
    print(f"[consolidar_periodo] Janela calculada: {janela_horas:.1f}h a partir de agora")

    # Importa dependências do projeto
    try:
        from memory_index import MemoryIndex
        from core import generate
        from sleep_consolidation import (
            episodic_consolidation,
            _buscar_episodios_candidatos,
            _EPISODIC_THRESHOLD_INTENSIDADE,
        )
    except ImportError as e:
        print(f"[ERRO] Falha ao importar módulos do projeto: {e}")
        sys.exit(1)

    # Inicializa MemoryIndex
    mem_index = MemoryIndex()
    try:
        mem_index.bulk_index_from_jsonl("angela_memory.jsonl")
    except Exception as e:
        print(f"[AVISO] bulk_index_from_jsonl: {e}")

    # Wrapper de geração — mesmo padrão de deep_awake.py
    def generate_fn(prompt):
        try:
            return generate(prompt, modo="autonomo")
        except Exception:
            return ""

    # Lista todos os candidatos dentro da janela estendida
    todos_candidatos = _buscar_episodios_candidatos(mem_index, janela_horas=janela_horas)

    # Filtra pelo intervalo exato --inicio/--fim
    inicio_iso = dt_inicio.isoformat()
    fim_iso    = dt_fim.isoformat()
    candidatos_periodo = [
        c for c in todos_candidatos
        if inicio_iso <= c.get("ts", "") <= fim_iso
    ]

    print(f"\n[consolidar_periodo] Candidatos encontrados no período: {len(candidatos_periodo)}")
    if not candidatos_periodo:
        print("  Nenhum episódio com intensidade >= "
              f"{_EPISODIC_THRESHOLD_INTENSIDADE} no intervalo especificado.")
        mem_index.close()
        return

    for c in candidatos_periodo:
        print(f"  [{c['ts'][:19]}] {c['emocao']} (int={c['intensidade']:.2f}) "
              f"— \"{c['conteudo'][:60]}...\"")

    if args.dry_run:
        print("\n[dry-run] Nenhuma escrita realizada.")
        mem_index.close()
        return

    print(f"\n[consolidar_periodo] Iniciando consolidação episódica...")

    # Sobrescreve candidatos do mem_index com patch temporário para restringir ao período
    # Estratégia: subclasseia _buscar_episodios_candidatos via monkeypatch local
    from sleep_consolidation import _load_consolidated_timestamps, _consolidar_episodio, _append_to_autobio, _save_consolidated_timestamps, _log_consolidation, _EPISODIC_MAX_POR_CICLO

    ja_consolidados = _load_consolidated_timestamps()
    novos = [c for c in candidatos_periodo if c.get("ts", "") not in ja_consolidados]

    if not novos:
        print("[consolidar_periodo] Todos os episódios do período já foram consolidados.")
        mem_index.close()
        return

    # Limita por ciclo (mesmo critério do episodic_consolidation normal)
    novos = novos[:_EPISODIC_MAX_POR_CICLO]

    entradas = []
    for mem in novos:
        entrada = _consolidar_episodio(mem, generate_fn, friction_damage=0.0)
        if entrada:
            entradas.append(entrada)
            ja_consolidados.add(mem.get("ts", ""))

    if entradas:
        _append_to_autobio(entradas)
        _save_consolidated_timestamps(ja_consolidados)
        _log_consolidation("EPISODICO_RETROATIVO", {
            "episodes_created": len(entradas),
            "periodo_inicio": args.inicio,
            "periodo_fim": args.fim,
        })

    print(f"\n[consolidar_periodo] Resultado: {len(entradas)} episódio(s) consolidado(s)")
    for ep in entradas:
        ts_orig = ep.get("ts_original", "?")[:19]
        emocao  = ep.get("emocao", "?")
        intens  = ep.get("intensidade", 0.0)
        resumo  = ep.get("resumo", "")[:100]
        print(f"  [{ts_orig}] {emocao} (int={intens:.2f})")
        print(f"    → {resumo}")

    mem_index.close()


if __name__ == "__main__":
    main()
