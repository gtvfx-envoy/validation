import sys, json, os
from pathlib import Path
from graphify.llm import extract_corpus_parallel

# Configure Ollama with qwen3-coder:30b model
os.environ['GRAPHIFY_OLLAMA_BASE_URL'] = 'http://localhost:11434/v1'
os.environ['GRAPHIFY_OLLAMA_MODEL'] = 'qwen3-coder:30b'

detect = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
files = [f for cat in ('document', 'paper', 'image') for f in detect['files'].get(cat, [])]
print(f'Semantic extraction: {len(files)} files with Ollama (qwen3-coder:30b)', file=sys.stderr)

result = extract_corpus_parallel(
    files, 
    backend='ollama', 
    cache_root=Path('C:/graphify-cache')
)

Path('graphify-out/.graphify_semantic.json').write_text(
    json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'Semantic: {len(result.get("nodes", []))} nodes, {len(result.get("edges", []))} edges', file=sys.stderr)
