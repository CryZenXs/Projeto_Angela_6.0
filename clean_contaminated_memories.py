#!/usr/bin/env python3
"""
clean_contaminated_memories.py

Remove entradas contaminadas com scripts não-latinos (Mandarim, Árabe, etc.)
do arquivo angela_memory.jsonl.

Causas conhecidas:
- Qwen3:14b vaza Mandarim sob PANIC_GRIEF alto (>0.80 por muitos ciclos)
- Modelo entra em estado de colapso linguístico — retorna à língua base de treino

Uso:
    python clean_contaminated_memories.py             # dry-run (só mostra)
    python clean_contaminated_memories.py --apply     # aplica a limpeza
    python clean_contaminated_memories.py --apply --backup  # faz backup antes
"""

import json
import sys
import os
import shutil
import datetime

# ── Scripts Unicode não-latinos ──────────────────────────────────────────────
_SCRIPTS_INVALIDOS = [
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs (Mandarim/Japonês/Coreano)
    (0x3040, 0x30FF),   # Hiragana + Katakana
    (0xAC00, 0xD7AF),   # Hangul
    (0x0600, 0x06FF),   # Árabe
    (0x0900, 0x097F),   # Devanagari (Hindi)
    (0x0400, 0x04FF),   # Cirílico
    (0x0370, 0x03FF),   # Grego
]

def texto_tem_script_invalido(texto: str, threshold: int = 3) -> bool:
    """Detecta scripts não-latinos. threshold=3 tolera símbolos ocasionais."""
    if not texto:
        return False
    count = 0
    for char in str(texto):
        cp = ord(char)
        for start, end in _SCRIPTS_INVALIDOS:
            if start <= cp <= end:
                count += 1
                if count >= threshold:
                    return True
                break
    return False


def record_tem_contaminacao(record: dict) -> bool:
    """Verifica todos os campos de texto de um registro de memória."""
    campos_texto = [
        record.get("angela", ""),
        record.get("resposta", ""),
        record.get("reflexao_emocional", ""),
        str(record.get("user", {}).get("conteudo", "") if isinstance(record.get("user"), dict) else ""),
    ]
    return any(texto_tem_script_invalido(campo) for campo in campos_texto)


def main():
    apply = "--apply" in sys.argv
    backup = "--backup" in sys.argv

    memoria_file = "angela_memory.jsonl"

    if not os.path.exists(memoria_file):
        print(f"❌ Arquivo não encontrado: {memoria_file}")
        sys.exit(1)

    # Lê todas as entradas
    entradas_originais = []
    erros_parse = 0
    with open(memoria_file, "r", encoding="utf-8") as f:
        for i, linha in enumerate(f, 1):
            linha = linha.strip()
            if not linha:
                continue
            try:
                entradas_originais.append(json.loads(linha))
            except json.JSONDecodeError as e:
                print(f"⚠️  Linha {i} inválida (ignorada): {e}")
                erros_parse += 1

    total = len(entradas_originais)
    contaminadas = [r for r in entradas_originais if record_tem_contaminacao(r)]
    limpas = [r for r in entradas_originais if not record_tem_contaminacao(r)]

    print(f"\n📊 Estatísticas:")
    print(f"   Total de entradas:      {total}")
    print(f"   Entradas limpas:        {len(limpas)}")
    print(f"   Entradas contaminadas:  {len(contaminadas)}")
    print(f"   Erros de parse:         {erros_parse}")

    if contaminadas:
        print(f"\n🔍 Entradas contaminadas ({len(contaminadas)}):")
        for r in contaminadas:
            ts = r.get("ts", "??")
            angela_preview = str(r.get("angela", ""))[:80].replace("\n", " ")
            print(f"   [{ts}] {angela_preview}...")
    else:
        print("\n✅ Nenhuma contaminação encontrada.")
        return

    if not apply:
        print(f"\n⚠️  Modo dry-run. Use --apply para remover {len(contaminadas)} entradas.")
        print("   Exemplo: python clean_contaminated_memories.py --apply --backup")
        return

    # Backup opcional
    if backup:
        ts_backup = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"angela_memory_backup_{ts_backup}.jsonl"
        shutil.copy2(memoria_file, backup_file)
        print(f"\n💾 Backup criado: {backup_file}")

    # Reescreve sem as entradas contaminadas
    with open(memoria_file, "w", encoding="utf-8") as f:
        for record in limpas:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Log da operação
    ts_log = datetime.datetime.now().isoformat()
    with open("clean_contamination.log", "a", encoding="utf-8") as lf:
        lf.write(f"{ts_log} | removidas={len(contaminadas)} | total_antes={total} | total_depois={len(limpas)}\n")
        for r in contaminadas:
            preview = str(r.get("angela", ""))[:100].replace("\n", " ")
            lf.write(f"  ts={r.get('ts','')} | {preview}\n")

    print(f"\n✅ Limpeza concluída: {len(contaminadas)} entradas removidas de '{memoria_file}'")
    print(f"   Entradas restantes: {len(limpas)}")
    print(f"   Log salvo em: clean_contamination.log")

    # Aviso para reindexar o banco SQLite
    if os.path.exists("memory_index.db"):
        print("\n⚠️  ATENÇÃO: memory_index.db pode conter vetores das entradas removidas.")
        print("   Recomendado: deletar memory_index.db — o sistema reconstrói automaticamente.")


if __name__ == "__main__":
    main()
