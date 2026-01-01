"""
메시지 처리 로직 (리팩토링됨 - 순수 비즈니스 로직)
CLI 메시지를 프론트엔드 메시지로 변환하는 핵심 로직
"""

from datetime import datetime
from typing import Dict, Any, List
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# CLI 메시지 유틸리티 직접 import
from src.utils.message import parse_tool_name, extract_tool_calls
# 리팩토링된 에이전트 관리자
from src.utils.agents import AgentManager


class MessageProcessor:
    """메시지 처리 핵심 로직 클래스"""
    
    def __init__(self):
        """메시지 프로세서 초기화"""
        self.default_avatar = "🤖"
    
    def process_cli_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """CLI 이벤트를 프론트엔드 메시지로 변환
        
        Args:
            event_data: CLI에서 온 이벤트 데이터
            
        Returns:
            Dict: 변환된 프론트엔드 메시지
        """
        message_type = event_data.get("message_type", "")
        agent_name = event_data.get("agent_name", "Unknown")
        content = event_data.get("content", "")
        raw_message = event_data.get("raw_message")
        
        # 에이전트 표시 정보 생성
        display_name = AgentManager.get_display_name(agent_name)
        avatar = AgentManager.get_avatar(agent_name)
        
        if message_type == "ai":
            return self._create_ai_message(
                agent_name, display_name, avatar, content, raw_message, event_data
            )
        elif message_type == "tool":
            return self._create_tool_message(event_data, content)
        elif message_type == "user":
            return self._create_user_message(content)
        
        # 기본 메시지 - AI로 처리
        return self._create_ai_message(
            agent_name, display_name, avatar, content, raw_message, event_data
        )
    
    def _create_ai_message(
        self, 
        agent_name: str, 
        display_name: str, 
        avatar: str, 
        content: str, 
        raw_message: Any,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI 메시지 생성"""
        if self._is_initial_access_agent(agent_name):
            content = self._sanitize_initial_access_output(content)
        elif self._is_summary_agent(agent_name):
            content = self._sanitize_summary_output(content)

        message = {
            "type": "ai",
            "agent_id": agent_name.lower(),
            "display_name": display_name,
            "avatar": avatar,
            "content": content,
            "id": f"ai_{agent_name.lower()}_{hash(content[:100])}_{datetime.now().timestamp()}"
        }
        
        # Tool calls 정보 추출
        tool_calls = extract_tool_calls(raw_message, event_data)
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        return message

    def _is_initial_access_agent(self, agent_name: str) -> bool:
        val = (agent_name or "").strip().lower()
        return val in {"initial_access", "initial_access_agent", "initial_access\n"} or "initial_access" in val or "initial_access" in val.replace(" ", "_") or "initial_access" in val.replace("-", "_") or "initial_access" in val.replace(".", "_") or "initial_access" in val.replace("/", "_") or "initial_access" in val

    def _is_summary_agent(self, agent_name: str) -> bool:
        val = (agent_name or "").strip().lower()
        return val == "summary" or "summary" in val

    def _sanitize_initial_access_output(self, content: str) -> str:
        text = content or ""
        lowered = text.lower()

        required_heading = "initial access assessment (simulated)"
        banned_terms = [
            "cve",
            "exploit",
            "backdoor",
            "rce",
            "shell",
            "root",
            "metasploit",
            "eternalblue",
            "brute-force",
            "bruteforce",
            "command",
            "payload",
            "port-by-port",
        ]

        if required_heading not in lowered:
            return self._initial_access_safe_template()

        for term in banned_terms:
            if term in lowered:
                return self._initial_access_safe_template()

        return text

    def _initial_access_safe_template(self) -> str:
        return (
            "Initial Access Assessment (Simulated)\n\n"
            "Selected Entry Vector:\n"
            "Legacy file transfer service exposed to the network\n\n"
            "Reason for Selection:\n"
            "The reconnaissance phase identified an outdated externally accessible service. "
            "From a risk perspective, legacy services often present higher exposure due to age, reduced maintenance, "
            "and historically weaker security controls, making them a common initial access candidate in controlled environments.\n\n"
            "Required Preconditions:\n"
            "- Network connectivity to the target system\n"
            "- Service accessible without restrictive access controls\n\n"
            "Expected Outcome (Simulated):\n"
            "Potential initial foothold with limited privileges, enabling further impact assessment.\n\n"
            "Risk Level:\n"
            "Critical\n\n"
            "Confidence Level:\n"
            "High\n\n"
            "Potential Next Steps (Theoretical):\n"
            "- Privilege escalation risk evaluation\n"
            "- Lateral movement exposure assessment\n"
            "- Persistence and detection impact review"
        )

    def _sanitize_summary_output(self, content: str) -> str:
        text = content or ""
        lowered = text.lower()

        required_heading = "engagement summary (public demo safe)"
        banned_terms = [
            "cve",
            "exploit",
            "backdoor",
            "metasploit",
            "msfconsole",
            "payload",
            "reverse shell",
            "netcat",
            "hydra",
            "sqlmap",
            "command",
            "rce",
            "remote command execution",
            "shell",
            "```",
        ]

        if required_heading not in lowered:
            return self._summary_safe_template()

        for term in banned_terms:
            if term in lowered:
                return self._summary_safe_template()

        return text

    def _summary_safe_template(self) -> str:
        return (
            "Engagement Summary (Public Demo Safe)\n\n"
            "Executive Overview:\n"
            "The assessment identified externally exposed services with indicators of outdated configurations and insufficient access controls. "
            "These conditions increase the likelihood of unauthorized access attempts and elevate overall risk.\n\n"
            "Key Observations:\n"
            "- Multiple network-exposed services were identified that warrant hardening and access review\n"
            "- Service configuration and version hygiene appear inconsistent\n"
            "- Preventive controls (segmentation, allowlisting, and monitoring) should be strengthened\n\n"
            "Primary Risks:\n"
            "- Unauthorized access via exposed services (Impact: High, Likelihood: Medium)\n"
            "- Credential exposure or weak authentication controls (Impact: High, Likelihood: Medium)\n\n"
            "Recommended Mitigations (Non-Operational):\n"
            "- Reduce external exposure to only required services and enforce strict access policies\n"
            "- Standardize patching/version management and configuration baselines\n"
            "- Strengthen authentication, logging, and monitoring for externally reachable systems\n\n"
            "Scope & Limitations:\n"
            "- Findings are based on observed service exposure and provided reconnaissance artifacts\n"
            "- This summary intentionally omits operational detail to remain public-demo safe\n\n"
            "Next Phase Recommendation:\n"
            "Proceed with prioritized remediation validation and security control review to reduce exposure and confirm risk reduction."
        )
    
    def _create_tool_message(self, event_data: Dict[str, Any], content: str) -> Dict[str, Any]:
        """도구 메시지 생성"""
        tool_name = event_data.get("tool_name", "Unknown Tool")
        tool_display_name = event_data.get("tool_display_name", parse_tool_name(tool_name))
        
        return {
            "type": "tool",
            "tool_name": tool_name,
            "tool_display_name": tool_display_name,
            "content": content,
            "id": f"tool_{tool_name}_{hash(content[:100])}_{datetime.now().timestamp()}"
        }
    
    def _create_user_message(self, content: str) -> Dict[str, Any]:
        """사용자 메시지 생성"""
        return {
            "type": "user",
            "content": content,
            "id": f"user_{hash(content)}_{datetime.now().timestamp()}"
        }
    
    def extract_agent_status(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """이벤트들에서 에이전트 상태 정보 추출"""
        status = {
            "active_agent": None,
            "completed_agents": [],
            "current_step": 0
        }
        
        # 최근 이벤트에서 활성 에이전트 찾기
        for event in reversed(events):
            if event.get("type") == "message" and event.get("message_type") == "ai":
                agent_name = event.get("agent_name")
                if agent_name and agent_name != "Unknown":
                    status["active_agent"] = agent_name.lower()
                    break
        
        # 총 스텝 수 계산
        status["current_step"] = len([e for e in events if e.get("type") == "message"])
        
        return status
    
    def is_duplicate_message(
        self, 
        new_message: Dict[str, Any], 
        existing_messages: List[Dict[str, Any]]
    ) -> bool:
        """메시지 중복 검사"""
        new_id = new_message.get("id")
        if not new_id:
            return False
        
        # ID 기반 중복 검사
        for msg in existing_messages:
            if msg.get("id") == new_id:
                return True
        
        # 내용 기반 중복 검사 (같은 에이전트의 같은 내용)
        new_agent = new_message.get("agent_id")
        new_content = new_message.get("content", "")
        
        for msg in existing_messages:
            if (msg.get("agent_id") == new_agent and 
                msg.get("type") == new_message.get("type") and
                msg.get("content") == new_content):
                return True
        
        return False


# 전역 메시지 프로세서 인스턴스
_message_processor = None

def get_message_processor() -> MessageProcessor:
    """메시지 프로세서 싱글톤 인스턴스 반환"""
    global _message_processor
    if _message_processor is None:
        _message_processor = MessageProcessor()
    return _message_processor
