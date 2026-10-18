# hook-tkinterdnd2.py
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files('tkinterdnd2')
binaries = collect_dynamic_libs('tkinterdnd2')