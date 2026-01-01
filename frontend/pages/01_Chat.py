"""
Main Chat Page (리팩토링됨)
불필요한 래퍼 함수 제거, 새로운 컴포넌트 구조 적용
"""

import streamlit as st
import asyncio
import threading
import os
import sys
import time
import requests

try:
    from streamlit.runtime.scriptrunner_utils.exceptions import StopException
except Exception:
    StopException = None

if os.getenv("LANGSMITH_TRACING", "").lower() == "true" and os.getenv(
    "ENABLE_LANGSMITH_IN_STREAMLIT", "false"
).lower() != "true":
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

# 프로젝트 루트 경로 추가  
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Float utilities
from frontend.web.utils.float import float_init

# 새로운 컴포넌트들
from frontend.web.components.chat_messages import ChatMessagesComponent
from frontend.web.components.terminal_ui import TerminalUIComponent
from frontend.web.components.sidebar import SidebarComponent
from frontend.web.components.theme_ui import ThemeUIComponent

# 리팩토링된 비즈니스 로직
from frontend.web.core.app_state import get_app_state_manager
from frontend.web.core.executor_manager import get_executor_manager
from frontend.web.core.workflow_handler import get_workflow_handler
from frontend.web.core.terminal_processor import get_terminal_processor

# 검증 로직
from frontend.web.utils.validation import check_model_required
from frontend.web.utils.constants import ICON, ICON_TEXT, COMPANY_LINK

# 재현 관리
from frontend.web.core.chat_replay import ReplayManager

from src.utils.llm.config_manager import get_current_llm

# 전역 매니저들 초기화
app_state = get_app_state_manager()
executor_manager = get_executor_manager()  
workflow_handler = get_workflow_handler()
terminal_processor = get_terminal_processor()

# UI 컴포넌트들 초기화
theme_ui = ThemeUIComponent()
chat_messages = ChatMessagesComponent()
terminal_ui = TerminalUIComponent()
sidebar = SidebarComponent()


def main():
    """메인 채팅 페이지"""
    
    # 앱 상태 초기화 먼저 수행 (전체 관리자 초기화 포함)
    try:
        app_state._initialize_session_state()
        app_state._initialize_user_session()
        app_state._initialize_logging()
    except Exception as e:
        st.error(f"앱 상태 초기화 오류: {str(e)}")
        return

    if "cancel_workflow" not in st.session_state:
        st.session_state.cancel_workflow = False
    if "pending_new_chat" not in st.session_state:
        st.session_state.pending_new_chat = False

    if st.session_state.get("pending_new_chat", False) and not st.session_state.get("workflow_running", False):
        st.session_state.pending_new_chat = False
        st.session_state.cancel_workflow = False
        _finalize_new_chat()
    
    # 모델 필수 체크
    if not check_model_required():
        _show_model_required_message()
        return
    
    # 테마 및 Float 초기화
    current_theme = "dark" if st.session_state.get('dark_mode', True) else "light"
    theme_ui.apply_theme_css(current_theme)
    theme_ui.render_corner_logo()
    float_init()
    terminal_ui.apply_terminal_css()

    # 로고 직접 사용 (래퍼 함수 제거)
    # st.logo(ICON_TEXT, icon_image=ICON, size="large", link=COMPANY_LINK)
    
    # 제목 직접 사용 (show_page_header 래퍼 제거)
    st.title(":red[Decepticon]")
    
    # 사이드바 설정
    _setup_sidebar()

    if st.button("Run Reconnaissance", use_container_width=False):
        _run_recon_nmap()

    _render_recon_report_section()
    
    # 재현 모드 처리
    replay_manager = ReplayManager()
    if replay_manager.is_replay_mode():
        _handle_replay_mode(replay_manager)
        return
    
    # 메인 인터페이스
    _display_main_interface()


def _run_recon_nmap():
    api_base = os.getenv("EXEC_API_BASE_URL", "http://127.0.0.1:8000")
    url = f"{api_base.rstrip('/')}/execute/recon"

    terminal_ui.add_command("nmap -sV --version-light -Pn --open -T4 victim")

    try:
        with st.spinner("Running nmap in Kali container..."):
            resp = requests.post(url, timeout=330)
        if resp.status_code != 200:
            terminal_ui.add_output(resp.text)
            st.error(f"Recon API error ({resp.status_code})")
            return

        payload = resp.json()
        output = payload.get("output") or ""
        terminal_ui.add_output(output)

        st.session_state["recon_output"] = output
        st.session_state["recon_report"] = _generate_recon_report(output)

    except Exception as e:
        terminal_ui.add_output(str(e))
        st.error(f"Failed to call recon API: {e}")


def _generate_recon_report(raw_output: str) -> str:
    llm = get_current_llm()
    if llm is None:
        return "LLM is not available. Please select a model and ensure API keys are configured."

    prompt = (
        "You are a security analyst. Analyze the following raw Nmap output and produce a Reconnaissance Report with:\n"
        "1) Open ports list\n"
        "2) Services and versions\n"
        "3) High-level risk assessment\n"
        "4) Reconnaissance summary\n"
        "5) Recommendation for next phase (Initial Access - simulated)\n\n"
        "RAW OUTPUT:\n" + raw_output
    )

    try:
        resp = llm.invoke(prompt)
        return getattr(resp, "content", str(resp))
    except Exception as e:
        return (
            "AI analysis is temporarily unavailable.\n\n"
            f"Error: {e}\n\n"
            "You can still use the REAL terminal output above for screenshots. "
            "Retry after fixing model connectivity."
        )


def _render_recon_report_section():
    report = st.session_state.get("recon_report")
    raw_output = st.session_state.get("recon_output")

    if not raw_output:
        return

    st.markdown("## AI Reconnaissance Report")
    if report:
        st.markdown(report)
    else:
        st.info("Recon output captured. Generating report...")

    if st.button("Proceed to Initial Access (Simulated)", use_container_width=False):
        st.session_state["auto_user_input"] = (
            "Proceed to Initial Access (Simulated). Use the recon results below to plan the next steps.\n\n"
            + (report or raw_output)
        )
        st.rerun()


def _show_model_required_message():
    """모델 필요 메시지 표시"""
    st.warning("⚠️ Please select a model first")
    if st.button("Go to Model Selection", type="primary"):
        st.switch_page("streamlit_app.py")


def _setup_sidebar():
    """사이드바 설정 - 새로운 컴포넌트 사용"""
    # 콜백 함수들 정의
    callbacks = {
        "on_change_model": lambda: st.switch_page("streamlit_app.py"),
        "on_chat_history": lambda: st.switch_page("pages/02_Chat_History.py"),
        "on_new_chat": _create_new_chat,
        "on_debug_mode_change": app_state.set_debug_mode
    }
    
    # 현재 데이터 가져오기 (예외 처리 포함)
    try:
        current_model = st.session_state.get('current_model')
        active_agent = st.session_state.get('active_agent')
        completed_agents = st.session_state.get('completed_agents', [])
        session_stats = app_state.get_session_stats()
        debug_info = app_state.get_debug_info()
    except Exception as e:
        st.error(f"사이드바 데이터 로드 오류: {str(e)}")
        # 기본값으로 폴백
        current_model = None
        active_agent = None
        completed_agents = []
        session_stats = {"messages_count": 0, "events_count": 0, "steps_count": 0, "elapsed_time": 0, "active_agent": None, "completed_agents_count": 0}
        debug_info = {"user_id": "Error", "thread_id": "Error", "executor_ready": False, "workflow_running": False}
    
    # 사이드바 렌더링
    sidebar.render_complete_sidebar(
        model_info=current_model,
        active_agent=active_agent,
        completed_agents=completed_agents,
        session_stats=session_stats,
        debug_info=debug_info,
        callbacks=callbacks
    )


def _display_main_interface():
    """메인 인터페이스 - 전체 화면 Chat + Floating Terminal"""
    
    # 터미널 상태 초기화
    if "terminal_visible" not in st.session_state:
        st.session_state.terminal_visible = True
    
    terminal_processor.initialize_terminal_state()
    
    # 전체 화면 Chat UI
    chat_height = app_state.get_env_config().get("chat_height", 700)
    chat_container = st.container(height=chat_height, border=False)
    
    with chat_container:
        messages_area = st.container()
        if not st.session_state.get('workflow_running', False):
            structured_messages = st.session_state.get('structured_messages', [])
            chat_messages.display_messages(structured_messages, messages_area)
    
    # Floating 터미널 토글 버튼 - 워크플로우와 독립적으로 처리
    _handle_terminal_toggle()
    
    # Floating 터미널 표시
    _render_floating_terminal()
    
    # 사용자 입력 처리
    _handle_user_input(messages_area)


def _handle_terminal_toggle():
    """터미널 토글 버튼 처리 - 워크플로우와 독립적"""
    toggle_clicked = terminal_ui.create_floating_toggle_button(st.session_state.terminal_visible)
    
    if toggle_clicked:
        # 터미널 상태 토글
        st.session_state.terminal_visible = not st.session_state.terminal_visible
        
        # 토글 시에만 즉시 리랜더링 (워크플로우 실행 중에도 작동)
        st.rerun()


def _render_floating_terminal():
    """플로팅 터미널 렌더링 - 상태에 따라 조건부 표시"""
    if st.session_state.terminal_visible:
        terminal_history = terminal_processor.get_terminal_history()
        terminal_ui.create_floating_terminal(terminal_history)


def _handle_user_input(messages_area):
    """사용자 입력 처리 - 새로운 워크플로우 핸들러 사용"""
    
    auto_user_input = st.session_state.pop("auto_user_input", None)
    user_input = auto_user_input or st.chat_input("Type your red team request here...")
    
    if user_input and not st.session_state.get('workflow_running', False):
        
        async def execute_workflow():
            # 사용자 입력 검증
            validation_result = workflow_handler.validate_execution_state()
            if not validation_result["can_execute"]:
                st.error(validation_result.get("error_message") or "Cannot execute workflow")
                return
            
            # 사용자 메시지 준비
            user_message = workflow_handler.prepare_user_input(user_input)
            
            # 사용자 메시지 표시
            with messages_area:
                chat_messages.display_user_message(user_message)
            
            # UI 콜백 함수들 정의
            ui_callbacks = {
                "on_message_ready": lambda msg: _display_message_callback(msg, messages_area),
                "on_terminal_message": _terminal_message_callback,
                "on_workflow_complete": lambda: None,
                "on_error": lambda error: st.error(f"Workflow error: {error}")
            }
            
            # 워크플로우 실행 - 터미널 UI 직접 전달
            result = await workflow_handler.execute_workflow_logic(
                user_input, ui_callbacks, terminal_ui
            )
            
            # 결과 처리
            if result["success"]:
                # 에이전트 상태 업데이트를 위해 사이드바 새로고침
                # rerun 제거하여 문제 방지
                # st.rerun()
                pass
            else:
                if result["error_message"]:
                    st.error(result["error_message"])

        def _run_async_safely(coro):
            try:
                return asyncio.run(coro)
            except BaseException as e:
                if StopException is not None and isinstance(e, StopException):
                    return None
                raise

        _run_async_safely(execute_workflow())

        if st.session_state.get("pending_new_chat", False) and not st.session_state.get(
            "workflow_running", False
        ):
            st.session_state.pending_new_chat = False
            st.session_state.cancel_workflow = False
            _finalize_new_chat()


def _display_message_callback(message, messages_area):
    """메시지 표시 콜백"""
    with messages_area:
        message_type = message.get("type", "")
        if message_type == "ai":
            chat_messages.display_agent_message(message, streaming=False)
        elif message_type == "tool":
            chat_messages.display_tool_message(message)


def _terminal_message_callback(tool_name, content):
    """터미널 메시지 콜백 (단순화된 버전)"""
    # 더 이상 사용되지 않음 - 직접 호출 방식으로 대체
    pass


def _create_new_chat():
    """새 채팅 생성 - 래퍼 함수에서 직접 구현으로 변경"""
    try:
        if st.session_state.get("workflow_running", False):
            st.session_state.cancel_workflow = True
            st.session_state.pending_new_chat = True
            st.warning("Cancelling current workflow… starting new chat shortly.")
            return

        _finalize_new_chat()

    except Exception as e:
        st.error(f"Failed to create new chat: {str(e)}")


def _finalize_new_chat():
    conversation_id = app_state.create_new_conversation()
    executor_manager.reset()
    
    # 현재 모델로 재초기화
    current_model = st.session_state.get('current_model')
    if current_model:
        async def reinitialize():
            await executor_manager.initialize_with_model(current_model)
        asyncio.run(reinitialize())
    
    # 터미널 상태도 초기화
    terminal_processor.clear_terminal_state()
    
    st.success("✨ New chat session started!")
    # rerun 제거하여 문제 방지
    # st.rerun()


def _handle_replay_mode(replay_manager):
    """재현 모드 처리 - ReplayManager 사용"""
    # 메시지 제거 - 바로 이전 대화 내역 재현
    
    # Float 초기화
    float_init()
    terminal_ui.apply_terminal_css()
    
    # 터미널 상태 초기화
    if "terminal_visible" not in st.session_state:
        st.session_state.terminal_visible = True
    
    terminal_processor.initialize_terminal_state()
    
    # 전체 화면 Chat UI
    chat_height = app_state.get_env_config().get("chat_height", 700)
    chat_container = st.container(height=chat_height, border=False)
    
    with chat_container:
        messages_area = st.container()
        
        # ReplayManager를 사용하여 재현 처리
        replay_handled = replay_manager.handle_replay_in_main_app(
            messages_area, st.sidebar.container(), chat_messages, terminal_ui
        )
        
        if not replay_handled:
            # 재현 실패 시 기본 메시지 표시
            st.error("재현에 실패했습니다. 세션 데이터를 찾을 수 없습니다.")
    
    # Floating 터미널 토글 버튼 - 워크플로우와 독립적으로 처리
    _handle_terminal_toggle()
    
    # Floating 터미널 표시
    _render_floating_terminal()
    
    # 재현 완료 후 버튼
    if st.session_state.get("replay_completed", False):
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✨ Start New Chat", use_container_width=True, type="primary"):
                # 재현 모드 종료
                for key in ["replay_mode", "replay_session_id", "replay_completed"]:
                    st.session_state.pop(key, None)
                # 새 채팅 생성 시 rerun 문제 방지
                _create_new_chat()
                # st.rerun() 제거


if __name__ == "__main__":
    main()
