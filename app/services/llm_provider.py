import logging
import os
import random
import re
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger("watson.llm")


@dataclass
class IntentResult:
    """비서 에이전트의 의도 분석 및 응답 결과 데이터클래스."""

    intent: str  # "chat_only", "log_suggest", "log_confirm", "log_reject", "log_explicit", "log_dual", "task_briefing"
    ai_response: str
    log_content: str | None = None
    category: str | None = None
    gtd_task_content: str | None = None  # GTD inbox에 등록할 액션 태스크 (ADR-014)
    is_dual_log: bool = False  # 데일리 로그 + GTD 인박스 동시 기록 여부


class LLMProvider:
    """
    왓슨 지능형 비서(Watson Butler) 엔진 (ADR-003, ADR-004, ADR-008 준수).
    AGY 엔진 및 대화 컨텍스트(History)를 기반으로 살아있는 지능형 대화를 나누며,
    GTD 브리핑 및 라이프로그 항목을 능동 제안 및 승인 시 커밋한다.
    """

    def __init__(self):
        self.agy_path = self._find_agy_path()

    def _find_agy_path(self) -> str | None:
        """멀티 플랫폼(Linux/Mac/Docker) agy CLI 바이너리 경로를 동적으로 탐색합니다."""
        found = shutil.which("agy")
        if found and os.path.exists(found):
            return found
        candidates = [
            os.path.expanduser("~/.local/bin/agy"),
            "/home/ubuntu/.local/bin/agy",
            "/usr/local/bin/agy",
            "/usr/bin/agy",
            "/Users/glshlee/.local/bin/agy",
        ]
        for c in candidates:
            if os.path.exists(c) and os.access(c, os.X_OK):
                return c
        return None

    def analyze_and_respond(
        self,
        prompt: str,
        history: list[dict[str, str]] | None = None,
        pending_log: dict[str, str] | None = None,
    ) -> IntentResult:
        prompt_clean = prompt.strip()

        # -------------------------------------------------------------
        # 1. 이전 비서 제안에 대한 승인/거절 (log_confirm / log_reject) 판별
        # -------------------------------------------------------------
        if pending_log:
            # (1-1) 거절 패턴 우선 검사
            reject_patterns = [
                r"(아니|아니야|아냐|됐어|필요\s*없|기록\s*하지\s*마|하지\s*마|취소|괜찮아|ㄴㄴ|no\b|cancel)",
                r"기록\s*(안\s*할래|안해)",
            ]
            for pattern in reject_patterns:
                if re.search(pattern, prompt_clean, re.IGNORECASE):
                    return IntentResult(
                        intent="log_reject",
                        ai_response="네, 기록하지 않고 편안한 대화로만 기억해 둘게요! 😊 또 말씀해 주세요.",
                        log_content=None,
                        category=None,
                    )

            # (1-2) 승인 패턴 검사
            confirm_patterns = [
                r"(기록|남겨|적어)\s*(해줘|줘|주세요|부탁)",
                r"^(응|어|네|예|그래|좋아|좋아요|좋습니다|부탁해|해줘|ㅇㅇ|yes|y|ok|sure)(\s+(좋아|그래|해줘|요))?$",
                r"^(응\s*좋아|응\s*그래|좋아요|좋습니다)$",
            ]
            for pattern in confirm_patterns:
                if re.search(pattern, prompt_clean, re.IGNORECASE):
                    content = pending_log.get("content", prompt_clean)
                    cat = pending_log.get("category", "Daily Notes & Diary")
                    return IntentResult(
                        intent="log_confirm",
                        ai_response=f"오늘 자 라이프로그 **[{cat}]** 섹션에 '{content}' 내용을 예쁘게 기록하고 GitHub 동기화를 마쳤습니다! 📝✨",
                        log_content=content,
                        category=cat,
                    )

        # -------------------------------------------------------------
        # 2. 명시적 직접 기록 및 맥락 참조 기록 요청 (log_explicit - ADR-010)
        # -------------------------------------------------------------
        if prompt_clean.startswith("/log "):
            log_body = prompt_clean[5:].strip()
            cat = self._detect_category(log_body)
            return IntentResult(
                intent="log_explicit",
                ai_response=f"명령해 주신 내용을 오늘 자 라이프로그 **[{cat}]**에 즉시 기록하고 GitHub에 커밋했습니다! 📄🚀",
                log_content=log_body,
                category=cat,
            )

        # 2-1. 이전 대화 맥락 참조 기록 ("아까 말한 내용도 기록해줘", "응 오늘 로그에 기록해줘", "방금 이야기 일기에 적어줘" 등 - ADR-010 & ADR-012)
        record_action_triggers = ["기록해", "적어줘", "남겨줘", "올려줘", "저장해", "써줘", "일기에", "로그에", "메모해"]
        context_ref_triggers = [
            "아까 말한", "아까 한", "방금 말한", "방금 한", "이전 이야기", "앞서 말한", "이전 대화",
            "지난 이야기", "아까 이야기", "방금 이야기", "이전 내용", "이 내용", "그 내용", "이 이야기", "그 이야기"
        ]

        has_explicit_context_ref = any(crt in prompt_clean for crt in context_ref_triggers) or (
            any(k in prompt_clean for k in ["아까", "방금", "이전", "앞서"]) and any(k in prompt_clean for k in ["말", "이야기", "내용"])
        )
        has_record_action = any(rat in prompt_clean for rat in record_action_triggers)

        # "응 오늘 로그에 기록해줘", "오늘 일기에 적어줘", "응 기록해줘"처럼 지시어/접두어만 있고 본문이 없는 경우 감지 (ADR-012)
        stripped_directive = prompt_clean
        stripped_directive = re.sub(r"^(응|어|네|예|그래|좋아|좋아요|오케이|ok|yes)\s*", "", stripped_directive, flags=re.IGNORECASE)
        stripped_directive = re.sub(r"(오늘|오늘자|오늘의|내일|어제)?\s*(라이프\s*로그|로그|일기|다이어리|수집함|인박스)?\s*(?:에|로|을|를)?\s*", "", stripped_directive)
        stripped_directive = re.sub(r"(기록|적어|남겨|올려|저장|써|메모)\s*(해줘|줘|주세요|부탁해|해|달라)?\s*", "", stripped_directive)
        stripped_directive = re.sub(r"(이|그)?\s*(내용|이야기|글|것|거|말)?\s*(?:도|은|는|이|가)?\s*", "", stripped_directive)
        is_pure_directive = has_record_action and len(stripped_directive.strip()) <= 2

        if (has_explicit_context_ref or is_pure_directive) and has_record_action and history:
            command_phrases = ["기록해", "푸시", "확인", "동기화", "pull", "push", "sync", "/", "응"]
            previous_user_msg = next(
                (
                    h["content"].strip()
                    for h in reversed(history)
                    if h.get("role") == "user"
                    and len(h.get("content", "").strip()) > 8
                    and not any(h.get("content", "").strip().startswith(cp) for cp in command_phrases)
                ),
                None,
            )
            if previous_user_msg:
                log_body = previous_user_msg
                cat = self._detect_category(f"{prompt_clean} {log_body}")
                snippet = log_body[:25] + "..." if len(log_body) > 25 else log_body
                return IntentResult(
                    intent="log_explicit",
                    ai_response=f"나누어 주신 소중한 이야기('{snippet}')를 오늘 자 라이프로그 **[{cat}]**에 기록하고 GitHub에 커밋했습니다! 🕯️📝",
                    log_content=log_body,
                    category=cat,
                )

        # 2-2. 복합 기록 지시 (데일리 로그 + GTD 인박스 동시 기록 - ADR-014)
        # 예: "회사에서 리조트를 신청할 수 있거든? ... 로그와 gtd에 기록해줘."
        dual_pattern = r"[\s,.]*(?:이\s*내용|이\s*이야기|이\s*글|이거|이것도)?\s*(?:오늘\s*)?(?:자\s*)?(?:데일리\s*)?(?:라이프\s*)?(?:로그\s*와|로그\s*랑|일기\s*와|일기\s*랑|다이어리\s*와|다이어리\s*랑)\s*(?:gtd\s*에?|할일\s*(?:에|에?도)?|인박스\s*에?|수집함\s*에?)\s*(?:둘\s*다|모두|함께|동시에)?\s*(?:에|로|을|를|도)?\s*(?:기록해줘|적어줘|남겨줘|넣어줘|추가해줘|올려줘|등록해줘|기록해|메모해줘)[\.\!\?\s]*$"
        dual_reverse_pattern = r"[\s,.]*(?:이\s*내용|이\s*이야기|이\s*글|이거|이것도)?\s*(?:오늘\s*)?(?:자\s*)?(?:gtd\s*와|gtd\s*랑|할일\s*과|할일\s*이랑|인박스\s*와|인박스\s*랑)\s*(?:데일리\s*)?(?:라이프\s*)?(?:로그\s*에?|일기\s*에?|다이어리\s*에?)\s*(?:둘\s*다|모두|함께|동시에)?\s*(?:에|로|을|를|도)?\s*(?:기록해줘|적어줘|남겨줘|넣어줘|추가해줘|올려줘|등록해줘|기록해|메모해줘)[\.\!\?\s]*$"

        dual_match = re.search(dual_pattern, prompt_clean, re.IGNORECASE) or re.search(dual_reverse_pattern, prompt_clean, re.IGNORECASE)
        if dual_match:
            cleaned_story = prompt_clean[:dual_match.start()].strip()
            cleaned_story = re.sub(r"^(응|어|네|예|그래|좋아|좋아요)\s*", "", cleaned_story).strip()
            if len(cleaned_story) > 3:
                gtd_task = self._extract_actionable_task(cleaned_story)
                cat = "Daily Notes & Diary"
                return IntentResult(
                    intent="log_dual",
                    ai_response=(
                        f"소중한 일상 이야기는 오늘 자 **[{cat}]**에 기록하고, "
                        f"실행 태스크(`- [ ] {gtd_task}`)는 **GTD 수집함(inbox.md)**에 등록했습니다! 📝📥✨"
                    ),
                    log_content=cleaned_story,
                    category=cat,
                    gtd_task_content=gtd_task,
                    is_dual_log=True,
                )

        # 2-3. 단일 후미 기록 명령 (e.g. "[긴 일화]... 오늘 로그에 기록해줘", "미팅 아젠다 정리... gtd에 추가해줘")
        single_end_pattern = r"[\s,.]*(?:이\s*내용|이\s*이야기|이\s*글|이거|이것도)?\s*(?:오늘\s*)?(?:자\s*)?(?:데일리\s*)?(?:라이프\s*)?(?:로그|일기|다이어리|gtd|인박스|수집함|할일)?\s*(?:에|로|을|를|도)?\s*(?:기록해줘|적어줘|남겨줘|넣어줘|추가해줘|올려줘|등록해줘|기록해|메모해줘)[\.\!\?\s]*$"
        single_end_match = re.search(single_end_pattern, prompt_clean, re.IGNORECASE)
        if single_end_match and len(prompt_clean[:single_end_match.start()].strip()) > 3:
            cleaned_body = prompt_clean[:single_end_match.start()].strip()
            cleaned_body = re.sub(r"^(응|어|네|예|그래|좋아|좋아요)\s*", "", cleaned_body).strip()
            matched_suffix = single_end_match.group(0).lower()

            if any(k in matched_suffix for k in ["gtd", "인박스", "inbox", "수집함", "할일"]):
                gtd_task = self._extract_actionable_task(cleaned_body)
                return IntentResult(
                    intent="log_explicit",
                    ai_response=f"요청하신 태스크(`- [ ] {gtd_task}`)를 **GTD 수집함(inbox.md)**에 등록하고 GitHub에 커밋했습니다! 📥🚀",
                    log_content=f"- [ ] {gtd_task}",
                    category="GTD Inbox",
                )
            else:
                cat = self._detect_category(cleaned_body)
                return IntentResult(
                    intent="log_explicit",
                    ai_response=f"보내주신 소중한 일과와 감정을 오늘 자 라이프로그 **[{cat}]**에 즉시 기록하고 GitHub에 커밋했습니다! 📝✨",
                    log_content=cleaned_body,
                    category=cat,
                )

        # 2-4. 문장 중간 기록 지시어 처리 (e.g. "헬스장 1시간 운동 기록해줘. 뿌듯함")
        explicit_match = re.search(
            r"(.*?)(?:을|를)?\s*(?:기록해줘|일기에\s*적어줘|로그에\s*남겨줘|기록해)(.*)",
            prompt_clean,
            re.DOTALL,
        )
        if explicit_match:
            main_part = explicit_match.group(1).strip()
            extra_part = explicit_match.group(2).strip()
            cleaned_main = re.sub(r"^(응|어|네|예|그래|좋아|좋아요)\s*", "", main_part)
            cleaned_main = re.sub(r"^(오늘|오늘자|라이프로그|로그|일기)?\s*(?:에|로)?\s*", "", cleaned_main).strip()
            if len(cleaned_main) > 2 and not any(w in main_part for w in ["아까", "방금", "이전"]):
                log_body = f"{main_part} {extra_part}".strip() if extra_part else main_part
                cat = self._detect_category(log_body)
                return IntentResult(
                    intent="log_explicit",
                    ai_response=f"요청하신 '{main_part}' 내용을 오늘 자 **[{cat}]**에 기록하고 GitHub에 커밋했습니다! 📄✨",
                    log_content=log_body,
                    category=cat,
                )


        # -------------------------------------------------------------
        # 3. GTD 레포 원격 푸시 (repo_push - ADR-011)
        # -------------------------------------------------------------
        is_pushup = any(w in prompt_clean.lower() for w in ["푸시업", "pushup", "push-up", "push up"])
        is_explicit_push = prompt_clean.lower() in [
            "/push", "push", "푸시", "푸시해", "푸시해줘", "푸시도 해줘", "푸시 부탁", "푸시 부탁해",
            "깃 푸시", "깃 푸시해줘", "git push", "깃푸시", "푸시 확인", "푸시 확인해줘", "푸시 다시 해줘"
        ]
        push_action_patterns = [
            r"(?:깃|git|원격|github|저장소|gtd|커밋|로그|내용|기록)?\s*(?:푸시|push)\s*(?:해줘|해|줘|주세요|부탁|확인|다시|진행)",
            r"(?:푸시|push)\s*(?:가|도|를|은)?\s*(?:안\s*됐|실패|누락|확인|다시|됐어|해줘|부탁)",
            r"(?:원격|깃허브|github)\s*(?:저장소)?(?:에|로)?\s*(?:올려줘|푸시해줘|반영해줘|보내줘)",
        ]
        has_push_action = any(re.search(pat, prompt_clean, re.IGNORECASE) for pat in push_action_patterns)

        if not is_pushup and (is_explicit_push or has_push_action):
            return IntentResult(
                intent="repo_push",
                ai_response="",
                log_content=None,
                category="Git",
            )

        # -------------------------------------------------------------
        # 4. GTD 레포 원격 동기화 및 최신화 (repo_sync / repo_sync_and_briefing - ADR-009)
        # -------------------------------------------------------------
        sync_triggers = ["최신화", "동기화", "pull", "sync", "가져와", "업데이트"]
        has_sync = any(st in prompt_clean.lower() for st in sync_triggers)

        briefing_triggers = [
            "해야할 일", "해야 할 일", "할 일", "할일", "투두", "todo", "일정", "스케줄",
            "gtd", "다음 행동", "수집함", "인박스", "태스크", "스케쥴"
        ]
        action_triggers = [
            "정리", "알려", "보여", "뭐 있", "확인", "브리핑", "요약", "체크", "목록",
            "리스트", "뭐 해야", "어떤 거", "어떻게 돼", "뭐할까", "뭐하지", "현황", "다시 알려"
        ]

        briefing_request_triggers = [
            "알려", "정리", "보여", "브리핑", "요약", "보고", "체크", "어때", "어떻게",
            "해야할 일", "해야 할 일", "할 일", "할일", "투두", "일정", "스케줄", "다음 행동"
        ]

        if prompt_clean.lower() == "/sync" or (has_sync and any(k in prompt_clean.lower() for k in ["레포", "gtd", "저장소", "git", "깃"])):
            # 동기화 + 브리핑 동시 요청 여부 확인 ("최신화하고 다시 알려줘", "동기화하고 일정 정리" 등)
            if any(brt in prompt_clean.lower() for brt in briefing_request_triggers):
                return IntentResult(
                    intent="repo_sync_and_briefing",
                    ai_response="",
                    log_content=None,
                    category="GTD",
                )
            return IntentResult(
                intent="repo_sync",
                ai_response="",
                log_content=None,
                category="GTD",
            )


        # -------------------------------------------------------------
        # 4. GTD 할 일 / 일정 / 브리핑 요청 (task_briefing - ADR-008)
        # -------------------------------------------------------------
        if any(bt in prompt_clean.lower() for bt in briefing_triggers) and any(at in prompt_clean.lower() for at in action_triggers):
            return IntentResult(
                intent="task_briefing",
                ai_response="",
                log_content=None,
                category="GTD",
            )


        # -------------------------------------------------------------
        # 4. 일과/사건/생각 감지 및 능동적 기록 제안 (log_suggest)
        # -------------------------------------------------------------
        workout_keywords = ["운동", "헬스", "러닝", "달리기", "벤치", "스쿼트", "풀업", "pt", "산책", "수영", "요가", "만보", "몸무게", "식단"]
        if any(k in prompt_clean for k in workout_keywords):
            cat = "Workout & Health"
            return IntentResult(
                intent="log_suggest",
                ai_response=f"건강을 챙기시는 모습이 정말 멋지십니다! 🏋️ 오늘 운동 기록({cat})에 **'{prompt_clean}'** 내용을 기록해 둘까요?",
                log_content=prompt_clean,
                category=cat,
            )

        idea_keywords = ["아이디어", "생각", "영감", "깨달음", "고민", "결심", "계획", "배움"]
        if any(k in prompt_clean for k in idea_keywords):
            cat = "Ideas & Thoughts"
            return IntentResult(
                intent="log_suggest",
                ai_response=f"참 흥미롭고 가치 있는 생각이네요! 💡 오늘의 생각 & 아이디어({cat})에 **'{prompt_clean}'** 내용을 적어둘까요?",
                log_content=prompt_clean,
                category=cat,
            )

        work_keywords = ["미팅", "회의", "프로젝트", "배포", "출시", "통과", "발표", "보고서", "완료", "퇴근", "출근", "업무", "성공"]
        if any(k in prompt_clean for k in work_keywords):
            cat = "Daily Notes & Diary"
            return IntentResult(
                intent="log_suggest",
                ai_response=f"오늘 하루도 정말 수고 많으셨습니다! 💼 오늘의 업무 및 일과({cat})에 **'{prompt_clean}'** 내용을 기록해 둘까요?",
                log_content=prompt_clean,
                category=cat,
            )

        # -------------------------------------------------------------
        # 5. 빠른 응답 패턴 (Fast-Path)
        # -------------------------------------------------------------
        # 숫자 뽑기 / 랜덤
        if re.search(r"(\d+)\s*부터\s*(\d+)", prompt_clean) or ("숫자" in prompt_clean and "골라" in prompt_clean):
            match = re.search(r"(\d+)\s*부터\s*(\d+)", prompt_clean)
            if match:
                min_val, max_val = int(match.group(1)), int(match.group(2))
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
                chosen = random.randint(min_val, max_val)
                return IntentResult(
                    intent="chat_only",
                    ai_response=f"제가 **{min_val}부터 {max_val} 범위**에서 고른 숫자는 **{chosen}**입니다! 🎲 마음에 드시나요?",
                )
            else:
                chosen = random.randint(1, 30)
                return IntentResult(
                    intent="chat_only",
                    ai_response=f"제가 고른 숫자는 **{chosen}**입니다! 🎲 마음에 드시나요?",
                )

        # 직전 숫자 선택에 대한 질문 처리 ("왜 23을 골랐어?", "왜 그 숫자야?")
        if re.search(r"왜\s*(\d+).*?(골랐|선택)", prompt_clean) or ("왜" in prompt_clean and "골랐" in prompt_clean):
            num_match = re.search(r"(\d+)", prompt_clean)
            num_str = num_match.group(1) if num_match else "그 숫자"
            return IntentResult(
                intent="chat_only",
                ai_response=(
                    f"제가 {num_str}을 고른 이유는, 수많은 숫자 중에서 가장 반짝이고 오늘 사용자님께 "
                    f"특별한 행운과 활력을 불어넣어 줄 것 같은 기운이 느껴졌기 때문이에요! 🎲✨\n"
                    f"나누어떨어지지 않는 독보적인 매력도 있고요. 마음에 드셨길 바랍니다! 😊"
                ),
            )

        # -------------------------------------------------------------
        # 6. 지능형 AI 엔진 대화 (AGY / Gemini Bridge)
        # -------------------------------------------------------------
        ai_response = self._call_ai_engine(prompt=prompt_clean, history=history)
        return IntentResult(
            intent="chat_only",
            ai_response=ai_response,
        )

    def _call_ai_engine(self, prompt: str, history: list[dict[str, str]] | None = None) -> str:
        """AGY CLI 또는 지능형 AI 엔진을 호출하여 이전 대화 맥락 기반 답변을 생성합니다."""
        agy_bin = self._find_agy_path()
        if agy_bin:
            try:
                # 최근 4개 대화 맥락 추출 및 긴 어시스턴트 메시지 슬라이싱 (ADR-010 프롬프트 다이어트)
                history_text = ""
                if history:
                    recent = history[-4:]
                    for h in recent:
                        role_name = "사용자" if h.get("role") == "user" else "왓슨"
                        content = str(h.get("content", "")).strip()
                        # 어시스턴트의 긴 브리핑/답변(GTD 목록 등)은 250자로 축약
                        if len(content) > 250:
                            content = content[:250] + " ... (이하 요약 생략)"
                        history_text += f"{role_name}: {content}\n"

                full_prompt = (
                    "너는 사용자의 24시간 개인 라이프로그 및 GTD AI 비서 왓슨(Watson)이다.\n"
                    "친절하고 다정하며 센스 있게 한국어로 대화해라. 이전 대화 맥락이 있다면 자연스럽게 이어가라.\n"
                    "주의: 코드 블록 실행이나 실제 Git 명령을 시뮬레이션하지 말고, 사용자와의 진솔하고 따뜻한 대화 및 조언에 집중하라.\n"
                    "절대로 '이야기 잘 들었습니다' 같은 기계적이고 판에 박힌 앵무새 답변을 하지 마라. "
                    "사용자의 질문이나 대화에 귀기울이고 구체적이고 도움이 되는 답변을 정성껏 제공해라.\n\n"
                )
                if history_text:
                    full_prompt += f"[이전 대화 내역]\n{history_text}\n"
                full_prompt += f"[사용자 입력]\n{prompt}\n\n왓슨 비서로서 답변:"

                env = os.environ.copy()
                env["PATH"] = "/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")

                res = subprocess.run(
                    [agy_bin, "-p", full_prompt, "--dangerously-skip-permissions"],
                    capture_output=True,
                    text=True,
                    timeout=50,
                    check=False,
                    env=env,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except (subprocess.SubprocessError, OSError) as e:
                logger.warning(f"AGY execution error: {e}")

        # 스마트 로컬 Fallback
        if any(w in prompt for w in ["누구", "왓슨"]):
            return (
                "저는 24시간 사용자의 삶의 기록(Life Log)과 GTD를 관리하는 **Watson AI 비서**입니다. 🤖\n"
                "일상 대화부터 오늘 해야 할 일 브리핑, 소중한 일과와 생각을 GitHub 마크다운으로 깔끔하게 기록해 드립니다!"
            )
        if any(w in prompt for w in ["안녕", "반가워", "하이"]):
            return "안녕하세요! 👋 왓슨 AI 비서입니다. 오늘 하루는 어떠셨나요? 편하게 이야기 들려주세요!"
        if any(w in prompt for w in ["날씨", "시간"]):
            return "오늘도 활기차고 좋은 하루 보내시길 바랍니다! 궁금한 점이 있으시거나 나누고 싶은 이야기가 있다면 언제든 말씀해 주세요. ☀️"

        # 이전 대화가 진행 중일 때 맥락을 인지하는 폴백 (ADR-010 & ADR-011)
        if history and len(history) > 0:
            if any(k in prompt for k in ["푸시", "커밋", "동기화", "확인", "깃", "오류", "에러", "실행", "명령"]):
                return (
                    "요청하신 작업 상태를 확인하고 있습니다. `/status`, `/sync`, `/push` 명령어로 저장소 상태를 직접 점검 및 실행하실 수 있습니다. 🤖"
                )
            return (
                "말씀해 주신 깊은 마음과 생각 잘 헤아리고 있습니다. 곁에서 언제나 든든한 버팀목이 되어 드릴 테니, "
                "필요하신 점이나 덧붙이고 싶은 일과가 있다면 편하게 이어서 말씀해 주세요. 🕯️"
            )

        return "네, 사용자님 말씀 잘 듣고 있습니다! 😊 오늘 하루 있었던 일과나 나누고 싶은 생각, 혹은 정리할 일정이 있다면 무엇이든 편하게 말씀해 주세요."


    def generate_response(self, prompt: str, history: list[dict[str, str]] | None = None) -> str:
        """기존 인터페이스 하위 호환용 메서드."""
        result = self.analyze_and_respond(prompt=prompt, history=history)
        return result.ai_response

    def _detect_category(self, text: str) -> str:
        """텍스트 내용을 분석하여 적합한 마크다운 카테고리를 추론합니다."""
        gtd_keywords = ["gtd", "할일", "할 일", "구매", "장보기", "투두", "todo", "task", "구입", "사야", "주문", "inbox", "수집함"]
        if any(k in text.lower() for k in gtd_keywords):
            return "GTD Inbox"
        workout_keywords = ["운동", "헬스", "러닝", "달리기", "벤치", "스쿼트", "풀업", "pt", "산책", "수영", "요가", "만보"]
        if any(k in text for k in workout_keywords):
            return "Workout & Health"
        idea_keywords = ["아이디어", "생각", "영감", "깨달음", "고민", "결심", "계획", "감정", "마음", "슬퍼", "걱정", "불안", "기분", "느낌"]
        if any(k in text for k in idea_keywords):
            return "Ideas & Thoughts"
        return "Daily Notes & Diary"

    def _extract_actionable_task(self, text: str) -> str:
        """
        비정형 일상 텍스트에서 실행 가능한 GTD 액션 태스크를 간결하고 명확하게 추출합니다 (ADR-014).
        """
        cleaned = text.strip()

        # 1. 구매 / 장보기 패턴
        buy_match = re.search(r"([가-힣A-Za-z0-9\s,]+?)(?:을|를|도)?\s*(?:사야|구매|구입|주문|장보기|결제)", cleaned)
        if buy_match and len(buy_match.group(1).strip()) > 1:
            items = [w.strip() for w in re.split(r"[,랑와과\s]+", buy_match.group(1)) if len(w.strip()) > 1]
            if items:
                return f"{' / '.join(items[:3])} 구매 🛒"

        # 2. 여행 / 나들이 / 방문 / 휴가 패턴
        travel_match = re.search(r"([가-힣A-Za-z0-9]+(?:쪽|으로|에)?)\s*(?:여행|방문|나들이|휴가|가보려)", cleaned)
        if travel_match:
            raw_dest = travel_match.group(1)
            dest = re.sub(r"(쪽으로|으로|쪽|에)$", "", raw_dest).strip()
            spots = []
            for word in ["용현집", "어죽", "게국지", "맛집", "식당", "카페", "리조트", "호텔", "숙소", "펜션", "또간집"]:
                if word in cleaned and word not in spots:
                    spots.append(word)
            spots_str = f" ({', '.join(spots[:3])})" if spots else ""
            if dest:
                return f"{dest} 여행 계획 및 맛집 방문{spots_str} 🚗🍲"
            elif spots:
                return f"{spots[0]} 방문 및 여행 계획 🚗🍲"

        # 3. 병원 / 건강 / 검진
        health_match = re.search(r"([가-힣A-Za-z0-9\s]+?(?:병원|검진|초음파|진료|치료|재검))", cleaned)
        if health_match:
            h_item = health_match.group(1).strip()
            return f"{h_item} 방문 및 확인 🏥"

        # 4. 업무 / 회의 / 프로젝트 / 문서
        work_match = re.search(r"([가-힣A-Za-z0-9\s]+?(?:회의|미팅|보고|프로젝트|기획|개발|배포|가이드라인|문서|정리))", cleaned)
        if work_match and len(work_match.group(1).strip()) > 3:
            w_item = work_match.group(1).strip()
            return f"{w_item} 진행 📊"

        # 5. 문장의 핵심 어절 추출
        sentences = [s.strip() for s in re.split(r"[\n.!?]", cleaned) if len(s.strip()) > 3]
        if sentences:
            candidate = sentences[-1]
            candidate = re.sub(r"(로그|gtd|일기|인박스|할일|기록|남겨|적어).*$", "", candidate).strip()
            if len(candidate) > 4:
                return f"{candidate} 📌"

        return f"{cleaned[:25].strip()} 📌"

