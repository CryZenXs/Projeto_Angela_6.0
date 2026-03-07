#!/usr/bin/env python3
# reset_damage.py
# Ferramenta para resetar damage de forma segura e auditável

import json
import os
import argparse
from datetime import datetime

DAMAGE_FILE = "friction_damage.persistent"
AUDIT_LOG = "damage_resets.log"

def reset_damage(level=0.0, reason="manual_reset", reset_endocrine=False):
    """
    Reseta damage para nível especificado.
    
    Args:
        level: Novo valor de damage (0.0 a 1.0)
        reason: Motivo do reset (para auditoria)
        reset_endocrine: Se deve resetar também endocrine_state.json
    """
    if not 0.0 <= level <= 1.0:
        print(f"❌ Erro: level deve estar entre 0.0 e 1.0 (recebido: {level})")
        return False
    
    # Carrega estado atual
    old_data = {}
    if os.path.exists(DAMAGE_FILE):
        try:
            with open(DAMAGE_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível ler arquivo antigo: {e}")
    
    old_damage = old_data.get("damage", 0.0)
    old_load = old_data.get("load", 0.0)
    
    # Cria novo estado
    new_data = {
        "damage": float(level),
        "load": 0.0,  # Sempre reseta load também
        "chronic": False if level < 0.35 else old_data.get("chronic", False),
        "last_updated": datetime.now().isoformat(),
        "total_sessions": old_data.get("total_sessions", 0),
        "version": "2.0.0",
        "last_reset": {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "previous_damage": old_damage,
            "previous_load": old_load
        }
    }
    
    # Salva novo estado
    try:
        with open(DAMAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Damage resetado com sucesso!")
        print(f"   Antes: damage={old_damage:.4f}, load={old_load:.4f}")
        print(f"   Depois: damage={level:.4f}, load=0.0000")
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return False
    
    # Registra em audit log
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | RESET | "
                   f"damage: {old_damage:.4f} → {level:.4f} | "
                   f"load: {old_load:.4f} → 0.0 | "
                   f"reason: {reason}"
                   f"{' | endocrine: RESET' if reset_endocrine else ''}\n")
        print(f"📝 Reset registrado em {AUDIT_LOG}")
    except Exception:
        pass
    
    if reset_endocrine:
        endocrine_file = "endocrine_state.json"
        endo_data = {
            "cortisol": 0.0,
            "oxytocin": 0.0,
            "adrenaline": 0.0,
            "last_damage": float(level),
            "last_update": datetime.now().isoformat()
        }
        try:
            with open(endocrine_file, "w", encoding="utf-8") as f:
                json.dump(endo_data, f, ensure_ascii=False, indent=2)
            print("🧪 Estado endócrino (endocrine_state.json) resetado com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao resetar endócrino: {e}")
            
    return True

def show_current_state():
    """Mostra estado atual de damage"""
    if not os.path.exists(DAMAGE_FILE):
        print("ℹ️ Arquivo de damage não existe ainda.")
        print("   Será criado na primeira execução do sistema.")
        return
    
    try:
        with open(DAMAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print("\n📊 ESTADO ATUAL:")
        print(f"   Damage: {data.get('damage', 0.0):.4f}")
        print(f"   Load: {data.get('load', 0.0):.4f}")
        print(f"   Chronic: {data.get('chronic', False)}")
        print(f"   Sessions: {data.get('total_sessions', 0)}")
        print(f"   Última atualização: {data.get('last_updated', 'N/A')}")
        
        if "last_reset" in data:
            print(f"\n   Último reset:")
            print(f"     Quando: {data['last_reset'].get('timestamp', 'N/A')}")
            print(f"     Motivo: {data['last_reset'].get('reason', 'N/A')}")
    
    except Exception as e:
        print(f"❌ Erro ao ler estado: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Ferramenta para resetar damage do sistema Ângela",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s --show                           # Ver estado atual
  %(prog)s --level 0.0 --reason bug_fix    # Resetar para 0
  %(prog)s --level 0.3 --reason test       # Resetar para 0.3
        """
    )
    
    parser.add_argument(
        "--show",
        action="store_true",
        help="Mostrar estado atual (não reseta)"
    )
    
    parser.add_argument(
        "--level",
        type=float,
        help="Novo nível de damage (0.0 a 1.0)"
    )
    
    parser.add_argument(
        "--reason",
        type=str,
        default="manual_reset",
        help="Motivo do reset (para auditoria)"
    )

    parser.add_argument(
        "--reset-endocrine",
        action="store_true",
        help="Zera também endocrine_state.json"
    )
    
    args = parser.parse_args()
    
    if args.show:
        show_current_state()
    elif args.level is not None:
        reset_damage(args.level, args.reason, args.reset_endocrine)
    else:
        parser.print_help()
        print("\n" + "="*60)
        show_current_state()

if __name__ == "__main__":
    main()
