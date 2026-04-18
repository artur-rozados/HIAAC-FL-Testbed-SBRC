import os
import time
import zipfile
from io import BytesIO
from pathlib import Path
import subprocess
import shutil
import threading
import streamlit as st
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

try:
    import pandas as pd
    import plotly.graph_objects as go
    _CHARTS_AVAILABLE = True
except ImportError:
    _CHARTS_AVAILABLE = False

try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
except Exception:
    st_autorefresh = None

DEVICE_IPS = [
    "10.10.20.201",
    "10.10.20.202",
    "10.10.20.203",
    "10.10.20.204",
    "10.10.20.205",
    "10.10.20.206",
    "10.10.20.207",
    "10.10.20.208",
    "10.10.20.209",
    "10.10.20.231",
    "10.10.20.232",
    "10.10.20.233",
    "10.10.20.234",
    "10.10.20.235",
    "10.10.20.236",
]

DEVICE_NAMES = {
    "10.10.20.201": "Raspberry Pi 1",
    "10.10.20.202": "Raspberry Pi 2",
    "10.10.20.203": "Raspberry Pi 3",
    "10.10.20.204": "Raspberry Pi 4",
    "10.10.20.205": "Raspberry Pi 5",
    "10.10.20.206": "Raspberry Pi 6",
    "10.10.20.207": "Raspberry Pi 7",
    "10.10.20.208": "Raspberry Pi 8",
    "10.10.20.209": "Raspberry Pi 9",
    "10.10.20.231": "Jetson 1",
    "10.10.20.232": "Jetson 2",
    "10.10.20.233": "Jetson 3",
    "10.10.20.234": "Jetson 4",
    "10.10.20.235": "Jetson 5",
    "10.10.20.236": "Jetson 6",
}

DEVICE_STATUS = {ip: {"online": None, "last_checked": None} for ip in DEVICE_IPS}
DEVICE_STATUS_LOCK = threading.Lock()
DEVICE_MONITOR_INTERVAL_SECONDS = 5

CUSTOM_CSS = """
<style>
:root {
    --card-bg: #0f172a;
    --card-border: rgba(255,255,255,0.08);
    --text-muted: #9ca3af;
}

section.main > div {
    padding-top: 0 !important;
}

.section-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 18px 35px rgba(15,23,42,0.35);
}

.device-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.7rem;
    margin-top: 0.85rem;
    max-height: 320px;
    overflow-y: auto;
    padding-right: 0.25rem;
}

.device-card {
    border-radius: 16px;
    padding: 0.85rem 1rem;
    border: 1px solid rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.02);
}

.device-card.online {
    border-color: rgba(34,197,94,0.8);
}

.device-card.offline {
    border-color: rgba(248,113,113,0.8);
}

.status-dot {
    height: 10px;
    width: 10px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 8px;
}

.status-dot.online {
    background: #22c55e;
    box-shadow: 0 0 8px rgba(34,197,94,0.8);
}

.status-dot.offline {
    background: #f87171;
    box-shadow: 0 0 8px rgba(248,113,113,0.8);
}

.status-dot.muted {
    background: var(--text-muted);
    box-shadow: none;
}

.secondary-text {
    font-size: 0.85rem;
    color: var(--text-muted);
}

button[kind="secondary"] {
    border-radius: 999px;
}
</style>
"""


def ping_once(ip: str) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return result.returncode == 0
    except Exception:
        return False


def device_monitor_loop() -> None:
    while True:
        refresh_device_status_now()
        time.sleep(DEVICE_MONITOR_INTERVAL_SECONDS)


def refresh_device_status_now() -> None:
    for ip in DEVICE_IPS:
        is_online = ping_once(ip)
        with DEVICE_STATUS_LOCK:
            DEVICE_STATUS[ip] = {
                "online": is_online,
                "last_checked": time.time(),
            }


def ensure_device_monitor_running() -> None:
    if st.session_state.get("device_monitor_started"):
        return
    thread = threading.Thread(target=device_monitor_loop, daemon=True)
    thread.start()
    st.session_state["device_monitor_started"] = True


def get_device_status_snapshot() -> dict:
    with DEVICE_STATUS_LOCK:
        return {ip: status.copy() for ip, status in DEVICE_STATUS.items()}


def render_device_status_section() -> None:
    snapshot = get_device_status_snapshot()
    known = [s for s in snapshot.values() if s["online"] is not None]
    online_total = sum(1 for s in known if s["online"])
    offline_total = sum(1 for s in known if s["online"] is False)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### 🔌 Monitoramento em tempo real")
    top_cols = st.columns([3, 1])
    with top_cols[0]:
        st.caption("Acompanhe as Jetsons e Raspberry Pis sem precisar atualizar manualmente.")
    with top_cols[1]:
        if st.button("🔄 Verificar agora", width="stretch", key="btn_manual_refresh"):
            with st.spinner("Atualizando status dos dispositivos..."):
                refresh_device_status_now()
            snapshot = get_device_status_snapshot()
            st.success("Status atualizado.")

    metric_cols = st.columns(3)
    metric_cols[0].metric("Monitorados", len(DEVICE_IPS))
    metric_cols[1].metric("Online", online_total)
    metric_cols[2].metric("Offline", offline_total)

    cards_html = ["<div class='device-grid'>"]
    for ip in DEVICE_IPS:
        info = snapshot.get(ip, {"online": None, "last_checked": None})
        status = info.get("online")
        last_checked = info.get("last_checked")
        status_class = "online" if status else "offline"
        if status is None:
            status_class = "unknown"
        dot_class = "online" if status else "offline"
        if status is None:
            dot_class = "muted"
        label = "Online" if status else "Offline"
        if status is None:
            label = "Aguardando..."
        time_label = ""
        if last_checked:
            time_label = time.strftime("%H:%M:%S", time.localtime(last_checked))

        card_html = (
            f"<div class='device-card {status_class}'>"
            f"<div><span class='status-dot {dot_class}'></span><strong>{DEVICE_NAMES.get(ip, ip)}</strong></div>"
            f"<div class='secondary-text'>IP: {ip}</div>"
            f"<div class='secondary-text'>{label}{(' • ' + time_label) if time_label else ''}</div>"
            "</div>"
        )
        cards_html.append(card_html)
    cards_html.append("</div>")
    st.markdown("".join(cards_html), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if not st_autorefresh:
        st.caption("Dica: pressione R para atualizar rapidamente caso esteja sem auto-refresh.")


def safe_extract(zip_file: zipfile.ZipFile, path: Path) -> list:
    extracted = []
    for member in zip_file.infolist():
        member_path = Path(member.filename)
        dest_path = (path / member_path).resolve()
        if not str(dest_path).startswith(str(path.resolve())):
            raise Exception(f"Unsafe zip file path: {member.filename}")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if member.is_dir():
            dest_path.mkdir(exist_ok=True)
            continue
        with zip_file.open(member) as source, open(dest_path, "wb") as target:
            target.write(source.read())
        extracted.append(str(dest_path))
    return extracted


def make_logs_zip_bytes(logs_path: Path, include_pcaps: bool = False) -> bytes:
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        for root, _, files in os.walk(logs_path):
            for fname in files:
                # Pular pcaps se não solicitado
                if fname.endswith('.pcap') and not include_pcaps:
                    continue
                    
                fpath = Path(root) / fname
                arcname = os.path.relpath(fpath, start=str(logs_path))
                # Não comprimir pcaps (binários grandes, não comprimem bem)
                compress_type = ZIP_STORED if fname.endswith('.pcap') else ZIP_DEFLATED
                zf.write(fpath, arcname=arcname, compress_type=compress_type)
    buf.seek(0)
    return buf.getvalue()


def render_upload_tab() -> None:
    st.markdown("#### 📁 Upload e extração")
    st.write("Envie um ZIP e deixe o sistema extrair automaticamente para `files_to_copy/`.")

    uploaded = st.file_uploader("Selecione um arquivo .zip", type=["zip"], key="zip_uploader")
    if uploaded is None:
        return

    target_dir = Path("files_to_copy")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Limpar arquivos antigos antes de extrair os novos
    for item in target_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    
    save_path = target_dir / Path(uploaded.name).name

    with open(save_path, "wb") as f:
        f.write(uploaded.getbuffer())
    st.success(f"Arquivo salvo em {save_path}")

    try:
        with zipfile.ZipFile(save_path, "r") as zf:
            with st.spinner("Extraindo conteúdo..."):
                extracted = safe_extract(zf, target_dir)
        
        # Remover o arquivo ZIP após extração bem-sucedida
        save_path.unlink()
        
        if extracted:
            preview = "\n".join([os.path.relpath(p, start=str(target_dir)) for p in extracted[:200]])
            st.text_area("Arquivos extraídos", value=preview, height=220)
        else:
            st.info("Zip sem arquivos (apenas diretórios ou vazio).")
    except zipfile.BadZipFile:
        st.error("O arquivo enviado não é um ZIP válido.")
    except Exception as exc:
        st.error(f"Falha ao extrair: {exc}")

    (target_dir / "logs").mkdir(exist_ok=True)


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, cwd=str(Path.cwd()))


def render_command_result(proc: subprocess.CompletedProcess, success_message: str) -> None:
    if proc.returncode == 0:
        st.success(success_message)
    else:
        st.error(f"Comando retornou código {proc.returncode}.")
    with st.expander("stdout", expanded=True):
        st.code(proc.stdout or "(sem saída)")
    with st.expander("stderr"):
        st.code(proc.stderr or "(sem erros)")


def render_operations_tab() -> None:
    st.markdown("#### ⚙️ Deploy & scripts")
    deploy_col, scripts_col = st.columns(2, gap="large")

    with deploy_col:
        st.markdown("##### 📦 Deploy Ansible")
        st.caption("Executa `ansible/build.yaml` com as credenciais do vault.")
        if st.button("Executar ansible-playbook", width="stretch", key="btn_ansible"):
            vault_file = Path.home() / ".ansible_vault_pass"
            if shutil.which("ansible-playbook") is None:
                st.error("`ansible-playbook` não está disponível no PATH.")
            elif not vault_file.exists():
                st.error("Arquivo ~/.ansible_vault_pass não encontrado.")
            else:
                cmd = [
                    "ansible-playbook",
                    "-i",
                    "ansible/inventory",
                    "ansible/build.yaml",
                    "--vault-password-file",
                    str(vault_file),
                    "-e",
                    "PYTHON_VERSION=python3.11",
                ]
                with st.spinner("Executando playbook..."):
                    proc = run_command(cmd)
                render_command_result(proc, "Playbook executado com sucesso.")

    with scripts_col:
        st.markdown("##### 🖥️ Scripts locais")
        col_run, col_stop = st.columns(2)
        with col_run:
            if st.button("Rodar run.sh", width="stretch", key="btn_run_sh"):
                script = Path("run.sh")
                if not script.exists():
                    st.error("run.sh não encontrado na raiz do projeto.")
                else:
                    with st.spinner("Executando run.sh..."):
                        proc = run_command(["bash", str(script)])
                    render_command_result(proc, "run.sh finalizado.")
        with col_stop:
            if st.button("Forçar stop", width="stretch", key="btn_stop_sh"):
                script = Path("force_stop.sh")
                if not script.exists():
                    st.error("force_stop.sh não encontrado.")
                else:
                    with st.spinner("Executando force_stop.sh..."):
                        proc = run_command(["bash", str(script)])
                    render_command_result(proc, "force_stop.sh finalizado.")


def render_logs_tab() -> None:
    st.markdown("#### 🗂️ Logs dos clientes")
    st.write("Gera pacotes com logs de métricas, treinamento e/ou captura de rede.")
    logs_dir = Path.home() / "app/logs"
    if not logs_dir.exists():
        st.warning("Diretório ~/app/logs não encontrado.")
        return

    col1, col2 = st.columns(2)
    
    # Botão para logs sem pcap
    with col1:
        if st.button("📊 Baixar Logs (CSV/métricas)", width="stretch", key="btn_logs_only"):
            try:
                with st.spinner("Compactando logs..."):
                    zip_bytes = make_logs_zip_bytes(logs_dir, include_pcaps=False)
                if not zip_bytes:
                    st.info("Nenhum log encontrado.")
                else:
                    st.success("Pacote pronto!")
                    st.download_button(
                        label="⬇️ Download logs.zip (~2MB)",
                        data=zip_bytes,
                        file_name="logs.zip",
                        mime="application/zip",
                        width="stretch",
                        key="btn_logs_download",
                    )
            except Exception as exc:
                st.error(f"Erro ao gerar ZIP: {exc}")
    
    # Botão para pcap
    with col2:
        if st.button("📡 Baixar PCAP + Logs", width="stretch", key="btn_pcap_only"):
            try:
                with st.spinner("Preparando pcap + logs..."):
                    zip_bytes = make_logs_zip_bytes(logs_dir, include_pcaps=True)
                if not zip_bytes:
                    st.info("Nenhum pcap encontrado.")
                else:
                    st.success("Pacote pronto!")
                    st.download_button(
                        label="⬇️ Download logs+pcap.zip (~1.8GB)",
                        data=zip_bytes,
                        file_name="logs_with_pcap.zip",
                        mime="application/zip",
                        width="stretch",
                        key="btn_pcap_download",
                    )
            except Exception as exc:
                st.error(f"Erro ao gerar ZIP: {exc}")


def _load_fl_csvs(logs_dir: Path) -> tuple[list, list, list]:
    """Retorna (train_frames, eval_frames, hw_frames) com coluna 'client' adicionada."""
    train_frames, eval_frames, hw_frames = [], [], []
    for client_dir in sorted(logs_dir.iterdir()):
        if not client_dir.is_dir() or client_dir.name == "pcaps":
            continue
        client = client_dir.name.replace("client-", "")
        for fname, frames, cols in [
            ("train.csv", train_frames, ["round", "epoch", "accuracy", "loss"]),
            ("evaluate.csv", eval_frames, ["round", "epoch", "accuracy", "loss"]),
        ]:
            fpath = client_dir / fname
            if fpath.exists():
                try:
                    df = pd.read_csv(fpath, header=None, names=cols)
                    df["client"] = client
                    frames.append(df)
                except Exception:
                    pass
        hw_path = client_dir / "hardware_metrics.csv"
        if hw_path.exists():
            try:
                df = pd.read_csv(hw_path)
                df["client"] = client
                hw_frames.append(df)
            except Exception:
                pass
    return train_frames, eval_frames, hw_frames


def render_charts_tab() -> None:
    if not _CHARTS_AVAILABLE:
        st.error("Instale as dependências: `pip install pandas plotly`")
        return

    logs_dir = Path.home() / "app/logs"
    if not logs_dir.exists():
        st.warning("Diretório ~/app/logs não encontrado. Execute um experimento primeiro.")
        return

    train_frames, eval_frames, hw_frames = _load_fl_csvs(logs_dir)

    if not train_frames and not eval_frames:
        st.info("Nenhum dado de treinamento encontrado em ~/app/logs.")
        return

    # ── Gráficos de Treino ────────────────────────────────────────────────────
    if train_frames:
        train_df = pd.concat(train_frames, ignore_index=True)
        # Agrupa por round, tira média entre clientes
        agg = train_df.groupby("round")[["accuracy", "loss"]].mean().reset_index()

        st.markdown("#### 📈 Treinamento (média entre clientes)")
        col_acc, col_loss = st.columns(2)

        with col_acc:
            fig = go.Figure()
            # Linha por cliente
            for client_df in train_frames:
                client = client_df["client"].iloc[0]
                fig.add_trace(go.Scatter(
                    x=client_df["round"], y=client_df["accuracy"],
                    mode="lines", name=client, opacity=0.4, showlegend=True,
                ))
            # Média
            fig.add_trace(go.Scatter(
                x=agg["round"], y=agg["accuracy"],
                mode="lines+markers", name="Média",
                line=dict(width=1, color="red"),
            ))
            fig.update_layout(title="Accuracy por Round", xaxis_title="Round",
                              yaxis_title="Accuracy", legend_title="Cliente",
                              height=350, margin=dict(t=40, b=20))
            st.plotly_chart(fig, width="stretch")

        with col_loss:
            fig = go.Figure()
            for client_df in train_frames:
                client = client_df["client"].iloc[0]
                fig.add_trace(go.Scatter(
                    x=client_df["round"], y=client_df["loss"],
                    mode="lines", name=client, opacity=0.4, showlegend=True,
                ))
            fig.add_trace(go.Scatter(
                x=agg["round"], y=agg["loss"],
                mode="lines+markers", name="Média",
                line=dict(width=1, color="red"),
            ))
            fig.update_layout(title="Loss por Round", xaxis_title="Round",
                              yaxis_title="Loss", legend_title="Cliente",
                              height=350, margin=dict(t=40, b=20))
            st.plotly_chart(fig, width="stretch")

    # ── Gráficos de Avaliação ─────────────────────────────────────────────────
    if eval_frames:
        eval_df = pd.concat(eval_frames, ignore_index=True)
        agg_eval = eval_df.groupby("round")[["accuracy", "loss"]].mean().reset_index()

        st.markdown("#### 🧪 Avaliação (média entre clientes)")
        col_acc2, col_loss2 = st.columns(2)

        with col_acc2:
            fig = go.Figure()
            for client_df in eval_frames:
                client = client_df["client"].iloc[0]
                fig.add_trace(go.Scatter(
                    x=client_df["round"], y=client_df["accuracy"],
                    mode="lines", name=client, opacity=0.4, showlegend=True,
                ))
            fig.add_trace(go.Scatter(
                x=agg_eval["round"], y=agg_eval["accuracy"],
                mode="lines+markers", name="Média",
                line=dict(width=1, color="red"),
            ))
            fig.update_layout(title="Accuracy por Round", xaxis_title="Round",
                              yaxis_title="Accuracy", height=350, margin=dict(t=40, b=20))
            st.plotly_chart(fig, width="stretch")

        with col_loss2:
            fig = go.Figure()
            for client_df in eval_frames:
                client = client_df["client"].iloc[0]
                fig.add_trace(go.Scatter(
                    x=client_df["round"], y=client_df["loss"],
                    mode="lines", name=client, opacity=0.4, showlegend=True,
                ))
            fig.add_trace(go.Scatter(
                x=agg_eval["round"], y=agg_eval["loss"],
                mode="lines+markers", name="Média",
                line=dict(width=1, color="red"),
            ))
            fig.update_layout(title="Loss por Round", xaxis_title="Round",
                              yaxis_title="Loss", height=350, margin=dict(t=40, b=20))
            st.plotly_chart(fig, width="stretch")

    # ── Hardware ──────────────────────────────────────────────────────────────
    if hw_frames:
        st.markdown("#### 🖥️ Hardware (por cliente)")
        hw_df = pd.concat(hw_frames, ignore_index=True)
        if "timestamp" not in hw_df.columns:
            st.warning("Coluna 'timestamp' não encontrada nos dados de hardware.")
            return

        hw_df["timestamp"] = pd.to_datetime(hw_df["timestamp"], errors="coerce")
        hw_df = hw_df.dropna(subset=["timestamp"])

        if hw_df.empty:
            st.warning("Nenhum dado de hardware válido encontrado.")
            return

        # Normaliza colunas numéricas para evitar falhas quando CSV chega como texto.
        numeric_cols = [
            "cpu_temp_C",
            "core_voltage_V",
            "cpu_load_1min",
            "mem_usage_percent",
            "mem_used_MB",
            "cpu_usage_percent",
            "power_mW",
        ]
        for col in numeric_cols:
            if col in hw_df.columns:
                hw_df[col] = pd.to_numeric(hw_df[col], errors="coerce")

        # Distingue clientes Raspberry Pi e Jetson pelo nome da pasta do cliente.
        hw_df["client_kind"] = hw_df["client"].astype(str).str.lower().apply(
            lambda name: "jetson" if "jetson" in name else "pi"
        )

        st.caption("Nos logs atuais, Raspberry Pi não envia CPU em %; envia CPU Load (1/5/15 min).")

        metric_options = {
            "Temperatura CPU (°C) - Pis": ("cpu_temp_C", "pi"),
            "Uso de Memória (%)": ("mem_usage_percent", None),
            "Uso de Memória (MB)": ("mem_used_MB", None),
            "Tensão de Core (V) - Pis": ("core_voltage_V", "pi"),
            "CPU Load 1min - Pis": ("cpu_load_1min", "pi"),
            "CPU (% uso) - Jetsons": ("cpu_usage_percent", "jetson"),
            "Energia/Potência (mW) - Jetsons": ("power_mW", "jetson"),
        }
        selected = st.multiselect(
            "Métricas de hardware",
            list(metric_options.keys()),
            default=list(metric_options.keys()),
        )

        for label in selected:
            col, client_scope = metric_options[label]
            if col not in hw_df.columns:
                st.warning(f"Coluna '{col}' não encontrada nos dados.")
                continue

            scoped_df = hw_df
            if client_scope is not None:
                scoped_df = hw_df[hw_df["client_kind"] == client_scope]

            if scoped_df.empty:
                st.info(f"Sem dados para '{label}' no grupo selecionado.")
                continue

            fig = go.Figure()
            plotted = 0
            for client, grp in scoped_df.groupby("client"):
                data = grp[["timestamp", col]].dropna().sort_values("timestamp")
                if data.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=data["timestamp"], y=data[col],
                    mode="lines", name=client,
                ))

                plotted += 1

            if plotted == 0:
                st.info(f"Sem amostras válidas para '{label}'.")
                continue

            fig.update_layout(title=label, xaxis_title="Tempo",
                              yaxis_title=label, height=300, margin=dict(t=40, b=20))
            st.plotly_chart(fig, width="stretch")


def main() -> None:
    st.set_page_config(page_title="HIAAC Testbed Console", layout="wide", page_icon="🛰️")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if st_autorefresh:
        st_autorefresh(interval=5_000, key="device-status-refresh")

    ensure_device_monitor_running()

    st.title("HIAAC Federated Learning Testbed")
    st.caption("Operações remotas de dispositivos, deploy e coleta de logs em um único painel.")

    render_device_status_section()

    tabs = st.tabs(["Arquivos", "Operações", "Logs", "Gráficos"])
    with tabs[0]:
        render_upload_tab()
    with tabs[1]:
        render_operations_tab()
    with tabs[2]:
        render_logs_tab()
    with tabs[3]:
        render_charts_tab()


def bootstrap_old_interface_backup() -> None:
    backup = Path("streamlit_app_old.py")
    if backup.exists():
        st.caption("Uma cópia do layout anterior foi mantida em streamlit_app_old.py para referência.")


if __name__ == "__main__":
    main()
    bootstrap_old_interface_backup()
