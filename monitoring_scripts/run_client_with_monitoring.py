#!/usr/bin/env python3
"""
Wrapper para rodar o cliente FL e coletar métricas de hardware simultaneamente.

O script faz o seguinte:
1. Limpa métricas antigas (se houver)
2. Inicia o monitor.sh em background (processo separado)
3. Roda o client.py e espera ele terminar
4. Garante que o monitor.sh seja encerrado no final

Uso: python run_client_with_monitoring.py
"""

import os
import sys
import subprocess
import signal
import atexit
import shutil
from pathlib import Path


class MonitoringWrapper:
    def __init__(self):
        self.monitoring_pid = None
        self.app_folder = Path(__file__).parent
        self.monitor_script = self.app_folder / "monitor.sh"
        self.client_script = self.app_folder / "client.py"
        self.metrics_dir = self.app_folder / "logs"
        
        # Para o monitor mesmo se o processo for morto externamente
        atexit.register(self.stop_monitoring)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print(f"\n[Wrapper] Sinal {signum} recebido. Encerrando...")
        self.stop_monitoring()
        sys.exit(0)
    
    def clean_old_metrics(self):
        # Limpa pasta de métricas antiga para não misturar dados de rounds diferentes
        if self.metrics_dir.exists():
            try:
                shutil.rmtree(self.metrics_dir)
                print(f"[Wrapper] Métricas antigas removidas: {self.metrics_dir}")
            except Exception as e:
                print(f"[Wrapper] Aviso: não consegui limpar métricas antigas: {e}")
        
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
    
    def start_monitoring(self):
        if not self.monitor_script.exists():
            print(f"[Wrapper] Aviso: {self.monitor_script} não encontrado. Monitoramento pulado.")
            return
        
        try:
            print(f"[Wrapper] Iniciando monitoramento de hardware...")
            # setsid cria um grupo de processos separado, assim dá pra matar o monitor e os filhos (ex: tegrastats) de uma vez
            process = subprocess.Popen(
                ['bash', str(self.monitor_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            self.monitoring_pid = process.pid
            print(f"[Wrapper] Monitoramento iniciado (PID: {self.monitoring_pid})")
            
            # Salva PID para cleanup de emergência
            with open(self.app_folder / 'monitor.pid', 'w') as f:
                f.write(str(self.monitoring_pid))
        except Exception as e:
            print(f"[Wrapper] Erro ao iniciar monitoramento: {e}")
    
    def stop_monitoring(self):
        if self.monitoring_pid is None:
            return
        
        try:
            # Mata o monitor e todos os subprocessos do grupo
            os.killpg(os.getpgid(self.monitoring_pid), signal.SIGTERM)
            print(f"[Wrapper] Monitoramento encerrado.")
            self.monitoring_pid = None
            
            pid_file = self.app_folder / 'monitor.pid'
            if pid_file.exists():
                pid_file.unlink()
        except ProcessLookupError:
            pass  # processo já encerrado
        except Exception as e:
            print(f"[Wrapper] Erro ao parar monitoramento: {e}")
    
    def run_client(self):
        if not self.client_script.exists():
            print(f"[Wrapper] Erro: {self.client_script} não encontrado!")
            sys.exit(1)
        
        print(f"[Wrapper] Executando client.py...")
        try:
            # Roda o client.py bloqueando este processo até terminar
            result = subprocess.run(
                [sys.executable, str(self.client_script)],
                cwd=str(self.app_folder)
            )
            return result.returncode
        except KeyboardInterrupt:
            print("\n[Wrapper] Interrompido pelo usuário.")
            return 130
        except Exception as e:
            print(f"[Wrapper] Erro ao rodar client.py: {e}")
            return 1
    
    def run(self):
        print("=" * 50)
        print("HIAAC FL Testbed - Client Wrapper")
        print("=" * 50)
        
        self.clean_old_metrics()
        self.start_monitoring()
        
        exit_code = self.run_client()
        
        self.stop_monitoring()
        
        print("=" * 50)
        print(f"Finalizado (exit code: {exit_code})")
        
        return exit_code


if __name__ == "__main__":
    wrapper = MonitoringWrapper()
    sys.exit(wrapper.run())
