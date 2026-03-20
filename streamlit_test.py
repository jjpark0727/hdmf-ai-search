"""
streamlit_test.py - Streamlit 웹 인터페이스

모드:
  - interactive_doc  : 파일 업로드 → 임베딩 → 질문 (문서 기반 RAG)
  - interactive_chat : 파일 없이 바로 질문 (채팅 전용)
"""

import sys
import shutil
import streamlit as st
from pathlib import Path

# 프로젝트 루트를 import 경로에 추가
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config import PDF_DIR, VECTORSTORE_DIR, ensure_directories
from ingest import ingest_documents, load_uploaded_files
from main import run_chat


# ─────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────

def init_session():
    """세션 상태 기본값 초기화"""
    defaults = {
        "messages":      [],
        "embedded":      False,
        "thread_id":     "streamlit_1",
        "input_counter": 0,
        "shutdown":      False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def save_pdfs_to_dir(uploaded_files: list):
    """업로드된 파일을 PDF_DIR 에 저장 (기존 파일 제거 후 저장)"""
    ensure_directories()
    for existing in PDF_DIR.glob("*.pdf"):
        existing.unlink()
    for uf in uploaded_files:
        (PDF_DIR / uf.name).write_bytes(uf.getbuffer())


def reset_all():
    """tmp 파일 + 세션 상태 완전 초기화"""
    # 1. /tmp PDF 및 벡터스토어 삭제
    try:
        if PDF_DIR.exists():
            shutil.rmtree(PDF_DIR)
        if VECTORSTORE_DIR.exists():
            shutil.rmtree(VECTORSTORE_DIR)
        ensure_directories()  # 빈 폴더 재생성
    except Exception as e:
        st.warning(f"파일 삭제 중 오류: {e}")

    # 2. 세션 상태 전체 초기화
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ─────────────────────────────────────────────
# 메인 화면
# ─────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="HDMF AI Search",
        page_icon="🤖",
        layout="wide",
    )
    init_session()

    # ── 헤더 (제목 + 초기화 버튼) ──────────────────
    title_col, quit_col = st.columns([11, 1])
    with title_col:
        st.title("HDMF AI Search")
    with quit_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("초기화", key="quit_btn", use_container_width=True):
            st.session_state.shutdown = True
            st.rerun()

    # ── 초기화 처리 ───────────────────────────────
    if st.session_state.shutdown:
        reset_all()
        st.success("✅ 초기화 완료! 새 문서를 업로드하세요.")
        st.stop()

    # ── 채팅 메시지 영역 ─────────────────────────
    chat_area = st.container(height=480)
    with chat_area:
        if not st.session_state.messages:
            st.caption("아직 대화가 없습니다. 아래에서 질문을 입력하세요.")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    st.divider()

    # ── 문서 업로드 (3개 슬롯) ──────────────────
    st.markdown("**문서 업로드** (선택사항 — 비워두면 채팅 전용 모드)")
    uc1, uc2, uc3 = st.columns(3)
    with uc1:
        f1 = st.file_uploader("문서 1", type="pdf", key="fu1")
    with uc2:
        f2 = st.file_uploader("문서 2", type="pdf", key="fu2")
    with uc3:
        f3 = st.file_uploader("문서 3", type="pdf", key="fu3")

    uploaded = [f for f in [f1, f2, f3] if f is not None]
    has_files = len(uploaded) > 0

    # 파일이 사라지면 embedded 상태 초기화
    if not has_files and st.session_state.embedded:
        st.session_state.embedded = False

    # ── 임베딩 버튼 ──────────────────────────────
    embed_col, _ = st.columns([2, 8])
    with embed_col:
        if st.button(
            "임베딩",
            disabled=not has_files or st.session_state.embedded,
            type="primary",
            key="embed_btn",
            use_container_width=True,
        ):
            save_pdfs_to_dir(uploaded)
            with st.spinner("문서 임베딩 중... 잠시 기다려 주세요."):
                try:
                    ingest_documents()
                    st.session_state.embedded = True
                except ValueError as e:
                    st.error(f"❗ 문서 처리 실패: {e}")
            st.rerun()

    # ── 모드 상태 표시 ───────────────────────────
    if has_files and st.session_state.embedded:
        mode = "interactive_doc"
        st.success("✅ 임베딩 완료 — 📄 문서 기반 RAG 모드 (interactive_doc)")
    elif has_files and not st.session_state.embedded:
        mode = None
        st.warning("⚠️ 임베딩 버튼을 눌러 문서를 처리하세요.")
    else:
        mode = "interactive_chat"
        st.info("💬 채팅 전용 모드 (interactive_chat) — 파일 없이 바로 질문 가능")

    st.divider()

    # ── 입력 영역 ────────────────────────────────
    send_enabled = mode is not None

    input_key = f"user_input_{st.session_state.input_counter}"
    inp_col, send_col = st.columns([9, 1])

    with inp_col:
        user_input = st.text_input(
            "질문",
            placeholder="질문을 입력하세요..." if send_enabled else "임베딩 완료 후 입력 가능합니다.",
            label_visibility="collapsed",
            key=input_key,
            disabled=not send_enabled,
        )

    with send_col:
        send_clicked = st.button(
            "Send",
            type="primary",
            disabled=not (send_enabled and bool(user_input)),
            use_container_width=True,
            key="send_btn",
        )

    # ── Send 처리 ────────────────────────────────
    if send_clicked and user_input and mode:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.spinner("응답 생성 중..."):
            try:
                if mode == "interactive_doc":
                    uploaded_files_info = load_uploaded_files()
                    response = run_chat(
                        question=user_input,
                        thread_id=st.session_state.thread_id,
                        uploaded_files=uploaded_files_info,
                        verbose=False,
                    )
                else:  # interactive_chat
                    response = run_chat(
                        question=user_input,
                        thread_id=st.session_state.thread_id,
                        uploaded_files=None,
                        verbose=False,
                    )

                assistant_msg = response or "응답을 생성하지 못했습니다."

            except Exception as e:
                assistant_msg = f"오류가 발생했습니다: {e}"
                st.error(assistant_msg)

        st.session_state.messages.append({"role": "assistant", "content": assistant_msg})
        st.session_state.input_counter += 1
        st.rerun()


if __name__ == "__main__":
    main()
