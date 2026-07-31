# Instructor Demo Guidance

## Demo 1: First Scanner
Use a very small subset of obvious failures.
Suggested targets:
- KnightBody.fbx
- chr_knight_sword_v001.max
- empty_texture.png
- prp_lantern_final_final2.fbx

Goal:
- successful directory walk
- readable terminal output
- clear pass/fail signal

## Demo 2: Add Config
Use configurable allowlists and banned terms.
Suggested targets:
- t_prp_lantern_d_v002.jpg
- notes.docx
- thumbs.db
- .DS_Store

Goal:
- show why hardcoding policy does not scale

## Demo 3: Structured Reporting
Output severity, rule_id, path, and message.

## Demo 4: Compare Clean vs Flawed
Run the same validator on both trees to show signal-to-noise value.

## Demo 5: Discuss False Positives
Use `.jpg`, `TODO.txt`, and documentation files to discuss policy decisions.
