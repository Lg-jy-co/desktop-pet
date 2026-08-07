# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'F:\Program_data\pycharm_data\MyDesktop\desktop-pet\README.md', 'r', encoding='utf-8-sig') as f:
    content = f.read()

new_section = (
    "## New Features\n"
    "\n"
    "### Local File Feeding\n"
    "- Added a local file feeding option in the Feed menu.\n"
    "- Feed value rules: base value 1, extension multiplier (.txt*5, .py*10, .md*3, .json*2), filename keyword multiplier (contains 'fruit'*2, 'gift'*5, 'snack'*3).\n"
    "- Source file is deleted after feeding (please feed copies or disposable files).\n"
    "- Drag-and-drop feeding requires tkinterdnd2 (pip install tkinterdnd2).\n"
    "\n"
    "### Keyboard Movement\n"
    "- Click the pet to select it, then use arrow keys or numpad to move.\n"
    "- Numpad 7/9/1/3 move diagonally; numpad 5 stops movement.\n"
    "- Directional animations are mapped to existing states as placeholders.\n"
    "\n"
    "### Random Movement\n"
    "- The pet may move randomly every ~8 seconds (30% chance, lasting 2 seconds).\n"
    "- Random movement is disabled while the pet is selected.\n"
    "\n"
    "### Drag Animation\n"
    "- Dragging plays the DRAG placeholder state (flattened body).\n"
    "- Dragging clears the selected state.\n"
    "\n"
    "### Notification Fix\n"
    "- Fixed _on_message to use now=time.time() correctly.\n"
    "\n"
)

parts = content.split('\n## ', 1)
if len(parts) == 2:
    content = parts[0] + new_section + '\n## ' + parts[1]
else:
    content = content + '\n\n' + new_section

with open(r'F:\Program_data\pycharm_data\MyDesktop\desktop-pet\README.md', 'w', encoding='utf-8') as f:
    f.write(content)
print('README updated')
