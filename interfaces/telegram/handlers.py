import logging
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.productivity import ProductivityService
from services.ai_agent import WatsonAIEngine
import config

router = Router()

def is_authorized(user_id: int) -> bool:
    if not config.AUTHORIZED_USER_ID:
        return True
    return str(user_id) == str(config.AUTHORIZED_USER_ID)

async def send_safe_message(message: Message, text: str, reply_markup=None, parse_mode="Markdown"):
    """4000자를 초과하는 긴 메시지를 안전하게 분할 전송"""
    if len(text) <= 4000:
        return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        last_msg = None
        for i in range(0, len(text), 4000):
            chunk = text[i:i+4000]
            current_markup = reply_markup if i + 4000 >= len(text) else None
            last_msg = await message.answer(chunk, reply_markup=current_markup, parse_mode=parse_mode)
        return last_msg

def get_todo_keyboard(todos) -> InlineKeyboardMarkup:
    buttons = []
    for t in todos:
        status_icon = "✅" if t.completed else "☐"
        buttons.append([InlineKeyboardButton(text=f"{status_icon} {t.title}", callback_data=f"toggle:{t.id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def register_handlers(service: ProductivityService, ai_engine: WatsonAIEngine):
    @router.message(Command("start", "help"))
    async def cmd_start(message: Message):
        if not is_authorized(message.from_user.id):
            logging.warning(f"Unauthorized access attempt from user_id: {message.from_user.id}")
            await message.answer("🔒 사용 권한이 없습니다.")
            return

        text = (
            "🤖 **Watson AI Assistant에 오신 것을 환영합니다!**\n\n"
            "저는 당신의 지속 대화 상대이자 생산성 조수입니다.\n"
            "• 자유롭게 아이디어나 질문, 잡담을 나눠보세요. (대화 맥락이 연속 유지됩니다)\n"
            "• 모든 대화는 GitHub `life_log` 내 Chat Log 노트에 자동 저장됩니다.\n"
            "• 할 일이나 메모 작성을 요청하시면 Todo/Memo 저장소에도 함께 기록됩니다.\n\n"
            "직접 명령어 안내:\n"
            "• `/todo [할일]` - 새로운 할 일 등록\n"
            "• `/todos` - 할 일 목록 조회 및 완료 상태 토글\n"
            "• `/memo [내용]` - 메모 저장\n"
            "• `/memos` - 전체 메모 목록 조회"
        )
        await send_safe_message(message, text)

    @router.message(Command("todo"))
    async def cmd_add_todo(message: Message):
        if not is_authorized(message.from_user.id):
            await message.answer("🔒 사용 권한이 없습니다.")
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("⚠️ 사용법: `/todo [할 일 내용]`", parse_mode="Markdown")
            return
        title = args[1]
        todo = await service.create_todo(user_id=message.from_user.id, title=title)
        await send_safe_message(message, f"✅ 새로운 할 일이 등록되었습니다:\n- {todo.title}")

    @router.message(Command("todos"))
    async def cmd_list_todos(message: Message):
        if not is_authorized(message.from_user.id):
            await message.answer("🔒 사용 권한이 없습니다.")
            return
        todos = await service.get_all_todos(user_id=message.from_user.id)
        if not todos:
            await message.answer("📌 등록된 할 일이 없습니다.")
            return
        kb = get_todo_keyboard(todos)
        await send_safe_message(message, "📋 **할 일 목록** (버튼 클릭시 완료/미완료 토글):", reply_markup=kb)

    @router.callback_query(F.data.startswith("toggle:"))
    async def cb_toggle_todo(callback: CallbackQuery):
        if not is_authorized(callback.from_user.id):
            await callback.answer("🔒 사용 권한이 없습니다.", show_alert=True)
            return
        todo_id = callback.data.split(":")[1]
        await service.toggle_todo_status(user_id=callback.from_user.id, todo_id=todo_id)
        todos = await service.get_all_todos(user_id=callback.from_user.id)
        kb = get_todo_keyboard(todos)
        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer("할 일 상태 변경 완료!")

    @router.message(Command("memo"))
    async def cmd_add_memo(message: Message):
        if not is_authorized(message.from_user.id):
            await message.answer("🔒 사용 권한이 없습니다.")
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("⚠️ 사용법: `/memo [메모 내용]`", parse_mode="Markdown")
            return
        memo = await service.create_memo(user_id=message.from_user.id, content=args[1])
        await send_safe_message(message, f"📝 메모가 저장되었습니다:\n- {memo.content}")

    @router.message(Command("memos"))
    async def cmd_list_memos(message: Message):
        if not is_authorized(message.from_user.id):
            await message.answer("🔒 사용 권한이 없습니다.")
            return
        memos = await service.get_all_memos(user_id=message.from_user.id)
        if not memos:
            await message.answer("📝 저장된 메모가 없습니다.")
            return
        lines = ["📝 **저장된 메모 목록:**"]
        for m in memos:
            lines.append(f"• {m.content}")
        await send_safe_message(message, "\n".join(lines))

    # 스마트 AI 대화 및 세션 연속성 + 대화 마크다운 깃 로그 자동 기록
    @router.message(F.text & ~F.text.startswith("/"))
    async def handle_general_text(message: Message):
        if not is_authorized(message.from_user.id):
            await message.answer("🔒 사용 권한이 없습니다.")
            return

        # 1. 즉시 "생각 중..." 피드백 메시지 발송
        status_msg = await message.answer("🤔 *Watson이 대화 맥락을 기억하며 답변 중입니다...*", parse_mode="Markdown")
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        user_text = message.text.strip()
        
        # 2. AI 대화 호출 (유저별 연속 세션 유지)
        ai_res = await ai_engine.analyze_and_respond(user_text=user_text, user_id=message.from_user.id)
        
        action = ai_res.get("action", "chat")
        content = ai_res.get("content", user_text)
        reply = ai_res.get("reply", "응답을 처리했습니다.")

        if action == "save_todo":
            todo = await service.create_todo(user_id=message.from_user.id, title=content or user_text)
            reply = f"{reply}\n\n📌 *(할 일에 자동 저장됨: {todo.title})*"
        elif action == "save_memo":
            memo = await service.create_memo(user_id=message.from_user.id, content=content or user_text)
            reply = f"{reply}\n\n📝 *(메모에 자동 저장됨: {memo.content})*"
        elif action == "save_schedule":
            schedule = await service.create_schedule(user_id=message.from_user.id, title=content or user_text, remind_time="")
            reply = f"{reply}\n\n📅 *(일정에 자동 저장됨: {schedule.title})*"

        # 3. 대화 내용을 life_log/02_personal/watson/chat_log_{user_id}.md 에 기록 후 Git push
        asyncio.create_task(service.record_chat_log(user_id=message.from_user.id, user_text=user_text, watson_reply=reply))

        # 4. 텔레그램 화면 출력
        try:
            if len(reply) <= 4000:
                await status_msg.edit_text(reply, parse_mode="Markdown")
            else:
                await status_msg.delete()
                await send_safe_message(message, reply)
        except Exception:
            await send_safe_message(message, reply)

    # 알 수 없는 커맨드 처리 핸들러
    @router.message(F.text.startswith("/"))
    async def handle_unknown_command(message: Message):
        if not is_authorized(message.from_user.id):
            await message.answer("🔒 사용 권한이 없습니다.")
            return
        await message.answer("❓ 알 수 없는 명령어입니다. `/start` 또는 `/help`를 입력하여 사용법을 확인하세요.", parse_mode="Markdown")

    return router
