#!/bin/bash
TOKEN="$1"
ORG_ID="org-3fd96d8d339b4afe87f315915f33907d"
curl -s "https://app.devin.ai/api/ada/list_indexes_by_org?invalidate_cache=false" -H "accept: */*" -H "authorization: Bearer ${TOKEN}" -H "x-cog-org-id: ${ORG_ID}" -o devin_indexes.json
cat devin_indexes.json
