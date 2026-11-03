# Documentation workflow

## Search before researching

Use the local search tool before starting external research:

```powershell
python scripts/dev/docs_tools/find.py --query "topic provider or model"
```

It searches Markdown under `docs/` and `stock-signal-bot/docs/` and prints ranked file/line matches. Start with [the documentation index](../INDEX.md). A search miss means no local match was found, not that no research exists elsewhere.

## Check docs affected by code

```powershell
python scripts/dev/docs_tools/check.py
python scripts/dev/docs_tools/check.py --files stock-signal-bot/backend/app/api/routes_scan.py
```

The source-to-doc mapping lives in `scripts/dev/departments/documentation/mapping_impl.py`. For a code change, the check lists likely affected docs; update those that actually describe changed behavior. CI enforces that mapped docs are present in pull requests. The check cannot infer or generate accurate architectural explanations.

`scripts/dev/update-docs.ps1` remains a PowerShell wrapper for the same check. To emit JSON, use `-Report`.

## Research records

Add reusable research to a topic file under `docs/research/`, and link it from `docs/INDEX.md`. Include source links, what was verified, access/license/quota caveats, verification date, and where the finding applies. Label volatile provider plans as needing re-verification before implementation. Do not copy private data or credentials into research notes.

Current provider/model findings and decisions: [free data and AI register](../research/FREE_DATA_AND_AI.md).
