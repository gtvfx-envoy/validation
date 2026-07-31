import json
from graphify.detect import detect
from pathlib import Path
result = detect(Path('V:\\repo\\gtvfx-contrib\\gt\\validation'))
Path='V:\\repo\\gtvfx-contrib\\gt\\validation'
open(Path+'\\graphify-out\\.graphify_detect.json','w',encoding='utf-8').write(json.dumps(result, ensure_ascii=False))
print(f"Files: {result.get('total_files',0)}, Words: ~{result.get('total_words',0):,}")
for cat in ['code','document','paper','image','video']:
    count = len(result['files'].get(cat,[]))
    if count > 0:
        print(f"  {cat}:     {count} files")
