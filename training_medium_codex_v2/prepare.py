from pathlib import Path
p=Path('training_medium_codex_v2/validate_sandbox_medium.cjs');s=p.read_text().replace("const outputPath = path.join(__dirname, 'best', 'answer_level-6_2-medium.txt');","const outputPath = process.argv[2] || path.join(__dirname, 'best', 'answer_level-6_2-medium.txt');");p.write_text(s)
