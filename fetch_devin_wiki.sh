#!/bin/bash
TOKEN="${1}"
ORG="org-3fd96d8d339b4afe87f315915f33907d"

fetch_wiki() {
  local REPO="$1"
  local OUTFILE="$2"
  local OUTDIR="$3"
  mkdir -p "$OUTDIR"
  curl -s "https://app.devin.ai/api/wiki/get_full_multi_language_wiki?repo_name=${REPO}" \
    -H "accept: */*" \
    -H "authorization: Bearer ${TOKEN}" \
    -H "x-cog-org-id: ${ORG}" \
    -H "referer: https://app.devin.ai/org/carley-fant/wiki/${REPO}" \
    -o "$OUTFILE"
  echo "$(wc -c < $OUTFILE) bytes saved to $OUTFILE"
  python3 << EOF
import json, os
with open('$OUTFILE') as f:
    data = json.load(f)
pages = data['wiki']['wikis']['en']['pages']
print(f"Total pages: {len(pages)}")
os.makedirs('$OUTDIR', exist_ok=True)
for p in pages:
    plan = p.get('page_plan', {})
    pid = plan.get('id','unknown').replace('/', '_')
    title = plan.get('title','untitled')
    content = p.get('content', '')
    with open(f'$OUTDIR/{pid}.md', 'w') as f:
        f.write(f"# {title}\n\n{content}")
    print(f"  {pid}: {title} ({len(content)} chars, {content.count('mermaid')} mermaid)")
EOF
}

fetch_wiki "51nk0r5w1m%2Famass"              "devin_wiki_raw/full_wiki.json"     "devin_wiki_raw/pages"
fetch_wiki "51nk0r5w1m%2Ffork_open-asset-model" "devin_wiki_raw/full_wiki_oam.json" "devin_wiki_raw/pages_oam"
fetch_wiki "51nk0r5w1m%2Ffork-asset-db" "devin_wiki_raw/full_wiki_assetdb.json" "devin_wiki_raw/pages_assetdb"

# Also run standalone:
# fetch_wiki "51nk0r5w1m%2Ffork-asset-db" "devin_wiki_raw/full_wiki_assetdb.json" "devin_wiki_raw/pages_assetdb"
