from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.productivity import ProductivityService
import config

router = Router()

def is_authorized(user_id: int) -> bool:
    if not config.AUTHORIZED_USER_ID:
        return True
    return str(user_id) == str(config.AUTHORIZED_USER_ID)

async def send_safe_message(message: Message, text: str, reply_markup=None, parse_mode="Markdown"):
    """4000자를 초과하는 긴 메시지를 안전하게 분할 전송"""
    if len(text) <= 4000:
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        for i in range(0, len(text), 4000):
            chunk = text[i:i+4000]
            # 인라인 키보드는 마지막 조각에만 부착
            current_markup = reply_markup if i + 4000 >= len(text) else None
            await message.answer(chunk, reply_markup=current_markup, parse_mode=parse_mode)

def get_todo_keyboard(todos) -> InlineKeyboardMarkup:
    buttons = []
    for t in todos:
        status_icon = "✅" if t.completed else "☐"
        buttons.append([InlineKeyboardButton(text=f"{status_icon} {t.title}", callback_data=f"toggle:{t.id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def register_handlers(service: ProductivityService):
    @router.message(Command("start"))
    async def cmd_start(message: Message):
        if not is_authorized(message.from_user.id):
            await message.answer("🔒 사용 권한이 없습니다.")
            return

        text = (
            "🤖 **Watson Bot에 오신 것을 환영합니다!**\n\n"
            "생산성 관리 명령어 안내:\n"
            "• `/todo [할일]` - 새로운 할 일 추가\n"
            "• `/todos` - 할 일 목록 확인 및 토글\n"
            "• `/memo [내용]` - 메모 저장\n"
            "• `/memos` - 메모 목록 확인\n"
            "• `/schedule [내용]` - 일정 등록"
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

    return router
