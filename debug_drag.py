import sys
sys.path.insert(0, r'F:\Program_data\pycharm_data\MyDesktop\desktop-pet')

with open(r'F:\Program_data\pycharm_data\MyDesktop\desktop-pet\pet\app.py', 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

# Add a simple _debug_drag_state method after __init__ or before first use
insert_idx = None
for i, line in enumerate(lines):
    if '    def _tick(self) -> None:' in line:
        insert_idx = i
        break

debug_method = [
    '    def _debug_drag_state(self):\n',
    '        print("[debug] _dragged=" + str(self._dragged) + " _selected=" + str(self._selected) + " state=" + str(self.animator.state))\n',
    '\n'
]

if insert_idx is not None:
    lines = lines[:insert_idx] + debug_method + lines[insert_idx:]

# Patch _click_press
for i, line in enumerate(lines):
    if '    def _click_press(self, event: tk.Event) -> None:' in line:
        lines[i] = '    def _click_press(self, event: tk.Event) -> None:\n        print("[debug] _click_press")\n        self._debug_drag_state()\n        self._dragged = False\n'
        break

# Patch _click_release
for i, line in enumerate(lines):
    if '    def _click_release(self, event: tk.Event) -> None:' in line:
        lines[i] = '    def _click_release(self, event: tk.Event) -> None:\n        print("[debug] _click_release")\n        self._debug_drag_state()\n        if self._dragged:\n            self._dragged = False\n            return\n        self._selected = not self._selected\n'
        break

# Patch _drag_move
for i, line in enumerate(lines):
    if '    def _drag_move(self) -> None:' in line:
        lines[i] = '    def _drag_move(self) -> None:\n        print("[debug] _drag_move")\n        self._debug_drag_state()\n        if not self._dragged:\n            self._dragged = True\n            self._selected = False\n        if not self._sleeping and self.animator.state != PetState.DRAG:\n            self.animator.play(PetState.DRAG, loop=True, now=time.time())\n'
        break

with open(r'F:\Program_data\pycharm_data\MyDesktop\desktop-pet\pet\app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Debug logging added')
