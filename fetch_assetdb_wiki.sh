#!/bin/bash
TOKEN="${1}"
ORG="org-3fd96d8d339b4afe87f315915f33907d"
mkdir -p devin_wiki_raw/pages_assetdb

curl -s "https://app.devin.ai/api/wiki/get_full_multi_language_wiki?repo_name=51nk0r5w1m%2Ffork-asset-db" \
  -H "accept: */*" \
  -H "authorization: Bearer ${TOKEN}" \
  -H "x-cog-org-id: ${ORG}" \
  -H "referer: https://app.devin.ai/org/carley-fant/wiki/51nk0r5w1m/fork-asset-db" \
  -o devin_wiki_raw/full_wiki_assetdb.json

echo "$(wc -c < devin_wiki_raw/full_wiki_assetdb.json) bytes"
head -c 100 devin_wiki_raw/full_wiki_assetdb.json

python3 << 'EOF'
import json, os
with open('devin_wiki_raw/full_wiki_assetdb.json') as f:
    data = json.load(f)
pages = data['wiki']['wikis']['en']['pages']
print(f"\nTotal pages: {len(pages)}")
for p in pages:
    plan = p.get('page_plan', {})
    pid = plan.get('id','unknown').replace('/', '_')
    title = plan.get('title','untitled')
    content = p.get('content', '')
    with open(f'devin_wiki_raw/pages_assetdb/{pid}.md', 'w') as f:
        f.write(f"# {title}\n\n{content}")
    print(f"  {pid}: {title} ({len(content)} chars, {content.count('mermaid')} mermaid)")
EOF
