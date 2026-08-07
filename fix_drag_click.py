import sys
sys.path.insert(0, r'F:\Program_data\pycharm_data\MyDesktop\desktop-pet')

with open(r'F:\Program_data\pycharm_data\MyDesktop\desktop-pet\pet\app.py', 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

# Remove any debug additions if present
lines = [line for line in lines if 'def _debug_drag_state' not in line]

# Add _drag_start_pos to __init__
for i, line in enumerate(lines):
    if '        self._move_direction = (0, 0)' in line and 'self._drag_start_pos' not in line:
        lines[i] = '        self._move_direction = (0, 0)\n        self._drag_start_pos = (0, 0)\n'
        break

# Patch _click_press
for i, line in enumerate(lines):
    if '    def _click_press(self, event: tk.Event) -> None:' in line:
        lines[i] = '    def _click_press(self, event: tk.Event) -> None:\n        self._dragged = False\n        self._drag_start_pos = (event.x_root, event.y_root)\n'
        break

# Patch _drag_move
for i, line in enumerate(lines):
    if '    def _drag_move(self) -> None:' in line:
        lines[i] = '    def _drag_move(self, event: tk.Event) -> None:\n        if not self._dragged:\n            dx = event.x_root - self._drag_start_pos[0]\n            dy = event.y_root - self._drag_start_pos[1]\n            if abs(dx) > 3 or abs(dy) > 3:\n                self._dragged = True\n                self._selected = False\n        if self._dragged and not self._sleeping and self.animator.state != PetState.DRAG:\n            self.animator.play(PetState.DRAG, loop=True, now=time.time())\n'
        break

# Patch _click_release
for i, line in enumerate(lines):
    if '    def _click_release(self, event: tk.Event) -> None:' in line:
        lines[i] = '    def _click_release(self, event: tk.Event) -> None:\n        if self._dragged:\n            self._dragged = False\n            return\n        self._selected = not self._selected\n        if self._selected:\n            self._say("selected")\n        else:\n            self._say("unselected")\n        self._interact()\n'
        break

with open(r'F:\Program_data\pycharm_data\MyDesktop\desktop-pet\pet\app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Patched drag/click with proper event handling')
