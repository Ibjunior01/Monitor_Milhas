"""
Entry point do Monitor de Milhas.
Uso: python main.py
"""
import sys
from src.monitor import executar_varredura
from src.logger import get_logger

log = get_logger("main")


def main():
    try:
        resumo = executar_varredura()
        print("\n" + "=" * 50)
        print("  VARREDURA CONCLUÍDA")
        print("=" * 50)
        print(f"  Total coletado   : {resumo['total_coletados']}")
        print(f"  Itens novos      : {resumo['novos']}")
        print(f"  Relevantes       : {resumo['relevantes']}")
        print(f"  Aprovadas        : {resumo['aprovadas']}")
        print(f"  Alertas enviados : {resumo['alertas_enviados']}")
        print(f"  Ignoradas        : {resumo['ignoradas']}")
        print("=" * 50)
        print("  Abra o dashboard: streamlit run dashboard.py")
        print("=" * 50 + "\n")
    except KeyboardInterrupt:
        log.info("Varredura interrompida pelo usuário.")
        sys.exit(0)
    except Exception as e:
        log.exception(f"Erro crítico durante varredura: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
