import os
from datetime import datetime, timezone


class AgentService:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir

    def get_lifelog_filepath(self, date_obj: datetime | None = None) -> str:
        if date_obj is None:
            date_obj = datetime.now(timezone.utc)
        
        year_str = date_obj.strftime("%Y")
        month_str = date_obj.strftime("%m")
        filename = date_obj.strftime("%Y-%m-%d.md")

        dir_path = os.path.join(self.base_dir, "lifelogs", year_str, month_str)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, filename)

    def append_or_update_lifelog(self, content: str, category: str = "Daily Notes & Diary", date_obj: datetime | None = None) -> str:
        filepath = self.get_lifelog_filepath(date_obj)
        current_date_str = (date_obj or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
        time_str = (date_obj or datetime.now(timezone.utc)).strftime("%H:%M")

        if not os.path.exists(filepath):
            # Create new file with template
            initial_template = f"""# 📅 Life Log - {current_date_str}

## 📝 Daily Notes & Diary

## 🏋️ Workout & Health

## 💡 Ideas & Thoughts

## 🖼️ Media & Attachments
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(initial_template)

        with open(filepath, "r", encoding="utf-8") as f:
            file_lines = f.readlines()

        header_target = f"## 📝 {category}" if not category.startswith("##") else category
        if "Daily Notes" in category:
            header_target = "## 📝 Daily Notes & Diary"
        elif "Workout" in category or "Health" in category:
            header_target = "## 🏋️ Workout & Health"
        elif "Idea" in category or "Thought" in category:
            header_target = "## 💡 Ideas & Thoughts"
        elif "Media" in category or "Attachment" in category:
            header_target = "## 🖼️ Media & Attachments"

        entry_line = f"- [{time_str}] {content}\n"
        
        # Find header line index
        target_idx = -1
        for i, line in enumerate(file_lines):
            if header_target.lower() in line.lower():
                target_idx = i
                break

        if target_idx != -1:
            file_lines.insert(target_idx + 1, entry_line)
        else:
            file_lines.append(f"\n{header_target}\n{entry_line}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(file_lines)

        return filepath
