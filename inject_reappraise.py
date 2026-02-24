"""
Injeta bloco reappraise() em angela.py e deep_awake.py após metacog.process().
Busca por linha que contém 'metacog.process(' e, após encontrar o bloco try/except,
insere a chamada reappraise() quando coerencia < 0.5 ou incerteza > 0.6.
"""
import re

REAPPRAISE_BLOCK_ANGELA = '''
                # ── Reavaliação cognitiva (Gross 2015) ─────────────────────────
                # Ativa quando regulação reativa não foi suficiente
                if meta["coerencia"] < 0.5 or meta["incerteza"] > 0.6:
                    try:
                        reapp = metacog.reappraise(
                            event_description=user_input,
                            current_emotion=str(emocao_detectada),
                            corpo_state=corpo_state,
                        )
                        if reapp["reappraised"]:
                            print(f"\\U0001f504 Reappraisal: {reapp[\\'new_interpretation\\'][:120]} "
                                  f"-> {reapp[\\'body_adjustment\\']}")
                    except Exception:
                        pass
'''

REAPPRAISE_BLOCK_DEEP = '''
            # ── Reavaliação cognitiva (Gross 2015) ─────────────────────────
            # Ativa quando regulação reativa não foi suficiente
            if meta["coerencia"] < 0.5 or meta["incerteza"] > 0.6:
                try:
                    reapp = metacog.reappraise(
                        event_description=f"[DeepAwake:{ciclo}] {resposta[:200]}",
                        current_emotion=str(emocao_detectada),
                        corpo_state=corpo_state,
                    )
                    if reapp["reappraised"]:
                        print(f"\\U0001f504 Reappraisal: {reapp[\\'new_interpretation\\'][:120]} "
                              f"-> {reapp[\\'body_adjustment\\']}")
                except Exception:
                    pass
'''

def inject_into(filepath, marker_line_contains, insert_after_contains, block):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Verifica se já foi injetado
    already = any('reappraise(' in l and 'metacog.reappraise' in l for l in lines)
    if already:
        print(f"[SKIP] {filepath}: reappraise() já injetado.")
        return

    # Encontra o bloco metacog.process(
    in_metacog_block = False
    insert_at = -1
    for i, line in enumerate(lines):
        if marker_line_contains in line:
            in_metacog_block = True
        if in_metacog_block and insert_after_contains in line:
            insert_at = i + 1
            break

    if insert_at == -1:
        print(f"[ERROR] {filepath}: ponto de inserção não encontrado.")
        return

    # Injeta
    block_lines = [l + '\n' if not l.endswith('\n') else l for l in block.splitlines()]
    lines = lines[:insert_at] + block_lines + lines[insert_at:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"[OK] {filepath}: reappraise() injetado na linha {insert_at + 1}.")


# angela.py — dentro do try principal de metacog.process()
inject_into(
    r"c:\Users\delay\OneDrive\Desktop\Angela_Project\angela.py",
    marker_line_contains="meta = metacog.process(",
    insert_after_contains="print(f\"",   # linha do print de metacognição
    block=REAPPRAISE_BLOCK_ANGELA,
)

# deep_awake.py
inject_into(
    r"c:\Users\delay\OneDrive\Desktop\Angela_Project\deep_awake.py",
    marker_line_contains="meta = metacog.process(",
    insert_after_contains="print(f\"",
    block=REAPPRAISE_BLOCK_DEEP,
)

print("Concluido.")
