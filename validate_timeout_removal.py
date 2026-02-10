#!/usr/bin/env python3
"""
Validação: Remoção de Timeouts do Projeto Ângela
Data: 10 Fevereiro 2026
"""

import os
import re

def check_core_py():
    """Verifica se core.py está sem timeout e com limites aumentados"""
    print("🔍 Verificando core.py...")
    
    with open('/mnt/project/core.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "timeout removido": "timeout=" not in content,
        "except Timeout removido": "except requests.exceptions.Timeout:" not in content,
        "limite iterações 10000": "if i > 10000:" in content,
        "limite caracteres 16000": "if len(text) > 16000:" in content,
    }
    
    all_passed = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False
    
    return all_passed

def check_other_files():
    """Verifica se há timeouts em outros arquivos"""
    print("\n🔍 Verificando outros arquivos Python...")
    
    project_path = '/mnt/project'
    timeout_found = False
    
    for filename in os.listdir(project_path):
        if filename.endswith('.py') and filename != 'core.py':
            filepath = os.path.join(project_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(r'timeout\s*=\s*\d+', content, re.IGNORECASE):
                        print(f"  ⚠️  {filename}: contém timeout")
                        timeout_found = True
            except:
                pass
    
    if not timeout_found:
        print("  ✅ Nenhum timeout encontrado em outros arquivos")
    
    return not timeout_found

def main():
    print("="*60)
    print("🔧 VALIDAÇÃO: REMOÇÃO DE TIMEOUTS")
    print("="*60 + "\n")
    
    core_ok = check_core_py()
    others_ok = check_other_files()
    
    print("\n" + "="*60)
    if core_ok and others_ok:
        print("✅ TODAS AS VERIFICAÇÕES PASSARAM")
        print("\nMudanças aplicadas:")
        print("  • Timeout HTTP removido (era 120s)")
        print("  • Tratamento de erro Timeout removido")
        print("  • Limite de iterações: 1200 → 10000")
        print("  • Limite de caracteres: 4000 → 16000")
        print("\nO sistema agora pode processar respostas")
        print("arbitrariamente longas sem interrupção por timeout.")
    else:
        print("❌ ALGUMAS VERIFICAÇÕES FALHARAM")
        print("\nRevise os arquivos manualmente.")
    print("="*60)

if __name__ == "__main__":
    main()
