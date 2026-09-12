import os
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_app_timezone, get_now
from app.services.agent_service import AgentService
from app.services.briefing_service import BriefingService
from app.services.git_service import GitService
from app.services.llm_provider import LLMProvider
from app.services.session_service import SessionService
from app.services.settings_service import SettingsService


class SupervisorService:
    def __init__(self, db: Session, base_dir: str | None = None):
        self.session_service = SessionService(db)
        self.settings_service = SettingsService()
        self.base_dir = base_dir or self.settings_service.get_gtd_path()
        self.agent_service = AgentService(base_dir=self.base_dir)
        self.git_service = GitService(repo_path=self.base_dir)
        self.llm_provider = LLMProvider()
        self.briefing_service = BriefingService(
            base_dir=self.base_dir,
            llm_provider=self.llm_provider,
            git_service=self.git_service,
        )

    def process_user_request(
        self,
        session_id: str,
        user_message: str,
        category: str = "Daily Notes & Diary",
        channel: str = "web",
        auto_push: bool = True,
    ) -> dict[str, Any]:
        # 1. DB 세션 생성 및 보류 기록/히스토리 조회
        self.session_service.get_or_create_session(session_id=session_id, channel=channel)
        self.session_service.auto_update_session_title(session_id=session_id, user_message=user_message)
        pending_log = self.session_service.get_pending_log(session_id=session_id)
        history = self.session_service.get_session_history(session_id=session_id)

        # 2. 사용자 메시지 DB 저장
        self.session_service.add_message(session_id=session_id, role="user", content=user_message)

        # 3. 비서 의도 분석 및 답변 생성 (ADR-004)
        intent_res = self.llm_provider.analyze_and_respond(
            prompt=user_message,
            history=history,
            pending_log=pending_log,
        )

        filepath = None
        push_success = False

        # 4. 의도별 분기 처리
        if intent_res.intent == "log_dual" or intent_res.is_dual_log:
            # (A-1) 복합 기록 (데일리 로그 + GTD 인박스 동시 반영 - ADR-014)
            content_to_log = intent_res.log_content or user_message
            target_cat = "Daily Notes & Diary"
            daily_filepath = self.agent_service.append_or_update_lifelog(
                content=content_to_log,
                category=target_cat,
                date_obj=get_now(),
            )
            gtd_task = intent_res.gtd_task_content or f"- [ ] {content_to_log[:30]}"
            self.agent_service.append_to_gtd_inbox(content=gtd_task)
            filepath = daily_filepath

            if auto_push:
                date_str = get_now().strftime("%Y-%m-%d")
                clean_summary = " ".join(line.strip() for line in content_to_log.splitlines() if line.strip())
                commit_msg = f"docs(lifelog & gtd): [{target_cat}] {clean_summary[:25]} ({date_str}) [{session_id}]"
                push_success = self.git_service.sync_and_commit_push(commit_message=commit_msg, file_path=None)

            self.session_service.clear_pending_log(session_id=session_id)

        elif intent_res.intent in ["log_confirm", "log_explicit"]:
            # (A-2) 승인되었거나 직접 요청된 유의미한 라이프로그 -> 마크다운 기록 & Git 커밋 (옵션 A)
            content_to_log = intent_res.log_content or user_message
            target_cat = category if category != "Daily Notes & Diary" else (intent_res.category or category)

            filepath = self.agent_service.append_or_update_lifelog(
                content=content_to_log,
                category=target_cat,
                date_obj=get_now(),
            )

            if auto_push:
                date_str = get_now().strftime("%Y-%m-%d")
                clean_summary = " ".join(line.strip() for line in content_to_log.splitlines() if line.strip())
                commit_msg = f"docs(lifelog): [{target_cat}] {clean_summary[:30]} ({date_str}) [{session_id}]"
                push_success = self.git_service.sync_and_commit_push(commit_message=commit_msg, file_path=filepath)

            self.session_service.clear_pending_log(session_id=session_id)


        elif intent_res.intent == "log_suggest":
            # (B) 비서가 라이프로그 기록을 제안 -> 세션에 보류 보관 (Git 커밋 X, 마크다운 수정 X)
            suggested_content = intent_res.log_content or user_message
            suggested_cat = intent_res.category or category
            self.session_service.set_pending_log(
                session_id=session_id,
                content=suggested_content,
                category=suggested_cat,
                gtd_task=intent_res.gtd_task_content,
                is_dual=intent_res.is_dual_log,
            )

        elif intent_res.intent == "log_reject":
            # (C) 사용자가 제안 거절 -> 보류 기록 초기화 (Git 커밋 X, 마크다운 수정 X)
            self.session_service.clear_pending_log(session_id=session_id)

        final_response = intent_res.ai_response

        if intent_res.intent == "gtd_remove":
            # (A-3) GTD 태스크 삭제/제거 (ADR-020)
            removed = self.agent_service.find_and_remove_matching_tasks(user_message)
            if removed:
                bullets = "\n".join(f"• {t}" for t in removed)
                date_str = get_now().strftime("%Y-%m-%d")
                commit_msg = f"fix(gtd): remove {len(removed)} completed tasks ({date_str}) [{session_id}]"
                push_res = ""
                if auto_push:
                    p_success, p_msg = self.git_service.commit(commit_msg)
                    if p_success:
                        p_ok, p_out = self.git_service.push()
                        push_res = f"\n\n🚀 **원격 저장소 반영**: {p_out}"
                        push_success = p_ok
                    else:
                        push_res = f"\n\nℹ️ {p_msg}"
                else:
                    self.git_service.commit(commit_msg)

                final_response = (
                    f"🗑️ **GTD 항목 제거 및 동기화 완료**\n\n"
                    f"요청하신 {len(removed)}개 항목을 GTD 목록(`inbox.md`, `next_actions.md`)에서 안전하게 제거했습니다:\n"
                    f"{bullets}{push_res}"
                )
            else:
                final_response = "제거할 일치하는 GTD 항목을 찾지 못했습니다. 현재 등록된 할 일 명칭을 다시 확인해 주세요. 📋"

        elif intent_res.intent == "task_complete":
            # (A-4) GTD 태스크 완료 처리 (ADR-027)
            query = intent_res.log_content or ""
            date_str = get_now().strftime("%Y-%m-%d")
            push_res = ""

            if query:
                completed = self.agent_service.complete_matching_tasks([query])
                if completed:
                    bullets = "\n".join(f"• - [x] {t}" for t in completed)
                    commit_msg = f"feat(gtd): complete {len(completed)} tasks ({date_str}) [{session_id}]"
                    if auto_push:
                        p_success, p_msg = self.git_service.commit(commit_msg)
                        if p_success:
                            p_ok, p_out = self.git_service.push()
                            push_res = f"\n\n🚀 **원격 저장소 반영**: {p_out}"
                            push_success = p_ok
                    else:
                        self.git_service.commit(commit_msg)
                    final_response = (
                        f"🎉 **GTD 태스크 완료 처리**\n\n"
                        f"{bullets}{push_res}"
                    )
                else:
                    final_response = f"'{query}'와 일치하는 미완료 GTD 태스크를 찾지 못했습니다. 📋"
            else:
                res = self.agent_service.complete_top_task()
                if res.get("success"):
                    task_name = res["task"]
                    file_name = res["file_name"]
                    commit_msg = f"feat(gtd): complete top task - {task_name} ({date_str}) [{session_id}]"
                    if auto_push:
                        p_success, p_msg = self.git_service.commit(commit_msg)
                        if p_success:
                            p_ok, p_out = self.git_service.push()
                            push_res = f"\n\n🚀 **원격 저장소 반영**: {p_out}"
                            push_success = p_ok
                    else:
                        self.git_service.commit(commit_msg)
                    final_response = (
                        f"🎉 **1순위 태스크 완료!**\n\n"
                        f"- [x] {task_name}\n"
                        f"📁 대상 파일: `{file_name}`\n"
                        f"GitHub에 안전하게 커밋 및 푸시되었습니다. 수고하셨습니다! ✨{push_res}"
                    )
                else:
                    final_response = "👏 축하합니다! 현재 등록된 미완료 1순위 태스크가 없습니다. 오늘 할 일을 모두 마치셨거나 수집함이 비어있습니다. 📋"

        elif intent_res.intent == "repo_commit":
            # (D-5) 명시적 로컬 Git 커밋 명령 (ADR-020)
            date_str = get_now().strftime("%Y-%m-%d")
            commit_msg = f"docs(gtd): manual commit via watson ({date_str}) [{session_id}]"
            success, msg = self.git_service.commit(commit_msg)
            if success:
                push_res = ""
                if auto_push:
                    p_ok, p_out = self.git_service.push()
                    push_res = f"\n🚀 **원격 저장소 동기화**: {p_out}"
                    push_success = p_ok
                final_response = f"✍️ **Git 커밋 완료**\n{msg}{push_res}"
            else:
                final_response = f"ℹ️ **Git 커밋 상태**\n{msg}"

        elif intent_res.intent == "repo_sync":
            # (D-1) GTD 레포 원격 동기화 (ADR-009)
            success, sync_msg = self.git_service.pull()
            icon = "✅" if success else "⚠️"
            final_response = f"{icon} **GTD 저장소 동기화 결과**\n{sync_msg}"

        elif intent_res.intent == "repo_sync_and_briefing":
            # (D-2) GTD 레포 동기화 후 즉시 브리핑 (ADR-009, ADR-024)
            success, sync_msg = self.git_service.pull()
            briefing_res = self.briefing_service.generate_briefing(mode=None)
            briefing = briefing_res["markdown"]
            if success:
                final_response = f"🔄 **최신 GTD 저장소 동기화 완료** (`git pull`)\n\n{briefing}"
            else:
                final_response = f"⚠️ **동기화 주의**: {sync_msg}\n\n{briefing}"

        elif intent_res.intent == "repo_push":
            # (D-4) GTD 레포 원격 푸시 및 상태/원격지 확인 (ADR-011, ADR-020)
            is_query = (intent_res.log_content == "query")
            remote_info = self.git_service.get_remote_info()

            if is_query or any(q in user_message for q in ["어디다", "어디로", "어디 푸시", "어디에"]):
                url = remote_info.get("url", "GitHub Remote")
                branch = remote_info.get("branch", "main")
                c_hash = remote_info.get("latest_hash", "")
                c_msg = remote_info.get("latest_commit", "")
                ahead = remote_info.get("ahead_count", 0)
                sync_state = "모든 로컬 커밋이 원격 저장소에 완벽히 동기화되어 있습니다. ✅" if ahead == 0 else f"{ahead}개의 로컬 커밋이 푸시 대기 중입니다."

                final_response = (
                    f"📍 **현재 연결된 원격 GitHub 저장소 정보**\n\n"
                    f"* **원격 저장소 URL**: `{url}`\n"
                    f"* **브랜치**: `{branch}`\n"
                    f"* **최근 커밋**: `{c_hash}` ({c_msg})\n"
                    f"* **동기화 상태**: {sync_state}\n\n"
                    f"모든 GTD 및 라이프로그 데이터는 지정하신 위 GitHub 공식 저장소로만 안전하게 푸시 및 백업됩니다. 🔐📦"
                )
            else:
                success, push_msg = self.git_service.push()
                icon = "🚀" if success else "⚠️"
                url = remote_info.get("url", "")
                url_mention = f"\n(원격 저장소: `{url}`)" if url else ""
                final_response = f"{icon} **GitHub 푸시 결과**\n{push_msg}{url_mention}"
                push_success = success

        elif intent_res.intent == "task_briefing_morning":
            # (D-3a) 아침 맞춤형 GTD 브리핑 (ADR-024)
            self.git_service.pull()
            briefing_res = self.briefing_service.generate_briefing(mode="morning")
            final_response = briefing_res["markdown"]

        elif intent_res.intent == "task_briefing_evening":
            # (D-3b) 저녁 일과 회고 및 GTD 브리핑 (ADR-024)
            self.git_service.pull()
            briefing_res = self.briefing_service.generate_briefing(mode="evening")
            final_response = briefing_res["markdown"]

        elif intent_res.intent == "task_briefing":
            # (D-3c) 시간대 자동 감지 GTD 종합 브리핑 (ADR-008, ADR-024)
            self.git_service.pull()
            briefing_res = self.briefing_service.generate_briefing(mode=None)
            final_response = briefing_res["markdown"]

        elif intent_res.intent == "briefing_schedule_inspect":
            # (D-3d) 브리핑 스케줄 및 오늘 주요 일정 시간표 확인 (ADR-025)
            final_response = self.briefing_service.format_schedule_briefing(date_obj=get_now())

        elif intent_res.intent == "log_status_inspect":
            # (D-6a) 당일 라이프로그 물리적 기록 여부 정밀 점검 및 보고 (ADR-028)
            now = get_now()
            date_str = now.strftime("%Y-%m-%d")
            filepath = self.agent_service.get_lifelog_filepath(now)
            has_file = os.path.exists(filepath)

            has_journal_entry = False
            file_content = ""
            if has_file:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_content = f.read().strip()
                    has_journal_entry = bool(re.search(r"-\s*\[\d{2}:\d{2}\]", file_content))
                except OSError:
                    pass

            if has_file and has_journal_entry:
                rel_path = os.path.relpath(filepath, self.agent_service.base_dir)
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath), tz=get_app_timezone()).strftime("%H:%M:%S")
                final_response = (
                    f"✅ **네, 오늘({date_str}) 일일 로그 파일에 정상 기록되어 있습니다.**\n\n"
                    f"* **파일 경로**: `{rel_path}` (최종 수정: `{mtime}`)\n\n"
                    f"---\n\n"
                    f"{file_content}"
                )
            else:
                rel_path = os.path.relpath(filepath, self.agent_service.base_dir) if has_file else f"logs/daily/{date_str}.md"
                recent_user_msg = None
                if history:
                    for h in reversed(history):
                        if h.get("role") == "user" and len(h.get("content", "").strip()) > 5:
                            c = h.get("content", "").strip()
                            if not any(c.startswith(cmd) for cmd in ["/", "기록", "확인", "푸시", "동기화", "오늘 로그", "오늘 일기"]):
                                recent_user_msg = c
                                break

                if recent_user_msg:
                    snippet = recent_user_msg[:35] + "..." if len(recent_user_msg) > 35 else recent_user_msg
                    cat = self.llm_provider._detect_category(recent_user_msg)
                    self.session_service.set_pending_log(session_id=session_id, content=recent_user_msg, category=cat)
                    final_response = (
                        f"ℹ️ **아직 오늘({date_str}) 일일 로그 파일에 기록되지 않았습니다.**\n\n"
                        f"* **대상 파일**: `{rel_path}`\n\n"
                        f"직전에 말씀해주신 이야기('{snippet}')를 오늘 라이프로그에 기록해 드릴까요?\n"
                        f"👉 **'응'** 또는 **'기록해줘'**라고 말씀하시면 즉시 파일에 작성하고 커밋합니다! ✍️"
                    )
                else:
                    final_response = (
                        f"ℹ️ **아직 오늘({date_str}) 일일 로그 파일에 작성된 기록이 없습니다.**\n\n"
                        f"* **대상 파일**: `{rel_path}`\n\n"
                        f"오늘 있었던 일과나 마음, 메모를 남겨주시면 즉시 마크다운 파일에 기록하고 GitHub에 커밋해 드립니다! ✍️"
                    )

        elif intent_res.intent == "daily_log_inspect":
            # (D-6b) 오늘 일일 로그 파일 즉시 조회 (ADR-022)
            final_response = self.agent_service.read_daily_log(date_obj=get_now())

        elif intent_res.intent == "gtd_inspect":
            # (D-7) GTD inbox/next_actions 파일 직접 조회 (ADR-022)
            final_response = self.agent_service.read_gtd_files()

        elif intent_res.intent == "gtd_and_log_inspect":
            # (D-8) GTD 파일 및 오늘 일일 로그 종합 직접 조회 (ADR-022)
            final_response = self.agent_service.read_gtd_and_daily_log(date_obj=get_now())

        # 5. AI 응답 DB 저장
        self.session_service.add_message(session_id=session_id, role="assistant", content=final_response)

        return {
            "session_id": session_id,
            "intent": intent_res.intent,
            "filepath": filepath,
            "ai_response": final_response,
            "git_pushed": push_success,
            "history": self.session_service.get_session_history(session_id=session_id),
            "pending_log": self.session_service.get_pending_log(session_id=session_id),
        }

    def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        return self.session_service.get_session_history(session_id=session_id)

    def list_sessions(self, agent_type: str | None = None) -> list[dict[str, Any]]:
        return self.session_service.list_sessions(agent_type=agent_type)

    def update_session_title(self, session_id: str, title: str) -> Any:
        return self.session_service.update_session_title(session_id=session_id, title=title)

    def delete_session(self, session_id: str) -> bool:
        return self.session_service.delete_session(session_id=session_id)

    def clear_session_messages(self, session_id: str) -> bool:
        return self.session_service.clear_session_messages(session_id=session_id)

    def get_briefing(self, mode: str | None = None) -> dict[str, Any]:
        """외부 REST API 및 스케줄러를 위한 아침/저녁 GTD 브리핑 조회 메서드 (ADR-024)."""
        return self.briefing_service.generate_briefing(mode=mode)

    def get_briefing_schedule(self) -> dict[str, Any]:
        """브리핑 스케줄 및 오늘 주요 일정 시간표 정보 조회 메서드 (ADR-025)."""
        return self.briefing_service.get_schedule_info()
