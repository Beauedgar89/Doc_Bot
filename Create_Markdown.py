from pathlib import Path
from ingest import extract_markdown


source_file = Path.cwd() / "C:\\VSCode\\Python Projects\\Doc_bot\\mentor-mp-advanced-user-guide.pdf"
markdown_text = extract_markdown(str(source_file))

output_path = Path.cwd() / "Mentor_mp_User_Guide.md"
output_path.write_text(markdown_text, encoding="utf-8")
print(f"Markdown content extracted from {source_file} and saved to {output_path}")