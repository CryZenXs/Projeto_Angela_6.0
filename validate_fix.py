#!/usr/bin/env python3
# validate_fix.py
# Valida que a correção de loops foi aplicada corretamente

import sys
import os

def check_file_version():
    """Verifica se deep_awake.py é a versão corrigida"""
    try:
        with open("deep_awake.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        checks = {
            "v2.1.1": "v2.1.1" in content or "CORREÇÃO DEFINITIVA" in content,
            "FIX #1": content.count("FIX #1") >= 2,
            "FIX #2": content.count("FIX #2") >= 2,
            "FIX #3": content.count("FIX #3") >= 2,
            "gerar_abstracao_variada": "gerar_abstracao_variada" in content,
            "consecutive_blocks": "consecutive_blocks" in content,
            "ABSTRACT_PHRASES": "ABSTRACT_PHRASES" in content,
        }
        
        print("📋 VALIDAÇÃO DA CORREÇÃO\n")
        print("Arquivo: deep_awake.py")
        print("─" * 50)
        
        all_passed = True
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
            if not passed:
                all_passed = False
        
        print("─" * 50)
        
        if all_passed:
            print("\n✅ CORREÇÃO APLICADA CORRETAMENTE")
            print("Sistema pronto para testes.")
            return True
        else:
            print("\n❌ CORREÇÃO INCOMPLETA")
            print("Aplicar deep_awake_FIXED_v2.py manualmente:")
            print("  cp deep_awake_FIXED_v2.py deep_awake.py")
            return False
            
    except FileNotFoundError:
        print("❌ Arquivo deep_awake.py não encontrado!")
        print("Execute este script no diretório do projeto.")
        return False

def check_memory_pollution():
    """Verifica se memória tem entradas vazias"""
    try:
        import json
        
        with open("angela_memory.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        total = len(lines)
        empty = 0
        abstract_repeats = []
        last_abstract = None
        repeat_count = 0
        
        for line in lines[-50:]:  # Últimas 50
            try:
                data = json.loads(line)
                angela = data.get("angela", "")
                
                # Conta vazios
                if not angela.strip():
                    empty += 1
                
                # Conta repetições de abstração
                if angela.startswith("Há uma sensação vaga"):
                    if angela == last_abstract:
                        repeat_count += 1
                    else:
                        if repeat_count > 1:
                            abstract_repeats.append(repeat_count)
                        repeat_count = 1
                        last_abstract = angela
                else:
                    if repeat_count > 1:
                        abstract_repeats.append(repeat_count)
                    repeat_count = 0
                    last_abstract = None
                    
            except:
                pass
        
        print("\n📊 ESTADO DA MEMÓRIA\n")
        print(f"Total de entradas: {total}")
        print(f"Entradas vazias (últimas 50): {empty}")
        print(f"Maior sequência de abstrações idênticas: {max(abstract_repeats) if abstract_repeats else 0}")
        print("─" * 50)
        
        if empty == 0 and (not abstract_repeats or max(abstract_repeats) <= 2):
            print("✅ MEMÓRIA LIMPA")
            return True
        else:
            print("⚠️ MEMÓRIA POLUÍDA")
            if empty > 5:
                print(f"  - {empty} entradas vazias detectadas")
            if abstract_repeats and max(abstract_repeats) > 2:
                print(f"  - Sequência de {max(abstract_repeats)} abstrações idênticas")
            print("\nRecomendação: executar clean_empty_memories.py")
            return False
            
    except FileNotFoundError:
        print("\n⚠️ angela_memory.jsonl não encontrado")
        print("Sistema pode estar em estado inicial.")
        return True

def main():
    print("="*50)
    print("🔍 VALIDAÇÃO DA CORREÇÃO v2.1.1")
    print("="*50 + "\n")
    
    # Check 1: Arquivo corrigido
    file_ok = check_file_version()
    
    # Check 2: Memória limpa
    memory_ok = check_memory_pollution()
    
    # Resultado final
    print("\n" + "="*50)
    if file_ok and memory_ok:
        print("✅ TUDO PRONTO PARA OPERAÇÃO")
        print("="*50)
        print("\nPróximo passo: python deep_awake.py")
        sys.exit(0)
    elif file_ok and not memory_ok:
        print("⚠️ ARQUIVO OK, MEMÓRIA PRECISA LIMPEZA")
        print("="*50)
        print("\nPróximos passos:")
        print("  1. python clean_empty_memories.py")
        print("  2. python deep_awake.py")
        sys.exit(1)
    else:
        print("❌ CORREÇÃO INCOMPLETA")
        print("="*50)
        print("\nPróximos passos:")
        print("  1. cp deep_awake_FIXED_v2.py deep_awake.py")
        print("  2. python validate_fix.py  (re-executar)")
        sys.exit(2)

if __name__ == "__main__":
    main()
