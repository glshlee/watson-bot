---
name: markdown-lifelog
description: 비정형 유저 텍스트/이미지 메모를 표준화된 마크다운 라이프 로그 파일로 생성/업데이트하는 스킬
---

# 📝 Markdown LifeLog Skill

## 1. 목적
유저의 자유로운 입력 메시지를 일관성 있고 아름다운 마크다운(MD) 구조로 파싱하여 적절한 날짜 파일에 반영한다.

## 2. 템플릿 표준 규격 (Template Specification)
```markdown
# 📅 Life Log - YYYY-MM-DD

## 📝 Daily Notes & Diary
- [시간] 기록 내용...

## 🏋️ Workout & Health
- 운동 종류 및 기록...

## 💡 Ideas & Thoughts
- 생각 정리 및 아이디어...

## 🖼️ Media & Attachments
- ![caption](static/images/path.png)
```

## 3. 업데이트 규칙 (Append / Edit Rules)
- **파일 미존재 시**: 해당 날짜 경로(`lifelogs/YYYY/MM/YYYY-MM-DD.md`) 생성 후 전체 헤더 템플릿과 함께 내용 작성.
- **파일 존재 시**: 기존 MD 구문을 파싱하여 해당 섹션 아래에 신규 로그를 덧붙임(Append). 기존 항목 수정 요청 시 해당 섹션만 치환(Edit).
