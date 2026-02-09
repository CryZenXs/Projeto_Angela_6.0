#!/usr/bin/env python3
# clean_empty_memories.py
# Script para remover entradas vazias que causam loop infinito

import json
import os
from datetime import datetime

MEMORY_FILE = "angela_memory.jsonl"
BACKUP_FILE = f"angela_memory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

def clean_empty_memories():
    """
    Remove entradas com angela="" e resposta="" vazios
    que causam loop infinito na governança narrativa.
    """
    
    if not os.path.exists(MEMORY_FILE):
        print(f"❌ Arquivo {MEMORY_FILE} não encontrado!")
        return
    
    # Backup primeiro
    print(f"📦 Criando backup em {BACKUP_FILE}...")
    os.system(f"cp {MEMORY_FILE} {BACKUP_FILE}")
    
    # Carregar todas entradas
    entradas = []
    vazias = 0
    total = 0
    
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                total += 1
                
                # Verificar se está vazio
                angela = data.get("angela", "")
                resposta = data.get("resposta", "")
                
                # Manter se:
                # 1. Tem conteúdo em angela OU resposta
                # 2. É diálogo (não autonomo/metacognicao vazio)
                tipo = "dialogo"
                if isinstance(data.get("user"), dict):
                    tipo = data["user"].get("tipo", "dialogo")
                
                if angela.strip() or resposta.strip():
                    # Tem conteúdo - manter
                    entradas.append(data)
                elif tipo == "dialogo":
                    # Diálogo vazio também manter (pode ser intencional)
                    entradas.append(data)
                else:
                    # Vazio de deep_awake/meta - remover
                    vazias += 1
                    print(f"  🗑️ Removendo: {data.get('ts', 'N/A')} - tipo={tipo}")
            
            except json.JSONDecodeError as e:
                print(f"⚠️ Linha inválida ignorada: {e}")
                continue
    
    # Salvar limpo
    print(f"\n📊 Estatísticas:")
    print(f"   Total original: {total}")
    print(f"   Vazios removidos: {vazias}")
    print(f"   Mantidos: {len(entradas)}")
    print(f"   Redução: {(vazias/total*100):.1f}%")
    
    if vazias > 0:
        print(f"\n💾 Salvando arquivo limpo...")
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            for entry in entradas:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        print(f"✅ Limpeza completa!")
        print(f"\n📝 Para restaurar backup se necessário:")
        print(f"   mv {BACKUP_FILE} {MEMORY_FILE}")
    else:
        print(f"\n✨ Nenhuma entrada vazia encontrada! Memória já está limpa.")
        # Remove backup desnecessário
        os.remove(BACKUP_FILE)

if __name__ == "__main__":
    print("🧹 LIMPEZA DE MEMÓRIAS VAZIAS")
    print("=" * 50)
    print()
    
    clean_empty_memories()
    
    print("\n" + "=" * 50)
    print("✅ Script concluído!")
