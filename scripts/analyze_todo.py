"""Analyze TODO.md for pending items"""
with open('TODO.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    s = line.strip()
    if '待实现' in s or '⏳' in s or '待实施' in s or '待处理' in s:
        # Show context: this line and next few lines
        print(f'--- L{i} ---')
        for j in range(i, min(i+8, len(lines))):
            l = lines[j].strip()
            if l:
                safe = l.encode('ascii', 'ignore').decode('ascii')
                if safe:
                    print(f'  {safe[:150]}')
        print()
